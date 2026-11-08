
import sys
import numpy as np
import pandas as pd
import pm4py


def cid(s):
    """Issue numbers as clean strings ('13392', not '13392.0')."""
    return pd.to_numeric(s, errors="coerce").astype("Int64").astype(str)


def tidy(d):
    return pd.DataFrame({"case": cid(d.HADM_ID).values,
                         "activity": d.Activity.astype(str).values,
                         "time": pd.to_datetime(d.Timestamp, utc=True, format="mixed").values})


def fmt(d):
    d = d.rename(columns={"case": "case:concept:name", "activity": "concept:name", "time": "time:timestamp"}).copy()
    return pm4py.format_dataframe(d, case_id="case:concept:name", activity_key="concept:name",
                                  timestamp_key="time:timestamp")


def draw(d, fname):
    """Directly-follows graph: box number = how often the activity occurs, arrow number = how often
    one activity directly follows the other (same reading as Fig. 13)."""
    dfg, sa, ea = pm4py.discover_dfg(d)
    pm4py.save_vis_dfg(dfg, sa, ea, fname, rankdir="LR")


out = sys.argv[1] if len(sys.argv) > 1 else "."
cases = [c.strip() for c in sys.argv[2:]]

enh_path = os.path.join(out, "enhanced_log.csv")
for p in ("event_log_evaluation.csv", enh_path):
    if not os.path.exists(p):
        found = [os.path.join(r, f) for r, _, fs in os.walk(".") for f in fs if f == os.path.basename(p)]
        print(f"Cannot find {p} (running in {os.getcwd()}).")
        print("Found here instead: " + (", ".join(found) if found else "nowhere below this folder"))
        print("Run the script from the folder with event_log_evaluation.csv and give the results folder, e.g.\n"
              "   python3 discover_cases.py results_wiki 13392 13657")
        sys.exit(1)
before = tidy(pd.read_csv("event_log_evaluation.csv"))
after = tidy(pd.read_csv(enh_path))
n_old = len(before)
is_new = np.arange(len(after)) >= n_old
after.loc[is_new, "activity"] = "[" + after.loc[is_new, "activity"].str.capitalize() + "]"
print(f"before: event_log_evaluation.csv, {n_old} events | "
      f"after: {out}/enhanced_log.csv, {len(after)} events ({is_new.sum()} new)")

# Sanity check: the first n_old rows of the enhanced log should be the original log.
head = after.iloc[:n_old]
same = (head.case.values == before.case.values) & (head.activity.values == before.activity.values)
if not same.all():
    print(f"WARNING: {(~same).sum()} of the first {n_old} enhanced rows differ in issue/activity from "
          f"event_log_evaluation.csv, so the new events may not simply be appended. Check before using.")
moved = same & (head.time.values != before.time.values)
if moved.any():
    print(f"Phase 2 changed the timestamp of {moved.sum()} original event(s) (kept in the 'after' log).")

if not cases:
    print("No issue numbers given. Issues with the most new events from Phase 2:")
    counts = after[is_new].case.value_counts().head(15)
    for c, n in counts.items():
        print(f"   {c}: {n} new event(s), {int((before.case == c).sum())} logged events")
    print(f"Rerun as: python3 discover_cases.py {out} <issue> <issue> ...")
    sys.exit()

missing = [c for c in cases if c not in set(before.case)]
if missing:
    print("Not in the log (check the numbers):", ", ".join(missing))
    cases = [c for c in cases if c not in missing]
    if not cases:
        sys.exit()

tag = "_".join(cases) if len(cases) <= 3 else f"{len(cases)}cases"
for name, d in [("before", before), ("after", after)]:
    d = fmt(d[d.case.isin(cases)])
    print(f"{name}: {len(d)} events, {d['case:concept:name'].nunique()} issues, "
          f"{d['concept:name'].nunique()} activities")
    for ext in ("png", "pdf"):  # png to look at, pdf (vector) for the LaTeX report
        draw(d, os.path.join(out, f"map_{name}_{tag}.{ext}"))

# Trace table: every event of each chosen issue in the 'after' log, in time order
t = after[after.case.isin(cases)].copy()
t["source"] = np.where(is_new[after.case.isin(cases).values], "text (new, Phase 2)", "GitHub log")
for k in np.where(moved)[0]:  # flag original events whose timestamp Phase 2 changed
    if after.case.iloc[k] in cases:
        t.loc[t.index == after.index[k], "source"] = f"GitHub log (time changed, was {before.time.iloc[k]:%H:%M:%S})"
t = t.sort_values(["case", "time"], kind="stable")
t.to_csv(os.path.join(out, f"traces_{tag}.csv"), index=False)
for c, g in t.groupby("case", sort=False):
    n_new = (g.source == "text (new, Phase 2)").sum()
    print(f"\nIssue {c}: {len(g) - n_new} logged + {n_new} new")
    for _, r in g.iterrows():
        print(f"   {r.time:%Y-%m-%d %H:%M:%S}  {r.activity:<40} {r.source}")
print(f"\nMaps and traces written to {out}/ (map_before_{tag}, map_after_{tag}, traces_{tag}.csv)")