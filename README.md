# Text2EL+ on GitHub issue data

Replication of **Text2EL+** (Kapugama Geeganage et al., *ACM JDIQ* 16(1), 2024) on a new domain:
GitHub issues of [`pypa/pip`](https://github.com/pypa/pip/issues).
It is adapted here so that the
structured event log comes from GitHub's issue events, and the unstructured text comes from
issue descriptions and comments.


## Data (not included)

Put these files in this folder called dataset

| File | Content |
|---|---|
| `issues.csv` | issues of pypa/pip (number, title, body, created_at, labels) |
| `events.csv` | issue timeline events (opened, labeled, closed, ...) |
| `comments.csv` | issue comments (issue number, body, created_at) |
| `wiki_unigrams.bin` | sent2vec model, from https://github.com/epfml/sent2vec | -- Outside the folder in root folder

## Setting up the environment

Requires Python 3.10/3.11, Java 8+ and Stanford CoreNLP 4.4.0.

```
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

sent2vec is not on PyPI. Install it from source:

```
pip install git+https://github.com/epfml/sent2vec.git
```

Download Stanford CoreNLP 4.4.0 from https://stanfordnlp.github.io/CoreNLP/ and set its path
in line 22 of `extract_events_attributes.py`.


## Running

Activate the environment each time (`source .venv/bin/activate`), then run:


python3 prep_github.py                       # note collection + structured event log
python3 extract_events_attributes.py         # Phase 1: extract events and attributes
python3 verify_events.py wiki_unigrams.bin   # Phase 2: verify and enrich
mkdir -p results_wiki && cp semantic_similariy.csv matched_events*.csv timestamp_updated*.csv enhanced_log.csv eventlog.xes enhanced_eventlog.xes results_wiki/
python3 discover_process.py 13372 13392   

