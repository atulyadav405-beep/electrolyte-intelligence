"""
Electrolyte Intelligence — Daily Page Generator
Calls Claude to fetch fresh market insights and regenerates index.html
Run: python generate.py
Requires: ANTHROPIC_API_KEY environment variable
"""

import anthropic
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ── CONFIG ──────────────────────────────────────────────────────────────────
MODEL = "claude-opus-4-5"          # swap to any model you prefer
IST   = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).strftime("%B %d, %Y")
DOW   = datetime.now(IST).strftime("%A")
MONTH = datetime.now(IST).strftime("%B")
YEAR  = datetime.now(IST).strftime("%Y")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM = """You are a senior market intelligence analyst for Osmo, a premium science-backed
electrolyte brand in India. Your job is to produce sharp, actionable intelligence briefs.
Always return ONLY valid JSON — no markdown fences, no preamble, no trailing text.
Today is {today} ({dow}). Current month: {month} {year}.
India context: Always factor in seasonal triggers, heatwave data, cricket/IPL calendar,
festival calendar, and health advisories. Osmo's positioning: high science credibility,
premium price, D2C, targeting urban professionals and serious athletes.
""".format(today=TODAY, dow=DOW, month=MONTH, year=YEAR)


def fetch(prompt: str, schema_hint: str = "") -> list:
    """Call Claude and return parsed JSON list."""
    full_prompt = f"{prompt}\n\nReturn a JSON array. {schema_hint}"
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM,
        messages=[{"role": "user", "content": full_prompt}]
    )
    raw = msg.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    return json.loads(raw)


# ── FETCH ALL SECTIONS ───────────────────────────────────────────────────────

print("Fetching India moments...")
india_items = fetch(
    f"""Generate 4 India-specific electrolyte marketing intelligence insights for {TODAY}.
Consider: current heatwave season, IPL cricket, upcoming festivals ({MONTH}),
outdoor worker stories, health advisories, dehydration incidents.
Each object must have:
  title (string), urgency ("critical"|"high"|"medium"|"low"),
  what (2-sentence summary of what's happening),
  why (1 sentence: mechanism connecting this to electrolyte need),
  angle (1 sentence: bold marketing hook in quotes),
  action ("organic_social"|"paid_campaign"|"pr_pitch"|"influencer"|"content_series"),
  tag (short descriptor like "Time-sensitive · 7-day window")""",
    "Fields: title, urgency, what, why, angle, action, tag"
)

print("Fetching global trends...")
global_items = fetch(
    f"""Generate 3 global electrolyte category trend insights relevant to an Indian
premium brand in {MONTH} {YEAR}.
Consider: market size ($43B global, $81M India growing 13.9% CAGR), clean-label shift,
zero-sugar formats, functional stacking, science credibility trend, competitor moves globally.
Each object: title, urgency, what, angle, tag""",
    "Fields: title, urgency, what, angle, tag"
)

print("Fetching competitor intelligence...")
competitor_items = fetch(
    f"""Generate 3 competitor intelligence insights for Osmo in India as of {TODAY}.
Known activity: Fast&Up launched electrolyte popsicles with NOTO (₹102, Swiggy/Zomato),
Powerade Power Water (zero-sugar, launched Nov 2025), Campa ₹10 SKU (Reliance),
MuscleBlaze scaling sports nutrition.
Each object: title, urgency, what (what the competitor did), gap (white space Osmo can claim), tag""",
    "Fields: title, urgency, what, gap, tag"
)

print("Fetching weekly actions...")
actions = fetch(
    f"""Generate 4 prioritized marketing actions for the Osmo team this week ({TODAY}).
Base on: heatwave urgency, IPL season (live until May 31), government pushing ORS for outdoor
workers, clean-label consumer shift, urban professional audience.
Each object: title, channel (e.g. "Instagram · X"), tone, description (2 sentences),
timing ("Do today"|"This week"|"This month"), brief_type (a short slug for the action type)""",
    "Fields: title, channel, tone, description, timing, brief_type"
)

print("Fetching heat map scores...")
heatmap = fetch(
    f"""Score 5 marketing opportunity dimensions for Osmo in India right now ({TODAY}).
Return exactly 5 objects, each: label (string), score (integer 0-100), color_hint ("red"|"amber"|"gold"|"green")""",
    "Fields: label, score, color_hint. Exactly 5 items."
)

print("Fetching upcoming triggers...")
triggers = fetch(
    f"""List 6 upcoming seasonal/cultural triggers in India for electrolyte marketing,
starting from {TODAY} and going forward through the year.
Each: month_label (e.g. "NOW" or "MAY" or "OCT"), title, description (1 sentence),
dot_color ("red"|"gold"|"green")""",
    "Fields: month_label, title, description, dot_color. Exactly 6 items."
)

print("All data fetched. Building HTML...")


# ── HTML HELPERS ─────────────────────────────────────────────────────────────

URG_CLASS = {
    "critical": "urg-critical",
    "high":     "urg-high",
    "medium":   "urg-medium",
    "low":      "urg-low",
}

DOT_COLORS = {
    "red":   "var(--red)",
    "gold":  "var(--accent)",
    "green": "var(--accent-2)",
    "amber": "var(--accent-3)",
}

HEAT_COLORS = {
    "red":   "var(--red)",
    "amber": "var(--accent-3)",
    "gold":  "var(--accent)",
    "green": "var(--accent-2)",
}

BRIEF_PROMPTS = {
    "heatwave_content":  "Create a full marketing content brief for Osmo around the current India heatwave — empathy-first, science-backed, 3 content pieces across Instagram, X, and email",
    "heatwave_social":   "Write complete copy for a 3-slide Instagram carousel for Osmo about the current India heatwave. Empathy-first tone, educational, soft product mention at end.",
    "ors_upgrade":       "Write a brand positioning brief for Osmo around the ORS moment — government pushing ORS for outdoor workers. How does Osmo position as the science upgrade?",
    "ipl_fan":           "Build a full IPL 2026 campaign brief for Osmo targeting fans watching in extreme heat — hook, message, 2 content formats, caption copy.",
    "ipl_reel":          "Write a 30-second Instagram Reel script for Osmo targeting IPL fans watching outdoors in summer heat. Fun, relatable, ends with product hook.",
    "science_35plus":    "Create a 4-post science content series for Osmo for LinkedIn and Instagram targeting urban professionals 35-50. Topic: dehydration and cognitive performance.",
    "heatwave_carousel": "Write copy for a 3-slide Instagram carousel: heatwave + hydration for Osmo. Empathy-first, educational.",
    "pr_pitch":          "Write a PR pitch email from Osmo to Mint Lounge health editor. Angle: ORS is not enough for outdoor workers — Osmo is the science-backed upgrade.",
    "cognitive_series":  "Build a 6-post LinkedIn content series for Osmo on cognitive dehydration — for urban professionals in Bangalore, Mumbai, Delhi.",
    "weekly_brief":      f"Generate a complete marketing intelligence brief for the Osmo team for the week of {TODAY}. Include top 3 India moments, 1 global trend, 1 competitor alert, 4 prioritized actions.",
    "competitor_alert":  "Analyze the competitive landscape for Osmo in India right now. Fast&Up popsicles, Powerade Power Water, Campa ₹10 SKU — what should Osmo do?",
}


def esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def brief_js(prompts: dict) -> str:
    lines = []
    for k, v in prompts.items():
        safe = v.replace("'", "\\'").replace("\n", " ")
        lines.append(f"    '{k}': '{safe}'")
    return "const BRIEF_PROMPTS = {{\n{}\n  }};".format(",\n".join(lines))


def india_cards_html(items: list) -> str:
    urgent = [i for i in items if i.get("urgency") in ("critical", "high")]
    ongoing = [i for i in items if i.get("urgency") in ("medium", "low")]

    def card(item, open_body=False):
        uc = URG_CLASS.get(item.get("urgency", "medium"), "urg-medium")
        body_class = "insight-card-body open" if open_body else "insight-card-body"
        return f"""
        <div class="insight-card">
          <div class="insight-card-head" onclick="toggleCard(this)">
            <div class="insight-card-title">{esc(item.get('title',''))}</div>
            <span class="urgency-badge {uc}">{esc(item.get('urgency',''))}</span>
          </div>
          <div class="{body_class}">
            <div class="insight-block">
              <div class="insight-block-label">What's happening</div>
              <div class="insight-block-text">{esc(item.get('what',''))}</div>
            </div>
            <div class="insight-block">
              <div class="insight-block-label">Why it matters</div>
              <div class="insight-block-text">{esc(item.get('why',''))}</div>
            </div>
            <div class="insight-block">
              <div class="insight-block-label">Marketing angle</div>
              <div class="insight-block-text"><strong>{esc(item.get('angle',''))}</strong></div>
            </div>
            <div class="card-tag-row"><span class="card-tag">{esc(item.get('tag',''))}</span></div>
            <div class="card-actions">
              <button class="card-action-btn" onclick="brief('{esc(item.get('action','weekly_brief'))}')">Get content brief →</button>
            </div>
          </div>
        </div>"""

    urgent_html = "\n".join(card(i, open_body=(j == 0)) for j, i in enumerate(urgent))
    ongoing_html = "\n".join(card(i) for i in ongoing)

    return f"""
      <div class="panel-section">
        <div class="panel-section-title">Critical — act immediately</div>
        {urgent_html}
      </div>
      <div class="panel-section">
        <div class="panel-section-title">Ongoing opportunities</div>
        {ongoing_html}
      </div>"""


def global_cards_html(items: list) -> str:
    def card(item, first=False):
        uc = URG_CLASS.get(item.get("urgency", "medium"), "urg-medium")
        body_class = "insight-card-body open" if first else "insight-card-body"
        return f"""
        <div class="insight-card">
          <div class="insight-card-head" onclick="toggleCard(this)">
            <div class="insight-card-title">{esc(item.get('title',''))}</div>
            <span class="urgency-badge {uc}">{esc(item.get('urgency',''))}</span>
          </div>
          <div class="{body_class}">
            <div class="insight-block">
              <div class="insight-block-label">What's happening</div>
              <div class="insight-block-text">{esc(item.get('what',''))}</div>
            </div>
            <div class="insight-block">
              <div class="insight-block-label">Marketing angle</div>
              <div class="insight-block-text"><strong>{esc(item.get('angle',''))}</strong></div>
            </div>
            <div class="card-tag-row"><span class="card-tag">{esc(item.get('tag',''))}</span></div>
          </div>
        </div>"""
    return "\n".join(card(i, first=(j == 0)) for j, i in enumerate(items))


def competitor_cards_html(items: list) -> str:
    def card(item, first=False):
        uc = URG_CLASS.get(item.get("urgency", "medium"), "urg-medium")
        body_class = "insight-card-body open" if first else "insight-card-body"
        return f"""
        <div class="insight-card">
          <div class="insight-card-head" onclick="toggleCard(this)">
            <div class="insight-card-title">{esc(item.get('title',''))}</div>
            <span class="urgency-badge {uc}">{esc(item.get('urgency',''))}</span>
          </div>
          <div class="{body_class}">
            <div class="insight-block">
              <div class="insight-block-label">What they did</div>
              <div class="insight-block-text">{esc(item.get('what',''))}</div>
            </div>
            <div class="insight-block">
              <div class="insight-block-label">White space for Osmo</div>
              <div class="insight-block-text"><strong>{esc(item.get('gap',''))}</strong></div>
            </div>
            <div class="card-tag-row"><span class="card-tag">{esc(item.get('tag',''))}</span></div>
          </div>
        </div>"""
    return "\n".join(card(i, first=(j == 0)) for j, i in enumerate(items))


def actions_html(items: list) -> str:
    result = []
    for i, item in enumerate(items, 1):
        timing_class = "urg-critical" if item.get("timing") == "Do today" else \
                       "urg-high"     if item.get("timing") == "This week" else "urg-low"
        result.append(f"""
        <div class="action-item">
          <div class="action-num">0{i}</div>
          <div class="action-content">
            <div class="action-title">{esc(item.get('title',''))}</div>
            <div class="action-desc">{esc(item.get('description',''))}</div>
            <div class="action-meta">
              <span class="action-chip">{esc(item.get('channel',''))}</span>
              <span class="action-chip">{esc(item.get('tone',''))}</span>
              <span class="urgency-badge {timing_class}" style="font-size:9px;padding:2px 8px">{esc(item.get('timing',''))}</span>
              <button class="action-cta" onclick="brief('{esc(item.get('brief_type','weekly_brief'))}')">Generate copy →</button>
            </div>
          </div>
        </div>""")
    return "\n".join(result)


def heatmap_html(items: list) -> str:
    rows = []
    for item in items:
        color = HEAT_COLORS.get(item.get("color_hint", "gold"), "var(--accent)")
        score = int(item.get("score", 50))
        rows.append(f"""
      <div class="heat-row">
        <div class="heat-label">{esc(item.get('label',''))}</div>
        <div class="heat-bar-wrap"><div class="heat-bar" style="width:{score}%;background:{color}"></div></div>
        <div class="heat-val" style="color:{color}">{score}</div>
      </div>""")
    return "\n".join(rows)


def triggers_html(items: list) -> str:
    rows = []
    for item in items:
        color = DOT_COLORS.get(item.get("dot_color", "gold"), "var(--accent)")
        rows.append(f"""
      <div class="cal-item">
        <div class="cal-date">{esc(item.get('month_label',''))}</div>
        <div class="cal-dot" style="background:{color}"></div>
        <div class="cal-text"><strong>{esc(item.get('title',''))}</strong> — {esc(item.get('description',''))}</div>
      </div>""")
    return "\n".join(rows)


def ticker_items_html(india: list, global_: list) -> str:
    items = []
    for i in india[:3]:
        items.append(f'<div class="ticker-item">{esc(i.get("title","")[:60])} <span class="hot">{esc(i.get("urgency","").upper())}</span></div>')
    for g in global_[:2]:
        items.append(f'<div class="ticker-item">{esc(g.get("title","")[:60])} <span class="up">↑ trending</span></div>')
    # static context items
    items += [
        '<div class="ticker-item">India market 2026 <span class="val up">$81M</span> <span class="up">↑ 13.9% CAGR</span></div>',
        '<div class="ticker-item">Global electrolyte mkt <span class="val">$43B</span></div>',
        '<div class="ticker-item">IPL 2026 <span class="val up">LIVE</span> through May 31</div>',
        '<div class="ticker-item">Clean-label shift <span class="up">accelerating</span></div>',
        '<div class="ticker-item">Zero-sugar formats <span class="up">↑ fastest growing</span></div>',
    ]
    doubled = items + items   # doubled for seamless loop
    return "\n      ".join(doubled)


# ── BUILD THE FULL HTML PAGE ──────────────────────────────────────────────────

INDIA_HTML      = india_cards_html(india_items)
GLOBAL_HTML     = global_cards_html(global_items)
COMPETITOR_HTML = competitor_cards_html(competitor_items)
ACTIONS_HTML    = actions_html(actions)
HEATMAP_HTML    = heatmap_html(heatmap)
TRIGGERS_HTML   = triggers_html(triggers)
TICKER_HTML     = ticker_items_html(india_items, global_items)
BRIEF_JS        = brief_js(BRIEF_PROMPTS)

# Build JS brief prompt map from fetched actions too
for a in actions:
    bt = a.get("brief_type", "")
    if bt and bt not in BRIEF_PROMPTS:
        BRIEF_PROMPTS[bt] = f"Write detailed marketing copy for: {a.get('title','')}. Channel: {a.get('channel','')}. Tone: {a.get('tone','')}. Brand: Osmo electrolytes India."
BRIEF_JS = brief_js(BRIEF_PROMPTS)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Electrolyte Intelligence — {TODAY}</title>
<meta name="description" content="Daily electrolyte market intelligence for India — heatwave alerts, competitor moves, and actionable marketing briefs for Osmo.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Mono:wght@300;400;500&family=Geist:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0a0a08;--bg-2:#111110;--bg-3:#1a1a17;--bg-4:#222220;
  --line:rgba(255,255,255,0.08);--line-2:rgba(255,255,255,0.14);
  --text:#f0ede8;--text-2:#9a9690;--text-3:#5a5752;
  --accent:#c8b882;--accent-2:#8aad8a;--accent-3:#c47c5a;--red:#d44;
  --font-display:'Instrument Serif',Georgia,serif;
  --font-body:'Geist',system-ui,sans-serif;
  --font-mono:'DM Mono',monospace;
}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--text);font-family:var(--font-body);font-size:14px;line-height:1.6;min-height:100vh;-webkit-font-smoothing:antialiased}}
.ticker-wrap{{border-bottom:1px solid var(--line);background:var(--bg);overflow:hidden;height:32px;display:flex;align-items:center;position:sticky;top:0;z-index:100}}
.ticker-label{{font-family:var(--font-mono);font-size:10px;letter-spacing:.1em;color:var(--accent);padding:0 16px;border-right:1px solid var(--line);height:100%;display:flex;align-items:center;flex-shrink:0;white-space:nowrap}}
.ticker-track{{display:flex;gap:0;animation:ticker 50s linear infinite;white-space:nowrap}}
.ticker-track:hover{{animation-play-state:paused}}
.ticker-item{{font-family:var(--font-mono);font-size:10px;letter-spacing:.05em;color:var(--text-2);padding:0 24px;border-right:1px solid var(--line);height:32px;display:flex;align-items:center;gap:8px}}
.ticker-item .val{{color:var(--text)}}.ticker-item .up{{color:var(--accent-2)}}.ticker-item .hot{{color:var(--red)}}
@keyframes ticker{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
nav{{display:flex;align-items:center;justify-content:space-between;padding:20px 48px;border-bottom:1px solid var(--line)}}
.nav-brand .brand-name{{font-family:var(--font-display);font-size:18px;letter-spacing:-.01em;color:var(--text)}}
.nav-brand .brand-sub{{font-family:var(--font-mono);font-size:9px;letter-spacing:.14em;color:var(--text-3);text-transform:uppercase;margin-top:2px}}
.nav-links{{display:flex;gap:32px;list-style:none}}
.nav-links a{{font-size:12px;color:var(--text-3);text-decoration:none;letter-spacing:.04em;transition:color .2s}}
.nav-links a:hover{{color:var(--text)}}
.nav-right{{display:flex;align-items:center;gap:12px}}
.date-pill{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);letter-spacing:.06em;border:1px solid var(--line-2);padding:5px 12px;border-radius:2px}}
.refresh-btn{{font-family:var(--font-mono);font-size:10px;letter-spacing:.08em;color:var(--accent);background:transparent;border:1px solid rgba(200,184,130,.25);padding:6px 14px;border-radius:2px;cursor:pointer;transition:all .2s;text-transform:uppercase;display:flex;align-items:center;gap:6px}}
.refresh-btn:hover{{background:rgba(200,184,130,.08);border-color:rgba(200,184,130,.5)}}
.spin{{display:inline-block}}.spinning .spin{{animation:rotate .8s linear infinite}}
@keyframes rotate{{to{{transform:rotate(360deg)}}}}
.hero{{padding:64px 48px 48px;border-bottom:1px solid var(--line);display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:end}}
.hero-kicker{{font-family:var(--font-mono);font-size:10px;letter-spacing:.14em;color:var(--accent);text-transform:uppercase;margin-bottom:16px;display:flex;align-items:center;gap:8px}}
.kicker-dot{{width:5px;height:5px;border-radius:50%;background:var(--accent);animation:blink 2s ease-in-out infinite}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
.hero h1{{font-family:var(--font-display);font-size:clamp(36px,4vw,56px);line-height:1.1;letter-spacing:-.02em;color:var(--text);margin-bottom:20px}}
.hero h1 em{{font-style:italic;color:var(--accent)}}
.hero-desc{{font-size:15px;color:var(--text-2);line-height:1.7;max-width:420px}}
.hero-stats{{display:flex;flex-direction:column;gap:0;align-self:stretch;justify-content:center}}
.hero-stat-row{{display:flex;justify-content:space-between;align-items:baseline;padding:16px 0;border-bottom:1px solid var(--line)}}
.hero-stat-row:first-child{{border-top:1px solid var(--line)}}
.stat-label{{font-family:var(--font-mono);font-size:10px;letter-spacing:.1em;color:var(--text-3);text-transform:uppercase}}
.stat-value{{font-family:var(--font-display);font-size:28px;color:var(--text);letter-spacing:-.02em}}
.stat-delta{{font-family:var(--font-mono);font-size:10px;color:var(--accent-2);margin-left:8px}}
.stat-delta.dn{{color:var(--accent-3)}}
.alert-banner{{display:flex;align-items:center;gap:16px;background:rgba(212,68,68,.06);border-bottom:1px solid rgba(212,68,68,.2);padding:12px 48px}}
.alert-tag{{font-family:var(--font-mono);font-size:9px;letter-spacing:.14em;color:var(--red);border:1px solid rgba(212,68,68,.4);padding:3px 8px;border-radius:2px;text-transform:uppercase;flex-shrink:0}}
.alert-text{{font-size:12px;color:var(--text-2)}}.alert-text strong{{color:var(--text)}}
.main{{display:grid;grid-template-columns:1fr 320px;min-height:calc(100vh - 200px)}}
.content-area{{border-right:1px solid var(--line);padding:0}}
.tabs{{display:flex;border-bottom:1px solid var(--line);overflow-x:auto}}
.tab-btn{{font-family:var(--font-mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-3);background:transparent;border:none;border-bottom:2px solid transparent;padding:16px 24px;cursor:pointer;white-space:nowrap;transition:all .2s;margin-bottom:-1px}}
.tab-btn:hover{{color:var(--text-2)}}.tab-btn.active{{color:var(--accent);border-bottom-color:var(--accent)}}
.panel{{display:none;padding:32px 40px}}.panel.active{{display:block}}
.panel-section{{margin-bottom:40px}}
.panel-section-title{{font-family:var(--font-mono);font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--text-3);margin-bottom:20px;padding-bottom:10px;border-bottom:1px solid var(--line)}}
.insight-card{{border:1px solid var(--line);border-radius:3px;margin-bottom:12px;overflow:hidden;transition:border-color .2s}}
.insight-card:hover{{border-color:var(--line-2)}}
.insight-card-head{{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;gap:16px;cursor:pointer}}
.insight-card-title{{font-size:14px;font-weight:400;color:var(--text);line-height:1.4;flex:1}}
.urgency-badge{{font-family:var(--font-mono);font-size:9px;letter-spacing:.1em;text-transform:uppercase;padding:3px 9px;border-radius:2px;flex-shrink:0}}
.urg-critical{{background:rgba(212,68,68,.12);color:#e06060;border:1px solid rgba(212,68,68,.25)}}
.urg-high{{background:rgba(196,124,90,.12);color:var(--accent-3);border:1px solid rgba(196,124,90,.25)}}
.urg-medium{{background:rgba(200,184,130,.1);color:var(--accent);border:1px solid rgba(200,184,130,.2)}}
.urg-low{{background:rgba(138,173,138,.1);color:var(--accent-2);border:1px solid rgba(138,173,138,.2)}}
.insight-card-body{{padding:0 18px 16px;display:none}}.insight-card-body.open{{display:block}}
.insight-block{{margin-bottom:12px}}
.insight-block-label{{font-family:var(--font-mono);font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--text-3);margin-bottom:4px}}
.insight-block-text{{font-size:13px;color:var(--text-2);line-height:1.6}}.insight-block-text strong{{color:var(--text);font-weight:500}}
.card-actions{{display:flex;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--line)}}
.card-action-btn{{font-family:var(--font-mono);font-size:10px;letter-spacing:.06em;color:var(--accent);background:transparent;border:1px solid rgba(200,184,130,.2);padding:6px 12px;border-radius:2px;cursor:pointer;transition:all .2s}}
.card-action-btn:hover{{background:rgba(200,184,130,.08);border-color:rgba(200,184,130,.4)}}
.card-tag-row{{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}}
.card-tag{{font-family:var(--font-mono);font-size:9px;letter-spacing:.08em;color:var(--text-3);background:var(--bg-3);padding:3px 8px;border-radius:2px}}
.comp-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.comp-card{{border:1px solid var(--line);border-radius:3px;padding:16px;transition:border-color .2s}}
.comp-card:hover{{border-color:var(--line-2)}}
.comp-name{{font-size:14px;font-weight:500;color:var(--text);margin-bottom:6px}}
.comp-desc{{font-size:12px;color:var(--text-2);line-height:1.5;margin-bottom:10px}}
.threat-chip{{font-family:var(--font-mono);font-size:9px;letter-spacing:.08em;padding:2px 8px;border-radius:2px}}
.action-item{{display:flex;gap:16px;padding:16px 0;border-bottom:1px solid var(--line);align-items:flex-start}}
.action-num{{font-family:var(--font-display);font-size:32px;color:var(--bg-4);line-height:1;flex-shrink:0;width:32px;text-align:center}}
.action-content{{flex:1}}
.action-title{{font-size:14px;color:var(--text);margin-bottom:4px}}
.action-desc{{font-size:12px;color:var(--text-2);line-height:1.5}}
.action-meta{{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;align-items:center}}
.action-chip{{font-family:var(--font-mono);font-size:9px;letter-spacing:.07em;color:var(--text-3);border:1px solid var(--line);padding:3px 8px;border-radius:2px}}
.action-cta{{font-family:var(--font-mono);font-size:9px;letter-spacing:.08em;color:var(--accent);background:transparent;border:1px solid rgba(200,184,130,.25);padding:4px 10px;border-radius:2px;cursor:pointer;transition:all .2s}}
.action-cta:hover{{background:rgba(200,184,130,.08)}}
.ai-fetch-btn{{font-family:var(--font-mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-2);background:var(--bg-3);border:1px solid var(--line-2);padding:10px 20px;border-radius:2px;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:8px;width:100%;justify-content:center}}
.ai-fetch-btn:hover{{background:var(--bg-4);border-color:var(--accent);color:var(--accent)}}
.ai-output{{margin-top:16px}}
.sk{{background:var(--bg-3);border-radius:2px;animation:pulse 1.5s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
.sk-card{{height:80px;margin-bottom:10px}}
.sidebar{{padding:0}}
.sidebar-block{{padding:24px;border-bottom:1px solid var(--line)}}
.sidebar-title{{font-family:var(--font-mono);font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--text-3);margin-bottom:16px}}
.heat-row{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
.heat-label{{font-size:12px;color:var(--text-2);flex:1}}
.heat-bar-wrap{{flex:1;background:var(--bg-3);border-radius:1px;height:4px;overflow:hidden}}
.heat-bar{{height:4px;border-radius:1px;transition:width .8s ease}}
.heat-val{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);min-width:28px;text-align:right}}
.cal-item{{display:flex;align-items:flex-start;gap:12px;margin-bottom:14px}}
.cal-date{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);min-width:32px;padding-top:2px}}
.cal-dot{{width:6px;height:6px;border-radius:50%;margin-top:5px;flex-shrink:0}}
.cal-text{{font-size:12px;color:var(--text-2);line-height:1.5}}.cal-text strong{{color:var(--text);font-weight:500}}
footer{{border-top:1px solid var(--line);padding:20px 48px;display:flex;align-items:center;justify-content:space-between}}
.footer-txt{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);letter-spacing:.06em}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.fade-in{{animation:fadeUp .5s ease forwards;opacity:0}}
.delay-1{{animation-delay:.1s}}.delay-2{{animation-delay:.2s}}.delay-3{{animation-delay:.3s}}.delay-4{{animation-delay:.4s}}
@media(max-width:900px){{
  nav{{padding:16px 20px}}.nav-links{{display:none}}
  .hero{{grid-template-columns:1fr;padding:40px 20px 32px;gap:32px}}
  .main{{grid-template-columns:1fr}}.sidebar{{border-top:1px solid var(--line)}}
  .panel{{padding:24px 20px}}.alert-banner{{padding:10px 20px}}
  .comp-grid{{grid-template-columns:1fr}}
  footer{{flex-direction:column;gap:8px;padding:16px 20px}}
}}
</style>
</head>
<body>

<div class="ticker-wrap">
  <div class="ticker-label">LIVE</div>
  <div style="overflow:hidden;flex:1">
    <div class="ticker-track">
      {TICKER_HTML}
    </div>
  </div>
</div>

<nav>
  <div class="nav-brand">
    <span class="brand-name">Electrolyte Intelligence</span>
    <span class="brand-sub">Daily Market Briefing · {TODAY}</span>
  </div>
  <ul class="nav-links">
    <li><a href="#" onclick="switchTab('india',document.querySelector('.tab-btn'));return false">India</a></li>
    <li><a href="#" onclick="switchTab('global',document.querySelectorAll('.tab-btn')[1]);return false">Global</a></li>
    <li><a href="#" onclick="switchTab('competitors',document.querySelectorAll('.tab-btn')[2]);return false">Competitors</a></li>
    <li><a href="#" onclick="switchTab('actions',document.querySelectorAll('.tab-btn')[3]);return false">Actions</a></li>
  </ul>
  <div class="nav-right">
    <div class="date-pill">{TODAY}</div>
    <button class="refresh-btn" onclick="location.reload()" id="refreshBtn">
      <span class="spin">↻</span> Refresh
    </button>
  </div>
</nav>

<div class="alert-banner">
  <span class="alert-tag">⚠ Alert</span>
  <span class="alert-text"><strong>Daily briefing updated:</strong> {TODAY} — Fresh intelligence across India moments, global trends, and competitor activity. Generated at 07:00 IST.</span>
</div>

<div class="hero">
  <div class="fade-in">
    <div class="hero-kicker"><div class="kicker-dot"></div> Daily intelligence briefing</div>
    <h1>What's moving the <em>electrolyte</em> category today</h1>
    <p class="hero-desc">Real-time market signals, India incidents, competitor moves, and actionable marketing briefs — built for your team to move fast.</p>
  </div>
  <div class="hero-stats fade-in delay-2">
    <div class="hero-stat-row">
      <span class="stat-label">India market 2026</span>
      <span><span class="stat-value">$81M</span><span class="stat-delta up">↑ 13.9%</span></span>
    </div>
    <div class="hero-stat-row">
      <span class="stat-label">Global market</span>
      <span><span class="stat-value">$43B</span><span class="stat-delta up">↑ 8.4%</span></span>
    </div>
    <div class="hero-stat-row">
      <span class="stat-label">Category growth India</span>
      <span><span class="stat-value" style="color:var(--accent-2)">13.9%</span><span class="stat-delta" style="color:var(--accent-2)">CAGR</span></span>
    </div>
    <div class="hero-stat-row">
      <span class="stat-label">IPL 2026 status</span>
      <span><span class="stat-value" style="font-size:20px;color:var(--accent-2)">Live now</span></span>
    </div>
  </div>
</div>

<div class="main">
  <div class="content-area fade-in delay-3">
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('india', this)">India Moments</button>
      <button class="tab-btn" onclick="switchTab('global', this)">Global Trends</button>
      <button class="tab-btn" onclick="switchTab('competitors', this)">Competitors</button>
      <button class="tab-btn" onclick="switchTab('actions', this)">This Week's Actions</button>
    </div>

    <div class="panel active" id="panel-india">
      {INDIA_HTML}
      <div style="margin-top:24px">
        <div class="panel-section-title">Live search — load today's fresh India incidents</div>
        <div class="ai-output" id="india-ai-output"></div>
        <button class="ai-fetch-btn" onclick="fetchLive('india')">↻ Search India incidents right now</button>
      </div>
    </div>

    <div class="panel" id="panel-global">
      <div class="panel-section">
        <div class="panel-section-title">Global category intelligence</div>
        {GLOBAL_HTML}
      </div>
      <div style="margin-top:24px">
        <div class="panel-section-title">Live search — load fresh global trends</div>
        <div class="ai-output" id="global-ai-output"></div>
        <button class="ai-fetch-btn" onclick="fetchLive('global')">↻ Search global trends right now</button>
      </div>
    </div>

    <div class="panel" id="panel-competitors">
      <div class="panel-section">
        <div class="panel-section-title">India competitor landscape</div>
        <div class="comp-grid">
          <div class="comp-card">
            <div class="comp-name">Fast&amp;Up</div>
            <div class="comp-desc">Effervescent tabs, pan-India. Launched electrolyte popsicles with NOTO (₹102). Aam panna + cola flavours show Indian palate ambition.</div>
            <span class="threat-chip" style="background:rgba(212,68,68,.1);color:#e06060;border:1px solid rgba(212,68,68,.2)">High threat</span>
          </div>
          <div class="comp-card">
            <div class="comp-name">Powerade (Coca-Cola)</div>
            <div class="comp-desc">Power Water zero-sugar launched India Nov 2025. First serious clean-label move from a major. Watch for wider rollout.</div>
            <span class="threat-chip" style="background:rgba(196,124,90,.1);color:var(--accent-3);border:1px solid rgba(196,124,90,.2)">Watch closely</span>
          </div>
          <div class="comp-card">
            <div class="comp-name">Campa (Reliance)</div>
            <div class="comp-desc">₹10 SKU via vertical integration. Forcing portfolio segmentation decisions across all incumbents.</div>
            <span class="threat-chip" style="background:rgba(196,124,90,.1);color:var(--accent-3);border:1px solid rgba(196,124,90,.2)">Price pressure</span>
          </div>
          <div class="comp-card">
            <div class="comp-name">MuscleBlaze</div>
            <div class="comp-desc">India's largest sports nutrition brand. If they scale electrolytes with their distribution, it's a direct threat.</div>
            <span class="threat-chip" style="background:rgba(200,184,130,.08);color:var(--accent);border:1px solid rgba(200,184,130,.15)">Monitor</span>
          </div>
          <div class="comp-card">
            <div class="comp-name">Supply6</div>
            <div class="comp-desc">D2C, high-sodium, blue-collar. Different ICP from Osmo — validates category with non-gym audiences.</div>
            <span class="threat-chip" style="background:rgba(138,173,138,.08);color:var(--accent-2);border:1px solid rgba(138,173,138,.15)">Low</span>
          </div>
          <div class="comp-card">
            <div class="comp-name">Enerzal / ORS</div>
            <div class="comp-desc">Govt actively pushing ORS for heatwave victims — creates "upgrade" narrative opportunity for Osmo.</div>
            <span class="threat-chip" style="background:rgba(138,173,138,.08);color:var(--accent-2);border:1px solid rgba(138,173,138,.15)">Low · Opportunity</span>
          </div>
        </div>
      </div>
      <div style="margin-top:8px">
        <div class="panel-section-title">AI competitor intelligence</div>
        {COMPETITOR_HTML}
      </div>
      <div style="margin-top:16px">
        <div class="ai-output" id="competitors-ai-output"></div>
        <button class="ai-fetch-btn" onclick="fetchLive('competitors')">↻ Search competitor news right now</button>
      </div>
    </div>

    <div class="panel" id="panel-actions">
      <div class="panel-section">
        <div class="panel-section-title">This week — {TODAY}</div>
        {ACTIONS_HTML}
      </div>
      <div style="margin-top:8px">
        <div class="panel-section-title">Generate custom brief</div>
        <div class="ai-output" id="actions-ai-output"></div>
        <button class="ai-fetch-btn" onclick="brief('weekly_brief')">↗ Generate full weekly brief in Claude</button>
      </div>
    </div>
  </div>

  <div class="sidebar fade-in delay-4">
    <div class="sidebar-block">
      <div class="sidebar-title">Opportunity heat map</div>
      {HEATMAP_HTML}
    </div>

    <div class="sidebar-block">
      <div class="sidebar-title">Upcoming triggers</div>
      {TRIGGERS_HTML}
    </div>

    <div class="sidebar-block">
      <div class="sidebar-title">Osmo positioning map</div>
      <svg viewBox="0 0 260 200" style="width:100%;font-family:var(--font-mono)">
        <line x1="130" y1="10" x2="130" y2="190" stroke="rgba(255,255,255,0.1)" stroke-width="0.5"/>
        <line x1="10" y1="100" x2="250" y2="100" stroke="rgba(255,255,255,0.1)" stroke-width="0.5"/>
        <text x="130" y="8" fill="#3a3a37" font-size="8" text-anchor="middle">HIGH SCIENCE</text>
        <text x="130" y="198" fill="#3a3a37" font-size="8" text-anchor="middle">LOW SCIENCE</text>
        <text x="12" y="104" fill="#3a3a37" font-size="8">LOW PRICE</text>
        <text x="182" y="104" fill="#3a3a37" font-size="8">HIGH PRICE</text>
        <circle cx="195" cy="35" r="8" fill="rgba(200,184,130,0.2)" stroke="#c8b882" stroke-width="1.5"/>
        <text x="195" y="26" fill="#c8b882" font-size="9" text-anchor="middle" font-weight="500">Osmo</text>
        <circle cx="80" cy="140" r="5" fill="rgba(196,124,90,0.15)" stroke="var(--accent-3)" stroke-width="1"/>
        <text x="80" y="155" fill="var(--accent-3)" font-size="8" text-anchor="middle">Supply6</text>
        <circle cx="55" cy="155" r="5" fill="rgba(90,87,82,0.3)" stroke="#5a5752" stroke-width="1"/>
        <text x="55" y="170" fill="#5a5752" font-size="8" text-anchor="middle">ORS</text>
        <circle cx="115" cy="70" r="5" fill="rgba(138,173,138,0.15)" stroke="var(--accent-2)" stroke-width="1"/>
        <text x="115" y="63" fill="var(--accent-2)" font-size="8" text-anchor="middle">Fast&amp;Up</text>
        <circle cx="170" cy="80" r="5" fill="rgba(90,87,82,0.3)" stroke="#5a5752" stroke-width="1"/>
        <text x="175" y="73" fill="#5a5752" font-size="8" text-anchor="middle">Liq.IV</text>
        <circle cx="200" cy="85" r="5" fill="rgba(90,87,82,0.3)" stroke="#5a5752" stroke-width="1"/>
        <text x="220" y="84" fill="#5a5752" font-size="8">LMNT</text>
        <text x="195" y="55" fill="rgba(200,184,130,0.3)" font-size="7" text-anchor="middle">White space</text>
      </svg>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-title">Quick actions</div>
      <div style="display:flex;flex-direction:column;gap:8px">
        <button class="ai-fetch-btn" style="font-size:9px;padding:8px 12px" onclick="brief('weekly_brief')">Generate full weekly brief →</button>
        <button class="ai-fetch-btn" style="font-size:9px;padding:8px 12px" onclick="brief('heatwave_carousel')">Write heatwave social copy →</button>
        <button class="ai-fetch-btn" style="font-size:9px;padding:8px 12px" onclick="brief('competitor_alert')">Latest competitor alert →</button>
      </div>
    </div>
  </div>
</div>

<footer>
  <div class="footer-txt">Electrolyte Intelligence · Internal use · Auto-refreshed daily at 07:00 IST</div>
  <div class="footer-txt">Generated {TODAY} · Powered by Claude {MODEL.upper()}</div>
</footer>

<script>
  const CLAUDE_API = 'https://api.anthropic.com/v1/messages';
  {BRIEF_JS}

  function switchTab(tab, btn) {{
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-' + tab).classList.add('active');
  }}

  function toggleCard(head) {{
    head.nextElementSibling.classList.toggle('open');
  }}

  function brief(type) {{
    const msg = BRIEF_PROMPTS[type] || 'Give me a detailed marketing brief for Osmo electrolytes India.';
    window.open('https://claude.ai/new?q=' + encodeURIComponent(msg), '_blank');
  }}

  const SYS = 'You are an electrolyte market intelligence analyst for Osmo India. Return a JSON array of 3 insight objects. Each: title, urgency ("critical"|"high"|"medium"|"low"), what (2 sentences), angle (bold 1-sentence marketing hook), tag (short descriptor). ONLY valid JSON array, no markdown.';

  async function fetchLive(section) {{
    const el = document.getElementById(section + '-ai-output');
    el.innerHTML = '<div class="sk sk-card"></div><div class="sk sk-card" style="height:70px"></div>';
    const prompts = {{
      india: 'India is in a severe 2026 heatwave — 46.9°C, census worker deaths, IPL ongoing, NDMA alerts active. Generate 3 fresh India marketing moment insights for Osmo electrolytes right now.',
      global: 'Global electrolyte market $43B, India fastest growing at 13.9% CAGR. Clean-label shift, zero-sugar dominant, Powerade Power Water India launch. Generate 3 global trend insights for Osmo.',
      competitors: 'India 2026: Fast&Up electrolyte popsicles, Powerade Power Water zero-sugar, Campa ₹10 SKU, MuscleBlaze scaling. Generate 3 competitor intelligence insights — white space for Osmo.'
    }};
    try {{
      const res = await fetch(CLAUDE_API, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{model: 'claude-haiku-4-5-20251001', max_tokens: 800, system: SYS, messages: [{{role:'user', content: prompts[section]}}]}})
      }});
      const data = await res.json();
      const raw = data.content?.find(b => b.type === 'text')?.text || '[]';
      const items = JSON.parse(raw.replace(/```json|```/g,'').trim());
      const urgClass = {{critical:'urg-critical',high:'urg-high',medium:'urg-medium',low:'urg-low'}};
      el.innerHTML = items.map(i => `
        <div class="insight-card" style="margin-bottom:10px">
          <div class="insight-card-head" onclick="toggleCard(this)">
            <div class="insight-card-title">${{i.title}}</div>
            <span class="urgency-badge ${{urgClass[i.urgency]||'urg-medium'}}">${{i.urgency}}</span>
          </div>
          <div class="insight-card-body">
            <div class="insight-block"><div class="insight-block-label">Summary</div><div class="insight-block-text">${{i.what}}</div></div>
            <div class="insight-block"><div class="insight-block-label">Angle</div><div class="insight-block-text"><strong>${{i.angle}}</strong></div></div>
            <div class="card-tag-row"><span class="card-tag">${{i.tag}}</span></div>
          </div>
        </div>`).join('');
    }} catch(e) {{
      el.innerHTML = '<div style="font-family:var(--font-mono);font-size:10px;color:var(--text-3);padding:10px 0">Live search unavailable — API key needed in browser context.</div>';
    }}
  }}
</script>
</body>
</html>"""

# ── WRITE OUTPUT ──────────────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(__file__), "index.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ index.html written ({len(html):,} bytes)")
print(f"   Date: {TODAY}")
print(f"   India insights: {len(india_items)}")
print(f"   Global insights: {len(global_items)}")
print(f"   Competitor insights: {len(competitor_items)}")
print(f"   Actions: {len(actions)}")
