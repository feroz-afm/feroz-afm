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


def render(days, year_total, theme, n):
    t = THEMES[theme]
    recent = days[-n:]
    counts = [c for _, c in recent]
    cur, best = streaks([c for _, c in days])
    W, H = 900, 330
    L, R, T, B = 52, 24, 92, 46
    pw, ph = W - L - R, H - T - B
    ymax = nice_max(max(counts) or 1)
    step = ymax / 4

    def x(i):
        return L + pw * i / (len(counts) - 1)

    def y(v):
        return T + ph * (1 - v / ymax)

    pts = [(x(i), y(c)) for i, c in enumerate(counts)]
    # smooth path (Catmull-Rom -> Bezier), clamped so it never dips below zero
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    base = y(0)
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(base, p1[1] + (p2[1] - p0[1]) / 6))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(base, p2[1] - (p3[1] - p1[1]) / 6))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    area = d + f" L{pts[-1][0]:.1f},{base:.1f} L{pts[0][0]:.1f},{base:.1f} Z"

    grid = []
    for k in range(5):
        v = step * k
        gy = y(v)
        label = f"{v:g}"
        grid.append(f'<line x1="{L}" y1="{gy:.1f}" x2="{W - R}" y2="{gy:.1f}" stroke="{t["grid"]}" stroke-dasharray="{"0" if k == 0 else "3 4"}"/>')
        grid.append(f'<text x="{L - 10}" y="{gy + 4:.1f}" text-anchor="end" class="ax">{label}</text>')

    xl = []
    for i in range(0, len(recent), 14):
        date = dt.date.fromisoformat(recent[i][0])
        xl.append(f'<text x="{x(i):.1f}" y="{H - B + 22}" text-anchor="middle" class="ax">{date.strftime("%b %d")}</text>')

    peak_i = max(range(len(counts)), key=counts.__getitem__)
    dots = "".join(
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{3.6 if i == peak_i else 2.2}" fill="{t["dot"]}"'
        f' stroke="{t["bg"]}" stroke-width="1"><title>{recent[i][0]}: {counts[i]}</title></circle>'
        for i, (px, py) in enumerate(pts) if counts[i] > 0
    )
    period = sum(counts)
    stats = [("Last %d days" % n, period), ("Past year", year_total),
             ("Current streak", f"{cur}d"), ("Best streak", f"{best}d")]
    sx = W - R
    stat_svg = []
    for label, val in reversed(stats):
        stat_svg.append(f'<text x="{sx}" y="44" text-anchor="end" class="sv">{val}</text>'
                        f'<text x="{sx}" y="62" text-anchor="end" class="sl">{label}</text>')
        sx -= 118
    px, py = pts[peak_i]
    peak_lbl = f'<text x="{px:.1f}" y="{py - 10:.1f}" text-anchor="middle" class="pk">{counts[peak_i]}</text>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Daily contributions">
<style>
text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}}
.tt{{fill:{t["title"]};font-size:20px;font-weight:600}}
.st{{fill:{t["text"]};font-size:12.5px}}
.ax{{fill:{t["text"]};font-size:11px}}
.sv{{fill:{t["accent"]};font-size:20px;font-weight:700}}
.sl{{fill:{t["text"]};font-size:11px}}
.pk{{fill:{t["title"]};font-size:11px;font-weight:600}}
.ln{{stroke-dasharray:4000;stroke-dashoffset:4000;animation:draw 2.2s ease-out forwards}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
</style>
<defs>
<linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["line2"]}" stop-opacity="{t["area_op"]}"/><stop offset="1" stop-color="{t["line2"]}" stop-opacity="0"/></linearGradient>
<linearGradient id="st" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["line1"]}"/><stop offset="1" stop-color="{t["line2"]}"/></linearGradient>
</defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>
<text x="24" y="42" class="tt">Daily Contributions</text>
<text x="24" y="62" class="st">{recent[0][0]} → {recent[-1][0]}</text>
{"".join(stat_svg)}
{"".join(grid)}
{"".join(xl)}
<path d="{area}" fill="url(#ar)"/>
<path class="ln" d="{d}" fill="none" stroke="url(#st)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
{dots}
{peak_lbl}
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
