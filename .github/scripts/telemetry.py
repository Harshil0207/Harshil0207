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
TEXT, MUTED, FAINT, BORDER = "#eef1f8", "#9aa3b8", "#5b6478", "#1f2740"
INDIGO, CYAN, VIOLET, AMBER, EMERALD, PINK = "#6366f1", "#22d3ee", "#a855f7", "#f59e0b", "#10b981", "#ec4899"

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
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-activity"},
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


def shade(h, f):
    h = h.lstrip("#")
    r = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    r = [v + (255 - v) * (f - 1) if f >= 1 else v * f for v in r]
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in r)


def mix(a, b, t):
    a, b = a.lstrip("#"), b.lstrip("#")
    ra = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    rb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(ra, rb))


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


def prism(x, y, w, h, dx, dy, color, delay=None):
    front = f'<rect x="{x:.1f}" y="{y - h:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{shade(color, 0.72)}"/>'
    top = f'<polygon points="{x:.1f},{y - h:.1f} {x + dx:.1f},{y - h - dy:.1f} {x + w + dx:.1f},{y - h - dy:.1f} {x + w:.1f},{y - h:.1f}" fill="{shade(color, 1.15)}"/>'
    side = f'<polygon points="{x + w:.1f},{y:.1f} {x + w + dx:.1f},{y - dy:.1f} {x + w + dx:.1f},{y - h - dy:.1f} {x + w:.1f},{y - h:.1f}" fill="{shade(color, 0.45)}"/>'
    cls = f' class="g" style="animation-delay:{delay:.3f}s"' if delay is not None else ""
    return f"<g{cls}>{front}{side}{top}</g>"


def cube(x, y, s, acc):
    c, h = 0.866 * s, 0.5 * s
    return (f'<polygon points="{x - c:.1f},{y + h:.1f} {x:.1f},{y + 2 * h:.1f} {x:.1f},{y + 2 * h + s:.1f} {x - c:.1f},{y + h + s:.1f}" fill="{shade(acc, 0.55)}"/>'
            f'<polygon points="{x:.1f},{y + 2 * h:.1f} {x + c:.1f},{y + h:.1f} {x + c:.1f},{y + h + s:.1f} {x:.1f},{y + 2 * h + s:.1f}" fill="{shade(acc, 0.35)}"/>'
            f'<polygon points="{x:.1f},{y:.1f} {x + c:.1f},{y + h:.1f} {x:.1f},{y + 2 * h:.1f} {x - c:.1f},{y + h:.1f}" fill="{acc}"/>')


def render(u):
    cc = u["contributionsCollection"]
    days = sorted((d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]), key=lambda d: d["date"])
    cur, longest = streaks([d["contributionCount"] for d in days])
    langs = {}
    for n in u["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            langs.setdefault(e["node"]["name"], [0, e["node"]["color"] or MUTED])
            langs[e["node"]["name"]][0] += e["size"]
    total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]

    W = 1200
    out = []
    stats = [
        (f'{cc["contributionCalendar"]["totalContributions"]:,}', "Contributions", "this year", CYAN),
        (f'{cc["totalCommitContributions"]:,}', "Commits", "this year", VIOLET),
        (f"{cur}", "Current streak", "days in a row", EMERALD),
        (f"{longest}", "Longest streak", "days", AMBER),
        (f'{u["repositories"]["totalCount"]}', "Repositories", "public", PINK),
    ]
    gap = 14
    tw = (W - 72 - gap * 4) / 5
    for i, (v, label, sub, acc) in enumerate(stats):
        x = 36 + i * (tw + gap)
        out.append(f'<g class="f" style="animation-delay:{i * .06:.2f}s">'
                   f'<rect x="{x}" y="36" width="{tw}" height="128" rx="16" fill="#ffffff" fill-opacity="0.03" stroke="{BORDER}"/>'
                   f'<rect x="{x + 16}" y="36" width="{tw - 32}" height="1" fill="url(#hl)"/>'
                   f'{cube(x + 30, 54, 11, acc)}'
                   f'<text x="{x + 52}" y="71" font-family="{SANS}" font-size="14" font-weight="600" fill="{MUTED}">{label}</text>'
                   f'<text x="{x + 20}" y="128" font-family="{SANS}" font-size="42" font-weight="800" letter-spacing="-1.5" fill="{TEXT}">{escape(v)}</text>'
                   f'<text x="{x + 22}" y="150" font-family="{SANS}" font-size="13" fill="{FAINT}">{sub}</text></g>')

    last = days[-30:]
    mx = max([d["contributionCount"] for d in last] + [1])
    cy, ch = 218, 190
    base = cy + 40 + ch
    out.append(f'<text x="36" y="{cy}" font-family="{SANS}" font-size="18" font-weight="700" fill="{TEXT}">Daily activity</text>')
    out.append(f'<text x="168" y="{cy}" font-family="{SANS}" font-size="15" fill="{MUTED}">last 30 days</text>')
    out.append(f'<text x="{W - 36}" y="{cy}" text-anchor="end" font-family="{SANS}" font-size="15" fill="{MUTED}"><tspan fill="{TEXT}" font-weight="700">{sum(d["contributionCount"] for d in last)}</tspan> contributions</text>')
    dx, dy = 18, 12
    x0, x1 = 50, W - 70
    out.append(f'<polygon points="{x0 - 8},{base + 6} {x0 - 8 + dx * 1.6},{base + 6 - dy * 1.6} {x1 + 8 + dx * 1.6},{base + 6 - dy * 1.6} {x1 + 8},{base + 6}" fill="#ffffff" fill-opacity="0.035" stroke="{BORDER}"/>')
    for k in range(1, 4):
        yy = base - ch * k / 4
        out.append(f'<line x1="{x0 + dx}" y1="{yy - dy:.1f}" x2="{x1 + dx}" y2="{yy - dy:.1f}" stroke="{BORDER}" stroke-dasharray="3 7"/>')
    bw = (x1 - x0) / len(last)
    for i, d in enumerate(last):
        v = d["contributionCount"]
        hgt = max(4, ch * v / mx)
        is_last = i == len(last) - 1
        col = EMERALD if is_last else (mix(INDIGO, CYAN, v / mx) if v else "#252c44")
        out.append(prism(x0 + i * bw + 4, base, bw - 14, hgt, dx * 0.55, dy * 0.55, col, 0.25 + i * 0.02))
        if is_last:
            out.append(f'<circle cx="{x0 + i * bw + 4 + (bw - 14) / 2 + 5:.1f}" cy="{base - hgt - 22:.1f}" r="4" fill="{EMERALD}" class="pl"/>')
    for i in (0, 10, 20, 29):
        out.append(f'<text x="{x0 + i * bw + bw / 2 - 2:.1f}" y="{base + 30}" text-anchor="middle" font-family="{SANS}" font-size="13" fill="{FAINT}">{dt.date.fromisoformat(last[i]["date"]).strftime("%d %b")}</text>')

    ly = base + 78
    out.append(f'<line x1="36" y1="{ly - 22}" x2="{W - 36}" y2="{ly - 22}" stroke="{BORDER}"/>')
    out.append(f'<text x="36" y="{ly + 18}" font-family="{SANS}" font-size="18" font-weight="700" fill="{TEXT}">Languages</text>')
    bx, bwid = 180, W - 180 - 60
    acc = 0
    segs = []
    for name, (size, col) in top:
        wseg = bwid * size / total
        segs.append(prism(bx + acc, ly + 22, max(wseg - 3, 3), 18, 10, 7, col))
        acc += wseg
    out.extend(segs)
    lx = bx
    for name, (size, col) in top:
        label = f"{name} {100 * size / total:.0f}%"
        out.append(f'<rect x="{lx}" y="{ly + 44}" width="11" height="11" rx="3" fill="{col}"/><text x="{lx + 18}" y="{ly + 54}" font-family="{SANS}" font-size="14" fill="{TEXT}">{escape(label)}</text>')
        lx += len(label) * 8 + 46
    H = ly + 84
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    out.append(f'<text x="{W - 36}" y="{H - 18}" text-anchor="end" font-family="{SANS}" font-size="12" fill="{FAINT}">Updated {stamp}</text>')
    style = ("<style>.f{opacity:0;animation:f .7s ease-out forwards}@keyframes f{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}"
             ".g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:g .7s cubic-bezier(.2,.7,.2,1) forwards}@keyframes g{to{transform:scaleY(1)}}"
             ".pl{animation:pl 2.4s ease-in-out infinite}@keyframes pl{50%{opacity:.3}}</style>")
    defs = (f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0c1122"/><stop offset="1" stop-color="#06080f"/></linearGradient>'
            f'<radialGradient id="gl" cx="20%" cy="0%" r="70%"><stop offset="0" stop-color="{EMERALD}" stop-opacity="0.16"/><stop offset="1" stop-color="{EMERALD}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="hl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="cp"><rect width="{W}" height="{H}" rx="20"/></clipPath></defs>')
    bg = (f'<g clip-path="url(#cp)"><rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#gl)"/></g>'
          f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="{BORDER}"/><rect x="40" y="0" width="{W - 80}" height="1" fill="url(#hl)"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{defs}{style}{bg}{"".join(out)}</svg>'


if __name__ == "__main__":
    data = mock() if "--mock" in sys.argv else fetch()
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, "activity.svg")
    with open(p, "w", encoding="utf-8") as f:
        f.write(render(data))
    print("wrote", p)