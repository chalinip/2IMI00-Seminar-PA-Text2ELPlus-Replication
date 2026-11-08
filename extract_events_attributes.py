import re
import pandas as pd
import glob
import ntpath
import sys, os
from os import listdir
from os.path import isfile, join

import scispacy
import spacy

import en_core_web_sm
from itertools import chain

from spacy import displacy
from pathlib import Path


from stanfordnlp.server import CoreNLPClient

GH_DATE = r"(?:20[0-9]{2}-[0-9]{2}-[0-9]{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? [0-9]{1,2}(?:st|nd|rd|th)?(?:,? 20[0-9]{2})?|[0-9]{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?: 20[0-9]{2})?)"  # [G1]
os.environ["CORENLP_HOME"] = '/Users/chal/Desktop/Q1-2026/seminar-PA/my-code/text2el/tools/stanford-corenlp-4.4.0'  # [E3] your CoreNLP folder


#Extract events based on temporal expressions 
def apply_regex_rules(collection_filepath, output_file1):
    time = []
    activity = []
    caseID = []
    folders = [f for f in listdir(collection_filepath)]
    df = pd.DataFrame()

    for dir in folders:
        for f in glob.glob(collection_filepath + '/' + dir + "/*.txt"):  # [G3]
            with open(f, "r+") as inputfile:
                con = inputfile.read()
                x = con.split("\n")

                pattern = re.compile(r"(.*"+GH_DATE+")")  # [G1]
                frontkeyonlypattern = re.compile(  # [G1]
                    r"(.*)"+GH_DATE+r"([ ][0-9]*[:][0-9]{2}[ ]*(AM|A\.M\.|am|a\.m\.|PM|P\.M\.|pm|p\.m\.))?")
                backkeyonlypattern = re.compile(  # [G1]
                    GH_DATE+r"([ ][0-9]*[:][0-9]{2}[ ]*(AM|A\.M\.|am|a\.m\.|PM|P\.M\.|pm|p\.m\.))?(.*)")
                datetimepattern = re.compile(  # [G1]
                    r"("+GH_DATE+r"([ ][0-9]*[:][0-9]{2}[ ]*(AM|A\.M\.|am|a\.m\.|PM|P\.M\.|pm|p\.m\.))?)")
                pattern1 = re.compile(r"("+GH_DATE+".*)")  # [G1]

                for k in x:
                    if k.startswith("Date/Time:"): continue  # [G2] metadata header, not text
                    m = pattern.findall(k)
                    m1 = pattern1.findall(k)
                    for i in m:
                        caseID.append(dir)
                        if not datetimepattern.match(i):
                            rgx = frontkeyonlypattern.search(i)
                            if rgx.group(1) is not None:
                                activity.append(rgx.group(1))
                            rgx1 = datetimepattern.search(i)
                            if rgx1.group(1) is not None:
                                time.append(rgx1.group(1))

                        else:
                            for i1 in m1:
                                rgx = backkeyonlypattern.search(i1)
                                if rgx.group(3) is not None:
                                    activity.append(rgx.group(3))
                                rgx1 = datetimepattern.search(i1)
                                if rgx1.group(1) is not None:
                                    time.append(rgx1.group(1))


    df["HADM_ID"] = caseID
    df['Activity'] = activity
    df['Timestamp'] = time
    df['Note']="Description"  # [G3]


    df.to_csv(output_file1)

#Extract events from event specific notes 
LOOKUP = []  # [G4] filled in __main__ from lookup_github_activity.tsv
def extract_specific_notes(collection_filepath, output_file2):
    folders = [f for f in listdir(collection_filepath)]
    df = pd.DataFrame()

    table1 = {"HADM_ID": [], "Activity": [], "Timestamp": [], "Note": []}
    for dir in folders:

        for f in glob.glob(collection_filepath + '/' + dir + "/*_Comment.txt"):  # [G3]
            with open(f, "r+") as inputfile:

                con = inputfile.read()

                pattern1 = re.compile(r"Date/Time:(.*)")
                m2 = next((a for ph, a in LOOKUP if ph in con.lower().split("\n", 2)[-1]), "")  # [G4] replaces Test: line

                rem_characters = ["['", "']", "at"]
                m1 = pattern1.findall(con)

                for i in rem_characters:
                    m1 = str(m1).replace(i, "")  # [G4] not applied to m2: removing "at" mangles labels

                table1["HADM_ID"].append(dir)
                table1["Activity"].append(m2)
                table1["Timestamp"].append(m1)
                table1["Note"].append(os.path.basename(f))

    df = pd.DataFrame(table1)  # [B1] replaces df.append, which was inside the removed Radiology loop
    df = df[["HADM_ID", "Activity", "Timestamp", "Note"]]
    df = df.dropna(how='all')


    df = df.drop_duplicates(keep='first')

    df = df[df.Activity != '']
    df.to_csv(output_file2)
    
#Refine the extracted events by excluding the activities which can’t be events     
def refine_events(input_csv, exclude_list, stopword_list, output_csv):
    d = pd.read_csv(input_csv)
    f1 = open(exclude_list , "r")
    w_list = f1.read().split('\n')

    suffix_list = ['in', 'on', 'of', 'On']

    d['Activity'] = d['Activity'].str.strip()

    d['Activity'] = d['Activity'].str.rstrip(',')
    d['Activity'] = d['Activity'].str.rstrip(',')
    d['Activity'] = d['Activity'].str.lstrip(',')

    #for j in suffix_list:
      #  d['Activity'] = d['Activity'].str.removesuffix(j)


    d['Activity'] = d['Activity'].str.replace('^[^a-zA-Z]*', '', regex=True)  # [B2]
    d['Activity'] = d['Activity'].str.replace('^and*', '', regex=True)  # [B2]

    d = d[d['Activity'].str.len() > 0]
  

    out_df = d[~d['Activity'].str.lower().isin([x.lower() for x in w_list])]
    '''f2 = open(stopword_list, "r")
    among_list = f2.readlines()
    rem=str.maketrans('', '', '\n')
    b=[s.translate(rem) for s in among_list]
    print(b)
    n_l = []
    for i in b:
        out_df['Activity'] = out_df['Activity'].str.replace(re.escape(i),'')
    '''
    out_df= out_df.dropna(how='all')
    out_df['Activity'] = out_df['Activity'].str.replace('^[^a-zA-Z]*', '', regex=True)  # [B2]
    out_df = out_df[out_df['Activity'].str.len() > 0]
    out_df=out_df[~out_df['Activity'].str.lower().isin([x.lower() for x in suffix_list])]
    out_df.to_csv(output_csv)

#merge all events, events extracted from the event-specific notes and case notes
def get_all_events(general_events_file, specific_event_file, all_events):
    d1=pd.read_csv(general_events_file)
    d2=pd.read_csv(specific_event_file)
    d1=d1[["HADM_ID",	"Activity",	"Timestamp",	"Note"]]
    d2 = d2[["HADM_ID", "Activity", "Timestamp", "Note"]]

    d3 = pd.concat([d1, d2])

    d3['Timestamp'] = d3['Timestamp'].str.replace(re.escape("[**"), '')
    d3['Timestamp'] = d3['Timestamp'].str.replace(re.escape("**]"), '')
    d3['Timestamp'] = d3['Timestamp'].str.replace(re.escape("-"), '/')
    d3['Timestamp'] = d3['Timestamp'].str.replace(re.escape("at"), ' ')
    d3['Timestamp'] = d3['Timestamp'].str.replace(re.escape("**"), '')
    d3['Timestamp'] = [_norm_ts(t, n, h) for t, n, h in zip(d3['Timestamp'], d3['Note'], d3['HADM_ID'])]  # [G5]
    d3 = d3.dropna(subset=['Timestamp'])
    d3=d3.drop_duplicates()
    d3=d3.sort_values(['HADM_ID', 'Timestamp'], ascending=[True, True])
    d3.to_csv(all_events)

    
COLLECTION = "Note_collection"
def _norm_ts(t, note, case):  # [G5] GitHub date -> 'YYYY-MM-DD[ HH:MM:SS]'; year-less date takes the note's year
    t = str(t).strip()
    if re.match(r"20\d\d/\d\d/\d\d \d\d:\d\d:\d\d$", t): t = t.replace("/", "-")
    if re.match(r"20\d\d-\d\d-\d\d \d\d:\d\d:\d\d$", t): return t
    files = glob.glob(f"{COLLECTION}/{case}/*.txt") if note == "Description" else glob.glob(f"{COLLECTION}/{case}/{note}")
    year = open(files[0]).readline().split("Date/Time:")[1].strip()[:4] if files else ""
    try: d = pd.to_datetime(t.replace("/", "-") if re.search(r"20\d\d", t) else f"{t} {year}", utc=True, format="mixed")
    except Exception: return None
    return d.strftime("%Y-%m-%d %H:%M:%S") if re.search(r"\d:\d\d", t) else d.strftime("%Y-%m-%d")


def tag_NER_lookup(filepath, lookup_p1, lookup_p2, out_csv):
    # [G9] one general-English NER model; clinical models (en_core_sci_lg, en_ner_bc5cdr_md) dropped
    nlp_ = spacy.load("en_core_web_sm")

    # [G10] header lines written by prep_github.py: not note content, skip them
    HEADERS = ("date/time", "author", "title")
    def body(text):
        return "\n".join(l for l in text.split("\n") if not l.strip().lower().startswith(HEADERS))

    # [G11] lookup_p1 / lookup_p2 no longer used here: lookup phrases name events in
    # extract_specific_notes, so they are not added again as "hospital/medical activity" attributes

    df = pd.DataFrame()
    case_id, attribute, value, source = [], [], [], []
    folders = [f for f in listdir(filepath)]
    outputfile = open(out_csv, 'w')

    for dir in folders:
        for f in glob.glob(filepath + '/' + dir + "/*.txt"):
            with open(f, "r") as inputfile:
                raw = inputfile.read()
            text = body(raw).lower()

            # 1. Named entities (general English NER)
            doc1 = nlp_(text)
            ent_bc = {}
            for x in doc1.ents:
                ent_bc[x.text] = x.label_
            for key in ent_bc:
                case_id.append(dir)
                attribute.append(ent_bc[key])
                value.append(key)
                source.append(os.path.basename(f))

            # 2. "Name: value" lines, e.g. "pip version: 24.0"
            for line in body(raw).split("\n"):
                v = "\n".join([x.strip() for x in line.splitlines() if ": " in x])
                result = [x for x in re.split(r"\s{4,}", v) if x]
                for r in result:
                    name, var = r.partition(": ")[::2]
                    case_id.append(dir)
                    attribute.append(name)
                    value.append(var)
                    source.append(os.path.basename(f))

        # [G3] Discharge summary "Pertinent Results" block removed: no GitHub counterpart

    df['HADM_ID'] = case_id
    df['Entity'] = attribute
    df['Value'] = value
    df['Note'] = source
    df = df[df['Entity'].astype(str).str.len() > 1]
    df['Entity'] = df['Entity'].astype(str).str.replace('^[^a-zA-Z]*', '', regex=True)  # [B2]
    df.Entity = df.Entity.str.replace(' +', ' ', regex=True)  # [B2]
    df['Entity'] = df['Entity'].str.lower().str.strip()
    df_uni = df[df['Value'].notnull() & df['Entity'].notnull()].dropna()
    df_uni = df_uni.drop_duplicates(keep='first')
    df_uni.to_csv(outputfile)
    outputfile.close()
#apply dependency parsing and extract attributes  
def dep_parse_attribute(filepath, out_dep_csv):
    df = pd.DataFrame()
    case_id = []
    dep_p= []
    source = []

    folders = [f for f in listdir(filepath)]
    client = CoreNLPClient(annotators=['tokenize', 'ssplit', 'pos', 'depparse'], timeout=60000, memory='16G')  # [B4]
    client.start()  # [B4]

    for dir in folders:

        case_notes = ["/*_Description.txt"]  # [G3]

        for i in case_notes:
            for f in glob.glob(filepath + '/' + dir + str(i)):

                with open(f, "r+") as inputfile:

                    text = inputfile.read().split(".")
                    text.pop()
                    list_dep=[]
                    add_dp = ""
                    for k in text:

                        if len(k) > 3:

                            if True:  # [B4] was: with CoreNLPClient(...) as client  (new server per sentence)
                        # set up the client
                                add_dp = ""

                            # submit the request to the server
                                ann = client.annotate(str(k))

                            # get the first sentence
                                sentence = ann.sentence[0]


                            # get the dependency parse of the first sentence
                                dependency_parse = sentence.basicDependencies

                                token_dict = {}
                                for i in range(0, len(sentence.token)) :
                                    token_dict[sentence.token[i].tokenEndIndex] = sentence.token[i].word

                                #get a list of the dependencies with the words they connect
                                list_dep=[]
                                for i in range(0, len(dependency_parse.edge)):

                                    source_node = dependency_parse.edge[i].source
                                    source_name = token_dict[source_node]

                                    target_node = dependency_parse.edge[i].target
                                    target_name = token_dict[target_node]

                                    dep = dependency_parse.edge[i].dep

                                    list_dep.append((dep,
                                        str(source_node)+'-'+source_name,
                                        str(target_node)+'-'+target_name))

                                #print(list_dep)'''
                                    dp_r = ""
                                    for k in list_dep:
                                        if (k[0] == 'nsubj') or (k[0] == 'obl') or (k[0] == 'obj') or (k[0] == 'advmod') or (k[0] == 'compound') or (k[0] == 'acomp') or (k[0] == 'appos') or ( k[0] == 'neg') or (k[0] == 'nsubjpass') or (k[0] == 'nummod') or ( k[0] == 'obl:tmod'):
                                            dp_r = dp_r + str(k) + "***"

                        add_dp = add_dp + dp_r

                        case_id.append(dir)
                        dep_p.append(add_dp)
                        source.append(os.path.basename(f))

    df['HADM_ID']=case_id  # [B12] moved out of the loop
    df['Dependency']=dep_p
    df['Note']=source

    df = df.drop_duplicates()

    n_df=df.groupby(['HADM_ID', 'Note'], as_index=False).agg({'Dependency': ' '.join})
    n_df.to_csv(out_dep_csv)
    client.stop()  # [B4]
            

def extract_case_attributes(dependenc_csv, extracted_attr_csv,all_events_csv, all_case_att_csv):
    d1=pd.read_csv(dependenc_csv)
    d1=d1[d1['Note'].str.contains("Description")]  # [G3]
    d2=pd.read_csv(extracted_attr_csv)  # [B5] was undefined extracted_case_csv
    
    d3=pd.DataFrame()
    Entitiy_ls =[]
    value_ls=[]
    case_ls=[]
    for index, row in d1.iterrows():
        ea_list = str(row.Dependency).split('***')
        for i in ea_list:
            k = tuple(re.findall(r'[\w]+', i))
            if len(k) == 5:
                if (k[0] == 'nummod') :
                    Entitiy_ls.append(k[2])
                    value_ls.append(k[4])
                    case_ls.append(str(row.HADM_ID))
    d3['HADM_ID']= case_ls  # [B13] moved out of the loop
    d3['Entity']=Entitiy_ls
    d3['Value']=value_ls
    case_df=d2[d2['Note'].str.contains("Description.txt")]  # [G3]
    df_e=pd.read_csv(all_events_csv)
    events_l = df_e['Activity'].drop_duplicates().to_list()
    # [G12] MIMIC exclude lists removed ('admit', 'discharge', 'Date of Birth', '+2  Left:+2')
      

    new_df = pd.concat([case_df , d3])
  
    new_df=new_df.drop_duplicates(keep='first')
    new_df=new_df[new_df['Value'].notna()]
    new_df=new_df[new_df['Entity'].notna()]
    new_df=new_df.dropna(how='all')
    new_df=new_df[['HADM_ID','Entity', 'Value', 'Note']]
    new_df.to_csv(all_case_att_csv)


def extract_event_attributes( dependency_csv, extracted_attributes_csv, specific_events_csv, all_events_csv, all_event_att_csv ):

    d3=pd.DataFrame()

    ''' extract from dependency_csv
    e_df1=pd.read_csv(dependency_csv)
    e_df1['Source_edi']=e_df1['Note'].str.replace('^[^a-zA-Z]*', '', regex=True)  # [B2]
    e_df1['Source_edi']=e_df1['Source_edi'].str.replace('.txt', '')
    #print(e_df1)
    
    
    Entitiy_ls =[]
    value_ls=[]
    case_ls=[]
    for index, row in e_df1.iterrows():
        ea_list = str(row.Dependency).split('***')
        for i in ea_list:
            k = tuple(re.findall(r'[\w]+', i))
            if len(k) == 5:
                if (k[0] == 'nummod') :
                    Entitiy_ls.append(k[2])
                    value_ls.append(k[4])
                    case_ls.append(str(row.HADM_ID))
        d3['HADM_ID']= case_ls
        d3['Entity']=Entitiy_ls
        d3['Value']=value_ls
    e_df1 = e_df1[e_df1['Source_edi'].isin(event_notes)]
    '''
    event_notes=['Comment']  # [G3]
    e_df2=pd.read_csv(extracted_attributes_csv)
    e_df2['Source_edi']=e_df2['Note'].str.replace('^[^a-zA-Z]*', '', regex=True)  # [B2]
    e_df2['Source_edi']=e_df2['Source_edi'].str.replace('.txt', '')
    
    #print(e_df2)
    e_df2 = e_df2[e_df2['Source_edi'].isin(event_notes)]
    #print(e_df2)
    df_e=pd.read_csv(all_events_csv)
    events_l = df_e['Activity'].drop_duplicates().to_list()
    e_df2 = e_df2[~e_df2['Value'].isin(events_l)]
    new_df = pd.concat([e_df2 , d3])
    #print(new_df)
    new_df.dropna()
    e_df3=pd.read_csv(specific_events_csv)
    new_df=new_df.merge(e_df3, on=["Note", 'HADM_ID'])
    new_df = new_df[['HADM_ID','Activity', 'Timestamp', 'Entity', 'Value', "Note"]]

    new_df=new_df.drop_duplicates(keep='first')

    new_df.to_csv(all_event_att_csv)
 
def merge_attributes(all_case_att_csv,  list_case_attributes):
    d1 = pd.read_csv(all_case_att_csv)
  
    final_filtered_attr = ["pip version", "python version", "os"]  # [G13] was ["service", "sex", "date of birth"]
    d1["Value"]=d1["Value"].astype(str).str.strip()
    d1['Entity'] = d1['Entity'].str.strip()
    d1["Value"]=d1["Value"].str.lstrip()
    d1['Entity'] = d1['Entity'].str.lstrip()
    d1 = d1[['HADM_ID', 'Entity', 'Value']]
    d1=d1.drop_duplicates(keep='first')
    event_merge = d1.groupby(['HADM_ID', 'Entity'], as_index=False).agg(list)

    out_df_f = event_merge[~event_merge['Entity'].str.lower().isin([x.lower() for x in final_filtered_attr])]

    out_merg_f = event_merge[event_merge['Entity'].str.lower().isin([x.lower() for x in final_filtered_attr])]
    out_merg_f = out_merg_f[['HADM_ID', 'Entity', 'Value']]
    out_df_f = out_df_f.groupby('HADM_ID').apply(lambda x: dict(zip(x['Entity'], x['Value']))).reset_index().rename(
        columns={"HADM_ID": "HADM_ID", 0: "Other_info"})

    out_df_ff = out_df_f.melt(id_vars="HADM_ID")
    out_df_ff = out_df_ff.rename(columns={'variable': 'Entity', 'value': 'Value'})
    
    out_df_f = pd.concat([out_df_ff, out_merg_f])
    out_df_f.to_csv(list_case_attributes)

def delete_garbage_files():
    file_list=["./output1.csv", "./specific_events.csv", "./all_events.csv", "./all_attributes.csv" , "./echo_events.csv","./radio_events.csv","./case_attr_final.csv", "./event_attr_final.csv" ]
    for i in file_list:
        if(os.path.exists(i) and os.path.isfile(i)):
            os.remove(i)
            print("file deleted")


if __name__ == '__main__':
    C = COLLECTION  # [G3] paths
    LOOKUP.extend(pd.read_csv("lookup_github_activity.tsv", sep="\t", names=["p", "a"], comment="#").itertuples(index=False, name=None))  # This lookup is a deviation
    apply_regex_rules(C, "extracted_events.csv")
    extract_specific_notes(C, "specific_events.csv") # deviation because of the lookup_github_activity.tsv file
    refine_events("extracted_events.csv", "exclude_list.txt", "stopwords.txt", "refined_events.csv") #stopwords.txt is not used in the current version of the code neither was it used in the original code. It was used in the previous version of the code to remove stopwords from the extracted events. The stopwords.txt file contains a list of common English words that are not relevant to the events being extracted. The refine_events function uses this list to filter out any events that contain these stopwords. However, in the current version of the code, this functionality has been removed and the stopwords.txt file is no longer used.
    get_all_events("refined_events.csv", "specific_events.csv", "all_events.csv")
    tag_NER_lookup(C, 'lookup_github_activity.txt', 'lookup_technical_object.txt', 'all_attributes.csv')
    dep_parse_attribute(C, "all_dependency.csv")
    extract_case_attributes("all_dependency.csv", "all_attributes.csv", 'all_events.csv', "case_attr_final.csv")
    extract_event_attributes("all_dependency.csv", "all_attributes.csv", 'specific_events.csv', 'all_events.csv', "event_attr_final.csv")
    # [G6] extract_echo_event_attr, extract_radiology_event_attr, extract_event_attr_event_notes removed (MIMIC Echo/Radiology header fields)
    merge_attributes("case_attr_final.csv", "case_attr_final_list.csv")