#!/usr/bin/env python3

import os
import sys
import json
import urllib.request
from datetime import datetime, timezone

GITHUB_USER = "Asteriix00"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
BG_DARK = "#10002B"
BG_MID = "#3C096C"
ACCENT = "#9D4EDD"
ACCENT_LIGHT = "#C77DFF"
GOLD = "#FFD60A"
TEXT = "#E0AAFF"
FONT = "JetBrains Mono, monospace"
RANK_COLORS = ["#FF8500", "#9D4EDD", "#0096FF", "#2ECC71", "#8D99AE"]
FALLBACK_COLOR = "#8D99AE"

def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_contributions():
    query = """
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
    data = gql(query, {"login": GITHUB_USER})
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]

    total = cal["totalContributions"]
    longest = current = 0
    running = 0
    today = datetime.now(timezone.utc).date()
    for d in days:
        if d["contributionCount"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    for d in reversed(days):
        date = datetime.fromisoformat(d["date"]).date()
        if date > today:
            continue
        if d["contributionCount"] > 0:
            current += 1
        else:
            break
    return total, current, longest


def fetch_top_languages(limit=5):
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
      }
    }
    """
    data = gql(query, {"login": GITHUB_USER})
    totals = {}
    for repo in data["data"]["user"]["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    grand_total = sum(v for _, v in ranked) or 1
    result = []
    for i, (name, size) in enumerate(ranked):
        color = RANK_COLORS[i] if i < len(RANK_COLORS) else FALLBACK_COLOR
        result.append({
            "name": name,
            "pct": round(size / grand_total * 100, 1),
            "color": color,
            "highlight": i == 0, 
        })
    return result


def stat_card(x, y, w, h, label, value, sub):
    return f"""
    <g transform="translate({x},{y})">
      <rect width="{w}" height="{h}" rx="12" fill="url(#cardGrad)" stroke="{ACCENT}" stroke-width="1.5"/>
      <text x="{w/2}" y="34" text-anchor="middle" font-family="{FONT}" font-size="13"
            font-weight="700" fill="{GOLD}" letter-spacing="1">{label}</text>
      <text x="{w/2}" y="72" text-anchor="middle" font-family="{FONT}" font-size="34"
            font-weight="700" fill="#ffffff">{value}</text>
      <text x="{w/2}" y="94" text-anchor="middle" font-family="{FONT}" font-size="11"
            fill="{TEXT}">{sub}</text>
    </g>"""


def language_bar(languages, x, y, width):
    segs = []
    cx = x
    for lang in languages:
        seg_w = width * (lang["pct"] / 100)
        segs.append(
            f'<rect x="{cx:.1f}" y="{y}" width="{seg_w:.1f}" height="10" fill="{lang["color"]}"/>'
        )
        cx += seg_w
    legend = []
    lx, ly = x, y + 26
    for i, lang in enumerate(languages):
        if i > 0 and i % 3 == 0:
            lx = x
            ly += 22
        weight = "700" if lang.get("highlight") else "400"
        legend.append(f"""
          <circle cx="{lx+5}" cy="{ly}" r="5" fill="{lang['color']}"/>
          <text x="{lx+16}" y="{ly+4}" font-family="{FONT}" font-size="11" font-weight="{weight}" fill="{TEXT}">
            {lang['name']} {lang['pct']}%
          </text>""")
        lx += 160
    return f"""
    <g>
      <rect x="{x}" y="{y}" width="{width}" height="10" rx="5" fill="#240046"/>
      <clipPath id="langClip"><rect x="{x}" y="{y}" width="{width}" height="10" rx="5"/></clipPath>
      <g clip-path="url(#langClip)">{''.join(segs)}</g>
      {''.join(legend)}
    </g>"""


def build_svg(total, current, longest, languages):
    W, H = 960, 240
    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{BG_DARK}"/>
      <stop offset="100%" stop-color="{BG_MID}"/>
    </linearGradient>
    <linearGradient id="cardGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#240046"/>
      <stop offset="100%" stop-color="{BG_MID}"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" rx="16" fill="url(#bgGrad)" stroke="{ACCENT}" stroke-width="2"/>

  {stat_card(30, 20, 200, 110, "TOTAL XP", f"{total}", "Contributions")}
  {stat_card(250, 20, 200, 110, "COMBO", f"{current}d", "Current streak")}
  {stat_card(470, 20, 200, 110, "BEST COMBO", f"{longest}d", "Longest streak")}
  {stat_card(690, 20, 240, 110, "MAIN CLASS", languages[0]['name'] if languages else "N/A", "Top language")}

  <text x="30" y="164" font-family="{FONT}" font-size="13" font-weight="700"
        fill="{GOLD}" letter-spacing="1">SKILL DISTRIBUTION</text>
  {language_bar(languages, 30, 176, W-60)}

  <text x="{W-20}" y="{H-14}" text-anchor="end" font-family="{FONT}" font-size="9"
        fill="{ACCENT_LIGHT}" opacity="0.6">Last updated {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')}</text>
</svg>"""


def main():
    if not TOKEN:
        print("ERREUR: GITHUB_TOKEN manquant. Verifie le secret METRICS_TOKEN "
              "et la ligne 'env:' dans le workflow.", file=sys.stderr)
        sys.exit(1)

    total, current, longest = fetch_contributions()
    languages = fetch_top_languages()

    if not languages:
        print("ERREUR: aucun langage recupere depuis l'API GitHub. "
              "Verifie que le token a acces aux repos (scope 'repo').", file=sys.stderr)
        sys.exit(1)

    svg = build_svg(total, current, longest, languages)
    os.makedirs("assets/badges", exist_ok=True)
    with open("assets/badges/player-stats.svg", "w") as f:
        f.write(svg)

if __name__ == "__main__":
    main()
