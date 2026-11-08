

import csv, json, os, urllib.request

REPO = "pypa/pip"
MAX_ISSUES = 250
TOKEN = os.environ.get("GITHUB_TOKEN")


def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req) as r:
        links = r.headers.get("Link", "")
        items = json.loads(r.read())
    nxt = next((l.split(";")[0].strip(" <>") for l in links.split(",") if 'rel="next"' in l), None)
    return items, nxt


def get(url):
    """Get all pages."""
    items = []
    while url:
        page, url = fetch(url)
        items += page
    return items


def save(name, rows):
    with open(name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


# 1. Issues (the API also returns pull requests, so drop those)
issues, url = [], f"https://api.github.com/repos/{REPO}/issues?state=closed&per_page=100"
while url and len(issues) < MAX_ISSUES:
    page, url = fetch(url)
    issues += [i for i in page if "pull_request" not in i]
issues = issues[:MAX_ISSUES]

# 2. Timeline of each issue (contains both the events and the comments)
issue_rows, event_rows, comment_rows = [], [], []
for k, i in enumerate(issues, 1):
    n = i["number"]
    print(f"[{k}/{len(issues)}] issue #{n}")
    issue_rows.append({
        "issue_number": n,
        "title": i["title"],
        "body": i["body"] or "",
        "user": i["user"]["login"],
        "created_at": i["created_at"],
        "closed_at": i["closed_at"],
        "labels": ";".join(l["name"] for l in i["labels"]),
    })
    for e in get(f"https://api.github.com/repos/{REPO}/issues/{n}/timeline?per_page=100"):
        if e.get("event") == "commented":
            comment_rows.append({
                "issue_number": n,
                "comment_id": e["id"],
                "user": (e.get("user") or {}).get("login", ""),
                "created_at": e["created_at"],
                "body": e.get("body") or "",
            })
        elif e.get("created_at"):
            event_rows.append({
                "issue_number": n,
                "event": e["event"],
                "actor": (e.get("actor") or {}).get("login", ""),
                "created_at": e["created_at"],
                "label": (e.get("label") or {}).get("name", ""),
                "assignee": (e.get("assignee") or {}).get("login", ""),
            })

save("issues.csv", issue_rows)
save("events.csv", event_rows)
save("comments.csv", comment_rows)