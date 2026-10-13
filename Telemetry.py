import datetime as dt
import json
import os
import random
import sys
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "Harshil0207")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "dist"

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Inter','Helvetica Neue',Arial,'DejaVu Sans',sans-serif"
MONO = "ui-monospace,'SF Mono','JetBrains Mono',Consolas,'DejaVu Sans Mono',monospace"
THEMES = {
    "dark": dict(fg="#f0f6fc", muted="#9198a1", faint="#656c76", line="#262c36", accent="#3fb950", bar="#2f353d"),
    "light": dict(fg="#1f2328", muted="#59636e", faint="#818b98", line="#d8dee4", accent="#1a7f37", bar="#d1d9e0"),
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-telemetry"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def mock():
    today = dt.date.today()
    days = [{"date": (today - dt.timedelta(days=i)).isoformat(), "contributionCount": random.choice([0, 0, 1, 3, 5, 8, 12, 2, 6])} for i in range(364, -1, -1)]
    langs = [("JavaScript", "#f1e05a", 780), ("TypeScript", "#3178c6", 146), ("Python", "#3572A5", 34), ("CSS", "#663399", 19), ("HTML", "#e34c26", 13)]
    return {
        "repositories": {"totalCount": 46, "nodes": [{"languages": {"edges": [{"size": s, "node": {"name": n, "color": c}} for n, c, s in langs]}}]},
        "contributionsCollection": {"totalCommitContributions": 812, "contributionCalendar": {"totalContributions": 1043, "weeks": [{"contributionDays": days[i:i + 7]} for i in range(0, 365, 7)]}},
    }


def streaks(counts):
    longest = run = 0
    for v in counts:
        run = run + 1 if v > 0 else 0
        longest = max(longest, run)
    cur, i = 0, len(counts) - 1
    if counts and counts[i] == 0:
        i -= 1
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    return cur, longest


def render(u, c):
    cc = u["contributionsCollection"]
    days = sorted((d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]), key=lambda d: d["date"])
    cur, longest = streaks([d["contributionCount"] for d in days])
    langs = {}
    for n in u["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            langs.setdefault(e["node"]["name"], [0, e["node"]["color"] or c["muted"]])
            langs[e["node"]["name"]][0] += e["size"]
    total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]

    W = 1200
    stats = [
        (f'{cc["contributionCalendar"]["totalContributions"]:,}', "Contributions this year"),
        (f'{cc["totalCommitContributions"]:,}', "Commits this year"),
        (f"{cur}", "Day streak right now"),
        (f"{longest}", "Longest streak"),
        (f'{u["repositories"]["totalCount"]}', "Public repositories"),
    ]
    sw = W / len(stats)
    out = []
    for i, (v, label) in enumerate(stats):
        x = i * sw
        out.append(f'<g class="f" style="animation-delay:{i * .06:.2f}s"><text x="{x}" y="52" font-family="{SANS}" font-size="44" font-weight="650" letter-spacing="-1.5" fill="{c["fg"]}">{escape(v)}</text>'
                   f'<text x="{x + 2}" y="82" font-family="{SANS}" font-size="15" fill="{c["muted"]}">{label}</text></g>')
    out.append(f'<line x1="0" y1="118" x2="{W}" y2="118" stroke="{c["line"]}"/>')

    last = days[-30:]
    mx = max([d["contributionCount"] for d in last] + [1])
    y0, ch = 168, 120
    out.append(f'<text x="0" y="156" font-family="{SANS}" font-size="15" fill="{c["muted"]}">Daily activity · last 30 days</text>')
    out.append(f'<text x="{W}" y="156" text-anchor="end" font-family="{SANS}" font-size="15" fill="{c["muted"]}">{sum(d["contributionCount"] for d in last)} contributions</text>')
    bw = W / len(last)
    for i, d in enumerate(last):
        v = d["contributionCount"]
        bh = max(3, ch * v / mx)
        col = c["accent"] if i == len(last) - 1 else (c["muted"] if v else c["bar"])
        op = 1 if i == len(last) - 1 else (0.85 if v else 1)
        out.append(f'<rect class="g" style="animation-delay:{0.2 + i * 0.015:.3f}s" x="{i * bw + 3:.1f}" y="{y0 + 14 + ch - bh:.1f}" width="{bw - 6:.1f}" height="{bh:.1f}" rx="2" fill="{col}" fill-opacity="{op}"/>')
    for i in (0, 14, 29):
        out.append(f'<text x="{i * bw + bw / 2:.1f}" y="{y0 + ch + 38}" text-anchor="middle" font-family="{SANS}" font-size="13" fill="{c["faint"]}">{dt.date.fromisoformat(last[i]["date"]).strftime("%d %b")}</text>')

    ly = y0 + ch + 76
    out.append(f'<line x1="0" y1="{ly - 26}" x2="{W}" y2="{ly - 26}" stroke="{c["line"]}"/>')
    out.append(f'<text x="0" y="{ly + 4}" font-family="{SANS}" font-size="15" fill="{c["muted"]}">Languages</text>')
    acc = 0
    bx, bwid = 120, W - 120
    for name, (size, col) in top:
        wseg = bwid * size / total
        out.append(f'<rect x="{bx + acc:.1f}" y="{ly - 6}" width="{max(wseg - 3, 2):.1f}" height="8" rx="4" fill="{col}"/>')
        acc += wseg
    lx = bx
    for name, (size, col) in top:
        label = f"{name} {100 * size / total:.0f}%"
        out.append(f'<circle cx="{lx + 5}" cy="{ly + 30}" r="5" fill="{col}"/><text x="{lx + 16}" y="{ly + 35}" font-family="{SANS}" font-size="14.5" fill="{c["fg"]}">{escape(label)}</text>')
        lx += len(label) * 8.2 + 44
    H = ly + 54
    style = "<style>.f{opacity:0;animation:f .7s ease-out forwards}@keyframes f{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:g .6s cubic-bezier(.2,.7,.2,1) forwards}@keyframes g{to{transform:scaleY(1)}}</style>"
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{style}{"".join(out)}</svg>'


if __name__ == "__main__":
    data = mock() if "--mock" in sys.argv else fetch()
    os.makedirs(OUT_DIR, exist_ok=True)
    for t, c in THEMES.items():
        p = os.path.join(OUT_DIR, f"activity-{t}.svg")
        with open(p, "w", encoding="utf-8") as f:
            f.write(render(data, c))
        print("wrote", p)