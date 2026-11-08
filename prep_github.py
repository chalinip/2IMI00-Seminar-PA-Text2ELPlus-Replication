# Convert the 3 GitHub CSVs into the layout Text2EL expects
#   Note_collection/<issue>/<id>_Description.txt  (case note, like a Discharge summary)
#   Note_collection/<issue>/<id>_Comment.txt      (event-specific note, like Echo: header with Date/Time)
#   event_log_evaluation.csv                      (HADM_ID, Activity, Timestamp)  <- structured log
import os, re, sys, pandas as pd
CLEAN = '--raw' not in sys.argv
def clean(t):
    t = t if isinstance(t, str) else ''
    if not CLEAN: return t
    t = re.sub(r'<!--.*?-->', '', t, flags=re.S)                    # template instructions
    t = re.sub(r'```.*?```', ' ', t, flags=re.S)                     # code blocks / tracebacks
    t = re.sub(r'<details>.*?</details>', ' ', t, flags=re.S | re.I)
    t = re.sub(r'^\s*>.*$', '', t, flags=re.M)                       # quoted earlier comments
    # issue-template sections '### pip version\n\n26.2.1' -> 'pip version: 26.2.1' (MIMIC 'Sex:   M' style)
    t = re.sub(r'^###\s+(.+?)\s*\n+\s*([^\n#][^\n]{0,80})\s*$', lambda m: f'{m.group(1)}: {m.group(2)}', t, flags=re.M)
    return t
ts = lambda s: pd.to_datetime(s, utc=True).strftime('%Y-%m-%d %H:%M:%S')
i = pd.read_csv('issues.csv'); c = pd.read_csv('comments.csv'); e = pd.read_csv('events.csv')
out = 'Note_collection'
for _, r in i.iterrows():
    os.makedirs(f'{out}/{r.issue_number}', exist_ok=True)
    open(f'{out}/{r.issue_number}/{r.issue_number}_Description.txt', 'w', encoding='utf-8').write(
        f"Date/Time: {ts(r.created_at)}\nTitle: {r.title}\n\n{clean(r.body)}")
for _, r in c.iterrows():
    if str(r.user).endswith('[bot]'): continue
    open(f'{out}/{r.issue_number}/{r.comment_id}_Comment.txt', 'w', encoding='utf-8').write(
        f"Date/Time: {ts(r.created_at)}\nAuthor: {r.user}\n\n{clean(r.body)}")
# structured event log (drop notification noise; add 'opened')
NOISE = {'subscribed', 'unsubscribed', 'mentioned'}
e = e[~e.event.isin(NOISE)].copy()
def act(r):
    if r.event == 'labeled':   return f'label added {r.label}'
    if r.event == 'unlabeled': return f'label removed {r.label}'
    return r.event.replace('_', ' ')
log = pd.concat([pd.DataFrame({'HADM_ID': i.issue_number, 'Activity': 'opened', 'Timestamp': i.created_at.map(ts)}),
                 pd.DataFrame({'HADM_ID': e.issue_number, 'Activity': e.apply(act, axis=1), 'Timestamp': e.created_at.map(ts)})])
log = log.sort_values(['HADM_ID', 'Timestamp'])
log.to_csv('event_log_evaluation.csv', index=False)
print('notes:', sum(len(f) for _, _, f in os.walk(out)), '| log events:', len(log), '| activities:', log.Activity.nunique())
