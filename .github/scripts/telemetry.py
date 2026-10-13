import datetime as dt
import json
import os
import random
import sys
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "Harshil0207")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "dist/telemetry.svg"

BG, PANEL, LINE = "#06070b", "#0b0d14", "#1b1f2e"
TEXT, MUTED, DIM = "#e8eaf2", "#8a90a3", "#4a5068"
CYAN, VIOLET, LIME, AMBER, PINK = "#22d3ee", "#a78bfa", "#a3e635", "#fbbf24", "#f472b6"
MONO = "'JetBrains Mono','SF Mono','Cascadia Code',Consolas,'DejaVu Sans Mono',monospace"
SANS = "'Segoe UI','Inter',system-ui,-apple-system,'Helvetica Neue','DejaVu Sans',sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "hg-os-telemetry"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def mock():
    today = dt.date.today()
    days = [{"date": (today - dt.timedelta(days=i)).isoformat(), "contributionCount": random.choice([0, 0, 1, 3, 5, 8, 12, 2, 6])} for i in range(364, -1, -1)]
    weeks = [{"contributionDays": days[i:i + 7]} for i in range(0, len(days), 7)]
    langs = [("JavaScript", "#f1e05a", 780), ("TypeScript", "#3178c6", 146), ("Python", "#3572A5", 34), ("CSS", "#663399", 19), ("HTML", "#e34c26", 13), ("C", "#555555", 1)]
    return {
        "repositories": {"totalCount": 46, "nodes": [{"stargazerCount": 1, "languages": {"edges": [{"size": s, "node": {"name": n, "color": c}} for n, c, s in langs]}}]},
        "contributionsCollection": {"totalCommitContributions": 812, "totalPullRequestContributions": 14, "contributionCalendar": {"totalContributions": 1043, "weeks": weeks}},
    }


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    cur = 0
    i = len(counts) - 1
    if counts and counts[i] == 0:
        i -= 1
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    return cur, longest


def render(u):
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    cur, longest = streaks(days)
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
    langs = {}
    for n in u["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            name = e["node"]["name"]
            langs.setdefault(name, [0, e["node"]["color"] or MUTED])
            langs[name][0] += e["size"]
    total_l = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]

    tiles = [
        ("CONTRIBUTIONS", f'{cc["contributionCalendar"]["totalContributions"]:,}', "last 12 months", CYAN),
        ("COMMITS", f'{cc["totalCommitContributions"]:,}', "last 12 months", VIOLET),
        ("CURRENT STREAK", f"{cur}d", "days in a row", LIME),
        ("LONGEST STREAK", f"{longest}d", "best run this year", AMBER),
        ("PUBLIC REPOS", f'{u["repositories"]["totalCount"]}', f"{stars} star" + ("" if stars == 1 else "s"), PINK),
    ]
    W = 1200
    tw = (W - 4 * 16) / 5
    parts = []
    for i, (label, val, sub, col) in enumerate(tiles):
        x = i * (tw + 16)
        parts.append(
            f'<g class="up" style="animation-delay:{i * 0.08:.2f}s">'
            f'<rect x="{x + 0.5}" y="0.5" width="{tw - 1}" height="131" rx="14" fill="{PANEL}" stroke="{LINE}"/>'
            f'<rect x="{x + 18}" y="20" width="22" height="3" rx="1.5" fill="{col}"/>'
            f'<text x="{x + 18}" y="46" font-family="{MONO}" font-size="11.5" fill="{MUTED}" letter-spacing="2">{label}</text>'
            f'<text x="{x + 18}" y="92" font-family="{SANS}" font-size="38" font-weight="800" fill="{TEXT}">{escape(val)}</text>'
            f'<text x="{x + 18}" y="116" font-family="{MONO}" font-size="11.5" fill="{DIM}">{escape(sub)}</text></g>'
        )

    last = days[-30:]
    cx0, cy0, cw, ch = 0, 152, 780, 290
    px0, px1, py0, py1 = cx0 + 34, cx0 + cw - 30, cy0 + 70, cy0 + ch - 46
    mx = max([d["contributionCount"] for d in last] + [1])
    pts = []
    for i, d in enumerate(last):
        x = px0 + (px1 - px0) * i / max(len(last) - 1, 1)
        y = py1 - (py1 - py0) * d["contributionCount"] / mx
        pts.append((x, y, d))
    line = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}" for i, (x, y, _) in enumerate(pts))
    area = line + f" L{pts[-1][0]:.1f} {py1} L{pts[0][0]:.1f} {py1} Z"
    grid = "".join(f'<line x1="{px0}" y1="{py0 + (py1 - py0) * k / 4:.1f}" x2="{px1}" y2="{py0 + (py1 - py0) * k / 4:.1f}" stroke="{LINE}" stroke-dasharray="2 6"/>' for k in range(5))
    ylab = "".join(f'<text x="{px0 - 10}" y="{py0 + (py1 - py0) * k / 4 + 4:.1f}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{DIM}">{round(mx * (4 - k) / 4)}</text>' for k in range(5))
    xlab = "".join(
        f'<text x="{x:.1f}" y="{py1 + 24}" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{DIM}">{dt.date.fromisoformat(d["date"]).strftime("%d %b").upper()}</text>'
        for i, (x, y, d) in enumerate(pts) if i % 5 == 0 or i == len(pts) - 1
    )
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3.2 if d["contributionCount"] else 2}" fill="{PINK if d["contributionCount"] else DIM}"/>' for x, y, d in pts)
    lx, ly = pts[-1][0], pts[-1][1]
    month_total = sum(d["contributionCount"] for d in last)
    parts.append(
        f'<rect x="{cx0 + 0.5}" y="{cy0 + 0.5}" width="{cw - 1}" height="{ch - 1}" rx="14" fill="{PANEL}" stroke="{LINE}"/>'
        f'<text x="{cx0 + 24}" y="{cy0 + 36}" font-family="{MONO}" font-size="12.5" font-weight="700" fill="{CYAN}" letter-spacing="2.5">DAILY ACTIVITY</text>'
        f'<text x="{cx0 + 182}" y="{cy0 + 36}" font-family="{MONO}" font-size="12" fill="{DIM}" letter-spacing="2">// LAST 30 DAYS</text>'
        f'<text x="{cx0 + cw - 24}" y="{cy0 + 36}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MUTED}">{month_total} contributions</text>'
        f'{grid}{ylab}<path d="{area}" fill="url(#ar)"/><path class="draw" d="{line}" fill="none" stroke="{CYAN}" stroke-width="2.2" stroke-linejoin="round" pathLength="1"/>{dots}{xlab}'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="6" fill="none" stroke="{CYAN}" class="ping"/>'
    )

    lx0, lw = cx0 + cw + 16, W - (cx0 + cw + 16)
    bar_x, bar_w, acc = lx0 + 24, lw - 48, 0
    seg = []
    for name, (size, col) in top:
        wseg = bar_w * size / total_l
        seg.append(f'<rect x="{bar_x + acc:.1f}" y="{cy0 + 62}" width="{max(wseg - 2, 1.5):.1f}" height="10" rx="2" fill="{col}"/>')
        acc += wseg
    rows = []
    for i, (name, (size, col)) in enumerate(top):
        y = cy0 + 108 + i * 28
        pct = 100 * size / total_l
        rows.append(
            f'<circle cx="{lx0 + 30}" cy="{y - 4}" r="4.5" fill="{col}"/>'
            f'<text x="{lx0 + 44}" y="{y}" font-family="{MONO}" font-size="13" fill="{TEXT}">{escape(name)}</text>'
            f'<text x="{lx0 + lw - 24}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="13" fill="{MUTED}">{pct:.1f}%</text>'
        )
    parts.append(
        f'<rect x="{lx0 + 0.5}" y="{cy0 + 0.5}" width="{lw - 1}" height="{ch - 1}" rx="14" fill="{PANEL}" stroke="{LINE}"/>'
        f'<text x="{lx0 + 24}" y="{cy0 + 36}" font-family="{MONO}" font-size="12.5" font-weight="700" fill="{VIOLET}" letter-spacing="2.5">LANGUAGE MIX</text>'
        f'<rect x="{bar_x}" y="{cy0 + 62}" width="{bar_w}" height="10" rx="2" fill="{LINE}"/>{"".join(seg)}{"".join(rows)}'
    )

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    H = cy0 + ch + 30
    parts.append(f'<text x="2" y="{H - 6}" font-family="{MONO}" font-size="11" fill="{DIM}" letter-spacing="2">● UPDATED {stamp} · REFRESHES EVERY 12H</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.35"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient></defs>
<style>
.up{{opacity:0;animation:up .6s ease-out forwards}} @keyframes up{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
.draw{{stroke-dasharray:1;stroke-dashoffset:1;animation:d 2.2s .3s ease-out forwards}} @keyframes d{{to{{stroke-dashoffset:0}}}}
.ping{{transform-box:fill-box;transform-origin:center;animation:p 1.8s ease-out infinite}} @keyframes p{{from{{transform:scale(.6);opacity:1}}to{{transform:scale(2.6);opacity:0}}}}
</style>
{"".join(parts)}
</svg>'''


if __name__ == "__main__":
    data = mock() if "--mock" in sys.argv else fetch()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(data))
    print("wrote", OUT)
