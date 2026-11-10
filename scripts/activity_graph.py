#!/usr/bin/env python3
"""Generate a daily-contribution activity graph (SVG) from the GitHub GraphQL API.

Env: GITHUB_TOKEN, USERNAME, optional DAYS (default 90), OUT_DIR (default activity-graph).
Writes activity-dark.svg and activity-light.svg.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", title="#e6edf3", text="#8b949e",
                 grid="#21262d", line1="#6366f1", line2="#3b82f6", dot="#93c5fd",
                 accent="#60a5fa", area_op="0.65"),
    "light": dict(bg="#ffffff", border="#d0d7de", title="#1f2328", text="#57606a",
                  grid="#eaeef2", line1="#4f46e5", line2="#2563eb", dot="#1d4ed8",
                  accent="#1d4ed8", area_op="0.40"),
}


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    return cal["totalContributions"], days


def streaks(counts):
    cur = 0
    for c in reversed(counts):
        if c > 0:
            cur += 1
        elif cur == 0 and c == 0:
            # today may not have contributions yet; skip only the last day
            continue
        else:
            break
    best = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        best = max(best, run)
    return cur, best


def nice_max(v):
    for step in (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 50, 75, 100, 200, 250, 500, 1000):
        if step * 4 >= v:
            return step * 4
    return v


STOPS = [(0.0, (139, 92, 246)), (0.18, (236, 72, 153)), (0.36, (249, 115, 22)),
         (0.46, (168, 85, 247)), (0.55, (59, 130, 246)), (0.72, (34, 211, 238)), (1.0, (34, 197, 94))]


def color_at(f):
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        if f <= b:
            k = (f - a) / (b - a) if b > a else 0
            return "#%02x%02x%02x" % tuple(round(ca[i] + (cb[i] - ca[i]) * k) for i in range(3))
    return "#%02x%02x%02x" % STOPS[-1][1]


ICONS = {
    "users": '<g fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round"><circle cx="7" cy="6" r="3.2"/><path d="M1.5 17c0-3.3 2.5-5.5 5.5-5.5s5.5 2.2 5.5 5.5"/><circle cx="14" cy="6.5" r="2.6"/><path d="M14.5 11.6c2.6.3 4.4 2.3 4.4 5.4"/></g>',
    "star": '<path d="M10 1.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9L10 14.9l-5.2 2.8 1-5.9L1.5 7.7l5.9-.8z" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"/>',
    "flame": '<path d="M10 1.5c.6 3.4 4.8 5.3 4.8 10a4.8 4.8 0 01-9.6 0c0-2.5 1.4-3.8 2.3-5 .3 1.6 1 2.6 2 3 .4-2.6-.6-5.5.5-8z" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"/>',
    "shield": '<g fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"><path d="M10 1.5l7 2.8v5.1c0 4.3-3 7.4-7 9.1-4-1.7-7-4.8-7-9.1V4.3z"/><path d="M6.8 10l2.3 2.3 4.2-4.4"/></g>',
}

CSS = """
text{font-family:"Segoe UI",-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif}
.tt{fill:#f1f5f9;font-size:30px;font-weight:700}
.st{fill:#22d3ee;font-size:15px;opacity:.85}
.ax{fill:#cbd5e1;font-size:14px}
.sv{font-size:28px;font-weight:800}
.sl{fill:#cbd5e1;font-size:14px}
.bd{fill:#ffffff;font-size:14px;font-weight:700}
.ln{stroke-dasharray:6000;stroke-dashoffset:6000;animation:draw 2.5s ease-out forwards}
@keyframes draw{to{stroke-dashoffset:0}}
"""


def render(days, year_total, theme, n):
    recent = days[-n:]
    counts = [c for _, c in recent]
    cur, best = streaks([c for _, c in days])
    W, H = 1000, 520
    CX, CY, CW, CH = 40, 36, W - 80, H - 72          # inner card
    L, R, T, B = CX + 64, CX + CW - 26, CY + 140, CY + CH - 52
    pw, ph = R - L, B - T
    ymax = nice_max(max(counts) or 1)
    last = len(counts) - 1

    def x(i):
        return L + pw * i / last

    def y(v):
        return T + ph * (1 - v / ymax)

    pts = [(x(i), y(c)) for i, c in enumerate(counts)]
    line = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    area = line + f" L{R:.1f},{B:.1f} L{L:.1f},{B:.1f} Z"
    grad_stops = "".join(f'<stop offset="{o}" stop-color="{color_at(o)}"/>' for o, _ in STOPS)

    grid = []
    for k in range(5):
        v = ymax / 4 * k
        gy = y(v)
        grid.append(f'<line x1="{L}" y1="{gy:.1f}" x2="{R}" y2="{gy:.1f}" stroke="#94a3b8" stroke-opacity="{0.35 if k == 0 else 0.13}"/>')
        grid.append(f'<text x="{L - 22}" y="{gy + 5:.1f}" text-anchor="end" class="ax">{v:g}</text>')
    xl = []
    for i in range(0, len(recent), 14):
        date = dt.date.fromisoformat(recent[i][0])
        xl.append(f'<text x="{x(i):.1f}" y="{B + 32}" text-anchor="middle" class="ax">{date.strftime("%b %d")}</text>')

    peak_i = max(range(len(counts)), key=counts.__getitem__)
    thr = max(3, ymax * 0.3)
    big = {i for i in range(len(counts))
           if counts[i] >= thr and counts[i] == max(counts[max(0, i - 4):i + 5])}
    big.add(peak_i)
    guides = sorted(big, key=lambda i: -counts[i])[:5]
    guide_svg = "".join(
        f'<line x1="{pts[i][0]:.1f}" y1="{T - 6}" x2="{pts[i][0]:.1f}" y2="{B}" stroke="{color_at(i / last)}" stroke-opacity="0.45" stroke-dasharray="4 4"/>'
        for i in guides if i != peak_i)

    dots = []
    for i, (px, py) in enumerate(pts):
        c = color_at(i / last)
        tip = f"<title>{recent[i][0]}: {counts[i]} contributions</title>"
        if i in big:
            dots.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="9" fill="{c}" filter="url(#glow)"/>'
                        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="none" stroke="{c}" stroke-width="2"/>'
                        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="#ffffff">{tip}</circle>')
        else:
            dots.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#ffffff" stroke="{c}" stroke-width="2.2">{tip}</circle>')

    px, py = pts[peak_i]
    pc = color_at(peak_i / last)
    lbl = str(counts[peak_i])
    bw = 16 + 9 * len(lbl)
    bx = min(max(px - bw / 2, L), R + 14 - bw)
    badge = (f'<rect x="{bx:.1f}" y="{py - 44:.1f}" width="{bw}" height="24" rx="5" fill="#0b1424" stroke="{pc}" stroke-opacity="0.9"/>'
             f'<rect x="{bx:.1f}" y="{py - 44:.1f}" width="{bw}" height="24" rx="5" fill="{pc}" fill-opacity="0.25"/>'
             f'<text x="{bx + bw / 2:.1f}" y="{py - 27:.1f}" text-anchor="middle" class="bd">{lbl}</text>')

    stats = [("users", "#22d3ee", sum(counts), f"Last {n} days"),
             ("star", "#e879f9", year_total, "Past year"),
             ("flame", "#fb923c", f"{cur}d", "Current streak"),
             ("shield", "#60a5fa", f"{best}d", "Best streak")]
    stat_svg, sx = [], R
    for icon, c, val, label in reversed(stats):
        val = str(val)
        vw = 16.5 * len(val)
        stat_svg.append(
            f'<text x="{sx}" y="{CY + 70}" text-anchor="end" class="sv" fill="{c}" filter="url(#tglow)">{val}</text>'
            f'<g transform="translate({sx - vw - 30:.1f},{CY + 49})">{ICONS[icon].format(c=c)}</g>'
            f'<text x="{sx - (vw + 30) / 2 + 10:.1f}" y="{CY + 96}" text-anchor="middle" class="sl">{label}</text>')
        sx -= max(138, vw + 78)

    bokeh = "".join(f'<circle cx="{a}" cy="{b}" r="{r}" fill="{c}" opacity="{o}"/>' for a, b, r, c, o in [
        (70, 120, 26, "#38bdf8", .14), (955, 90, 22, "#38bdf8", .16), (950, 330, 30, "#0ea5e9", .14),
        (45, 400, 22, "#8b5cf6", .14), (820, 30, 18, "#ec4899", .14), (300, 505, 20, "#22d3ee", .10),
        (640, 500, 16, "#38bdf8", .12), (975, 470, 18, "#22c55e", .12), (520, 22, 14, "#38bdf8", .12)])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Daily contributions">
<style>{CSS}</style>
<defs>
<radialGradient id="bg" cx="50%" cy="0%" r="110%"><stop offset="0" stop-color="#10233d"/><stop offset=".6" stop-color="#0a1426"/><stop offset="1" stop-color="#070b14"/></radialGradient>
<linearGradient id="card" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#132238" stop-opacity=".85"/><stop offset="1" stop-color="#0b1424" stop-opacity=".92"/></linearGradient>
<linearGradient id="rb" gradientUnits="userSpaceOnUse" x1="{L}" y1="0" x2="{R}" y2="0">{grad_stops}</linearGradient>
<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".8"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<linearGradient id="shade" gradientUnits="userSpaceOnUse" x1="0" y1="{T}" x2="0" y2="{B}"><stop offset="0" stop-color="#0f1b2e" stop-opacity="0"/><stop offset="1" stop-color="#0d1829" stop-opacity=".8"/></linearGradient>
<mask id="am" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect x="{L}" y="{T - 20}" width="{pw}" height="{ph + 20}" fill="url(#fade)"/></mask>
<filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="4"/></filter>
<filter id="lglow" filterUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><feGaussianBlur stdDeviation="5"/></filter>
<filter id="tglow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="blur" filterUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><feGaussianBlur stdDeviation="6"/></filter>
</defs>
<rect width="{W}" height="{H}" rx="44" fill="url(#bg)"/>
<g filter="url(#blur)">{bokeh}</g>
<rect x="{CX}" y="{CY}" width="{CW}" height="{CH}" rx="16" fill="url(#card)" stroke="#94a3b8" stroke-opacity=".35"/>
<text x="{CX + 34}" y="{CY + 62}" class="tt" filter="url(#tglow)">Daily Contributions</text>
<text x="{CX + 34}" y="{CY + 92}" class="st">{recent[0][0]} → {recent[-1][0]}</text>
{"".join(stat_svg)}
{"".join(grid)}
{"".join(xl)}
{guide_svg}
<path d="{area}" fill="url(#rb)" opacity=".6"/>
<path d="{area}" fill="url(#shade)"/>
<path d="{line}" fill="none" stroke="url(#rb)" stroke-width="7" stroke-linejoin="round" opacity=".75" filter="url(#lglow)"/>
<path class="ln" d="{line}" fill="none" stroke="url(#rb)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
{"".join(dots)}
{badge}
</svg>
'''


def main():
    n = int(os.environ.get("DAYS", "90"))
    out = os.environ.get("OUT_DIR", "activity-graph")
    if os.environ.get("SAMPLE_JSON"):
        total, days = json.load(open(os.environ["SAMPLE_JSON"]))
    else:
        total, days = fetch(os.environ["USERNAME"], os.environ["GITHUB_TOKEN"])
    os.makedirs(out, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out, f"activity-{theme}.svg"), "w") as f:
            f.write(render(days, total, theme, n))
    print(f"wrote {out}/activity-{{dark,light}}.svg  (year total {total})")


if __name__ == "__main__":
    main()
