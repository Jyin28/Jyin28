"""Generate a gamer-style trophy SVG for a GitHub profile.

Uses only the Python standard library and the GitHub GraphQL API.
Env vars: GH_TOKEN (required), GH_USER (required), OUT (default profile/trophy.svg)
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape

API = "https://api.github.com/graphql"
TOKEN = os.environ.get("GH_TOKEN", "")
USER = os.environ.get("GH_USER", "")
OUT = os.environ.get("OUT", "profile/trophy.svg")

RANKS = ["SSS", "SS", "S", "AAA", "AA", "A", "B", "C"]
COLORS = {
    "SSS": ("#FF4F9A", "#FFD1E6"), "SS": ("#FF4F9A", "#FFD1E6"), "S": ("#C239B3", "#F3C6EE"),
    "AAA": ("#FFD700", "#FFF3B0"), "AA": ("#FFD700", "#FFF3B0"), "A": ("#FFD700", "#FFF3B0"),
    "B": ("#C0C0C0", "#EEEEEE"), "C": ("#CD7F32", "#F2D2B3"), "?": ("#555566", "#888899"),
}
TROPHIES = [  # (title, key, thresholds for SSS..C)
    ("Commits", "commits", [4000, 2000, 1000, 500, 200, 100, 10, 1]),
    ("Repositories", "repos", [50, 45, 40, 35, 30, 20, 10, 1]),
    ("Stars", "stars", [2000, 700, 200, 100, 50, 30, 10, 1]),
    ("Followers", "followers", [1000, 400, 200, 100, 50, 20, 10, 1]),
    ("Pull Requests", "prs", [1000, 500, 200, 100, 50, 20, 10, 1]),
    ("Issues", "issues", [1000, 500, 200, 100, 50, 20, 10, 1]),
    ("Languages", "langs", [10, 8, 7, 6, 5, 4, 2, 1]),
    ("Experience", "years", [10, 7, 5, 4, 3, 2, 1, 0]),
]
LABELS = {
    "commits": "Commits", "repos": "Repos", "stars": "Stars", "followers": "Followers",
    "prs": "PRs", "issues": "Issues", "langs": "Languages", "years": "Years",
}


def gql(query, variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "trophy-script"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if body.get("errors"):
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]


def fetch_stats(login):
    q = """
    query($login: String!, $cursor: String) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        pullRequests { totalCount }
        issues { totalCount }
        contributionsCollection { contributionYears }
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $cursor) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes { stargazerCount languages(first: 20) { nodes { name } } }
        }
      }
    }"""
    stars, langs, cursor = 0, set(), None
    while True:
        u = gql(q, {"login": login, "cursor": cursor})["user"]
        repos = u["repositories"]
        for n in repos["nodes"]:
            stars += n["stargazerCount"]
            langs.update(l["name"] for l in n["languages"]["nodes"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]

    commits = 0
    yq = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions restrictedContributionsCount
        }
      }
    }"""
    for y in u["contributionsCollection"]["contributionYears"]:
        c = gql(yq, {"login": login, "from": f"{y}-01-01T00:00:00Z", "to": f"{y}-12-31T23:59:59Z"})
        cc = c["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]

    created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    years = (datetime.now(timezone.utc) - created).days // 365
    return {
        "commits": commits, "repos": repos["totalCount"], "stars": stars,
        "followers": u["followers"]["totalCount"], "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"], "langs": len(langs), "years": years,
    }


def rank_for(value, thresholds):
    for rank, t in zip(RANKS, thresholds):
        if value >= t and (t > 0 or value > 0 or rank == "C"):
            return rank
    return "?"


def cup(x, y, main, light):
    return f"""
    <g transform="translate({x},{y})">
      <path d="M-22,-24 h44 v10 a22,22 0 0 1 -44,0 z" fill="{main}"/>
      <path d="M-16,-20 h8 v8 a10,10 0 0 0 4,8 a16,16 0 0 1 -12,-16 z" fill="{light}" opacity="0.7"/>
      <path d="M-22,-20 h-8 a9,9 0 0 0 9,14" fill="none" stroke="{main}" stroke-width="4"/>
      <path d="M22,-20 h8 a9,9 0 0 1 -9,14" fill="none" stroke="{main}" stroke-width="4"/>
      <rect x="-4" y="6" width="8" height="10" fill="{main}"/>
      <rect x="-14" y="16" width="28" height="7" rx="2" fill="{main}"/>
    </g>"""


def render(stats):
    cols, w, h, gap = 4, 150, 170, 14
    rows = (len(TROPHIES) + cols - 1) // cols
    W, H = cols * w + (cols - 1) * gap, rows * h + (rows - 1) * gap
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
             <stop offset="0" stop-color="#1A0B2E"/><stop offset="1" stop-color="#2D0B3A"/></linearGradient></defs>
             <style>text{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif}
             .t{font-size:14px;font-weight:700;fill:#FFFFFF}.v{font-size:12px;fill:#C9B8E8}
             .r{font-size:13px;font-weight:800}</style>"""]
    for i, (title, key, thr) in enumerate(TROPHIES):
        val = stats[key]
        rank = rank_for(val, thr)
        main, light = COLORS[rank]
        x, y = (i % cols) * (w + gap), (i // cols) * (h + gap)
        cx = x + w / 2
        parts.append(f'<rect x="{x+1}" y="{y+1}" width="{w-2}" height="{h-2}" rx="10" fill="url(#bg)" stroke="{main}" stroke-opacity="0.6" stroke-width="2"/>')
        parts.append(f'<rect x="{cx-22}" y="{y+12}" width="44" height="20" rx="10" fill="{main}" fill-opacity="0.2"/>')
        parts.append(f'<text class="r" x="{cx}" y="{y+27}" text-anchor="middle" fill="{main}">{rank}</text>')
        parts.append(cup(cx, y + 78, main, light))
        parts.append(f'<text class="t" x="{cx}" y="{y+132}" text-anchor="middle">{escape(title)}</text>')
        parts.append(f'<text class="v" x="{cx}" y="{y+152}" text-anchor="middle">{val} {LABELS[key]}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    if os.environ.get("DEMO"):
        data = {"commits": 312, "repos": 6, "stars": 2, "followers": 4, "prs": 12,
                "issues": 0, "langs": 9, "years": 2}
    else:
        if not TOKEN or not USER:
            sys.exit("GH_TOKEN and GH_USER are required")
        data = fetch_stats(USER)
    print(json.dumps(data))
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(data))
    print(f"Wrote {OUT}")
