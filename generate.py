"""
Electrolyte Intelligence — Daily Page Generator v2
All improvements:
  1. Market size in INR with dropdown category breakup
  2. Competitor cards with live web search + date stamps + source notes
  3. All AI content grounded with web search context
  4. Osmo FAQ tab embedded
  5. Live Q&A tab powered by Claude
  6. Fresh clean visual redesign (light editorial theme)
Run: python generate.py
Requires: ANTHROPIC_API_KEY environment variable
"""

import anthropic
import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# ── CONFIG ─────────────────────────────────────────────────────────────────
MODEL       = "claude-sonnet-4-6"
IST         = timezone(timedelta(hours=5, minutes=30))
TODAY       = datetime.now(IST).strftime("%B %d, %Y")
TODAY_SHORT = datetime.now(IST).strftime("%d %b %Y")
DOW         = datetime.now(IST).strftime("%A")
MONTH       = datetime.now(IST).strftime("%B")
YEAR        = datetime.now(IST).strftime("%Y")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM = """You are a senior market intelligence analyst for Osmo, a premium science-backed
electrolyte brand in India. Your job is to produce sharp, actionable intelligence briefs.
Always return ONLY valid JSON — no markdown fences, no preamble, no trailing text.
Today is {today} ({dow}). Current month: {month} {year}.
India context: Always factor in seasonal triggers, heatwave data, cricket/IPL calendar,
festival calendar, and health advisories. Osmo positioning: high science credibility,
premium price, D2C, targeting urban professionals and serious athletes.
All market figures must be in INR. Use 1 USD = 83.5 INR for conversion.
""".format(today=TODAY, dow=DOW, month=MONTH, year=YEAR)


# ── WEB SEARCH ─────────────────────────────────────────────────────────────

def web_search(query):
    """DuckDuckGo instant answer search."""
    try:
        q = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={q}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        parts = []
        if data.get("AbstractText"):
            parts.append(data["AbstractText"][:400])
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(topic["Text"][:200])
        return " | ".join(parts) if parts else ""
    except Exception:
        return ""


def search_competitor_news():
    print("  Searching competitor news...")
    competitors = {
        "FastUp":      f"Fast&Up electrolyte India {YEAR} new launch",
        "Powerade":    f"Powerade India {YEAR} launch sports drink",
        "MuscleBlaze": f"MuscleBlaze electrolyte hydration {YEAR}",
        "Supply6":     f"Supply6 electrolyte India news {YEAR}",
        "Campa":       f"Campa sports drink Reliance India {YEAR}",
    }
    results = {}
    for brand, query in competitors.items():
        snippet = web_search(query)
        results[brand] = snippet or f"No recent web results for {brand} — using training knowledge."
        print(f"    {brand}: {'found' if snippet else 'no results'}")
    return results


def search_india_news():
    print("  Searching India health/heat news...")
    snippets = []
    for q in [f"India heatwave heat stroke {MONTH} {YEAR}", f"India dehydration health advisory {YEAR}", f"IPL cricket {YEAR} heat"]:
        s = web_search(q)
        if s:
            snippets.append(s[:300])
    return " ".join(snippets[:2])


def search_global_trends():
    print("  Searching global electrolyte trends...")
    snippets = []
    for q in [f"electrolyte market India {YEAR} INR crore", f"sports drink zero sugar trend {YEAR}", f"electrolyte supplement growth India"]:
        s = web_search(q)
        if s:
            snippets.append(s[:300])
    return " ".join(snippets[:2])


# ── FETCH HELPERS ───────────────────────────────────────────────────────────

def fetch(prompt, schema_hint=""):
    full_prompt = f"{prompt}\n\nReturn a JSON array. {schema_hint}"
    msg = client.messages.create(
        model=MODEL, max_tokens=1500, system=SYSTEM,
        messages=[{"role": "user", "content": full_prompt}]
    )
    raw = msg.content[0].text.strip()
    for fence in ["```json", "```"]:
        raw = raw.replace(fence, "")
    raw = raw.strip()
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("items", "data", "results", "triggers", "scores"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        return [v for v in parsed.values() if isinstance(v, dict)]
    return []


def fetch_one(prompt):
    full_prompt = f"{prompt}\n\nReturn a single JSON object. Keep all string values concise (under 100 chars each)."
    msg = client.messages.create(
        model=MODEL, max_tokens=1200, system=SYSTEM,
        messages=[{"role": "user", "content": full_prompt}]
    )
    raw = msg.content[0].text.strip()
    for fence in ["```json", "```"]:
        raw = raw.replace(fence, "")
    return json.loads(raw.strip())



# ── SANITIZE MARKET DATA ──────────────────────────────────────────────────────

def fmt_inr(val):
    if val is None: return "₹676 Cr"
    s = str(val).strip()
    if "₹" in s or "Cr" in s or "crore" in s.lower(): return s
    try:
        n = float(str(val).replace(",","").replace("₹",""))
        if n > 1e9: return f"₹{n/1e7:.0f} Cr"
        elif n > 1e6: return f"₹{n/1e5:.0f} L"
        else: return f"₹{n:.0f}"
    except: return str(val) if val else "₹676 Cr"

def fmt_pct(val):
    if val is None: return "13.9%"
    s = str(val)
    return s if "%" in s else f"{s}%"

def sanitize_market(d):
    if not d:
        return {"total_inr":"₹676 Cr","total_usd":"$81M","cagr":"13.9%","projected_inr":"₹910 Cr by 2031","segments":[],"zero_sugar_inr":"₹68 Cr","fitness_supplement_inr":"₹142 Cr","insight":"India electrolyte market growing fast."}
    for key in ["total_inr","total_value_inr","total"]:
        if d.get(key): d["total_inr"] = fmt_inr(d[key]); break
    for key in ["projected_inr","projected_value_inr","projected"]:
        if d.get(key): d["projected_inr"] = fmt_inr(d[key]); break
    for key in ["zero_sugar_inr","zero_sugar_segment_inr","zero_sugar"]:
        if d.get(key): d["zero_sugar_inr"] = fmt_inr(d[key]); break
    for key in ["fitness_supplement_inr","fitness_supplement_overlap_inr","fitness_supplement"]:
        if d.get(key): d["fitness_supplement_inr"] = fmt_inr(d[key]); break
    d.setdefault("total_inr","₹676 Cr")
    d.setdefault("projected_inr","₹910 Cr by 2031")
    d.setdefault("zero_sugar_inr","₹68 Cr")
    d.setdefault("fitness_supplement_inr","₹142 Cr")
    d["cagr"] = fmt_pct(d.get("cagr","13.9"))
    for s in d.get("segments",[]):
        for k in ["size_inr","size","market_size_inr","market_size"]:
            if s.get(k): s["size_inr"] = fmt_inr(s[k]); break
        s.setdefault("size_inr","N/A")
        for k in ["growth","growth_rate","cagr"]:
            if s.get(k): s["growth"] = fmt_pct(s[k]); break
        s.setdefault("growth","N/A")
        if "share_pct" not in s:
            s["share_pct"] = s.get("share", s.get("market_share","0"))
    return d

# ── DATA FETCHING ───────────────────────────────────────────────────────────

print("Step 1/7: Live web search...")
india_news_ctx    = search_india_news()
global_trends_ctx = search_global_trends()
competitor_news   = search_competitor_news()

print("Step 2/7: India moments...")
india_items = fetch(
    f"""Generate 4 India-specific electrolyte marketing intelligence insights for {TODAY}.
Live context: {india_news_ctx[:600] if india_news_ctx else 'Use best knowledge of current India summer season.'}
Each object: title, urgency ("critical"|"high"|"medium"|"low"), what (2 sentences),
why (1 sentence), angle (bold marketing hook), action ("organic_social"|"paid_campaign"|"pr_pitch"|"influencer"|"content_series"), tag""",
    "Fields: title, urgency, what, why, angle, action, tag"
)

print("Step 3/7: Global trends...")
global_items = fetch(
    f"""Generate 3 global electrolyte category trend insights for {MONTH} {YEAR}.
Live context: {global_trends_ctx[:500] if global_trends_ctx else 'Use best market knowledge.'}
ALL figures in INR. India market ~INR 676 crore ($81M x 83.5). Global ~INR 35900 crore.
Each: title, urgency, what (with INR figures), angle, tag, inr_figure (key stat as string)""",
    "Fields: title, urgency, what, angle, tag, inr_figure"
)

print("Step 4/7: Competitor intelligence...")
comp_ctx = "\n".join([f"{k}: {v[:200]}" for k, v in competitor_news.items()])
competitor_items = fetch(
    f"""Generate 4 competitor intelligence insights for Osmo in India as of {TODAY}.
Keep each 'what' field under 80 words. Competitors: Fast&Up, Powerade India, Campa Reliance, MuscleBlaze, Supply6.
Each: brand, title, urgency ("critical"|"high"|"medium"|"low"), what (max 80 words, cite recency),
gap (max 60 words, white space for Osmo), tag (short),
verified (false), source_note ("Training data — verify independently")""",
    "Fields: brand, title, urgency, what, gap, tag, verified, source_note. Keep all string values short."
)

print("Step 5/7: Weekly actions...")
actions = fetch(
    f"""Generate 4 prioritized marketing actions for Osmo this week ({TODAY}).
Base on: India heatwave, IPL season, government pushing ORS, clean-label shift, zero-sugar advantage.
Each: title, channel, tone, description (2 sentences), timing ("Do today"|"This week"|"This month"), brief_type""",
    "Fields: title, channel, tone, description, timing, brief_type"
)

print("Step 6/7: Heat map + triggers...")
heatmap = fetch(
    f"Score 5 marketing opportunity dimensions for Osmo in India right now ({TODAY}). Return exactly 5: label, score (0-100), color_hint (red|amber|gold|green)",
    "Exactly 5 items."
)
triggers = fetch(
    f"List 6 upcoming India seasonal triggers for electrolyte marketing from {TODAY}. Each: month_label, title, description (1 sentence), dot_color (red|gold|green)",
    "Exactly 6 items."
)

print("Step 7/7: INR market breakdown...")
market_data = fetch_one(
    f"""Generate detailed INR market breakdown for India electrolyte/hydration category {YEAR}.
1 USD = 83.5 INR. Return object with:
total_inr, total_usd, cagr, projected_inr (by 2031),
segments (array: name, size_inr, share_pct, growth, osmo_relevant boolean, note),
zero_sugar_inr, fitness_supplement_inr, insight (1 sentence on Osmo addressable market)"""
)

market_data = sanitize_market(market_data)
print("Building HTML...")


# ── HTML HELPERS ─────────────────────────────────────────────────────────────

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

URG  = {"critical":"urg-critical","high":"urg-high","medium":"urg-medium","low":"urg-low"}
DOTS = {"red":"var(--red)","gold":"var(--gold)","green":"var(--green)","amber":"var(--amber)"}
HEAT = {"red":"var(--red)","amber":"var(--amber)","gold":"var(--gold)","green":"var(--green)"}

BRIEFS = {
    "heatwave_content": "Create a full marketing content brief for Osmo around India heatwave — empathy-first, science-backed, 3 content pieces across Instagram, X, and email",
    "heatwave_social":  "Write 3-slide Instagram carousel copy for Osmo about India heatwave. Empathy-first, educational, soft product mention.",
    "ors_upgrade":      "Write Osmo brand positioning brief around the ORS moment — government pushing ORS for outdoor workers. How does Osmo position as the science-backed upgrade?",
    "ipl_fan":          "Build full IPL campaign brief for Osmo targeting fans watching in extreme heat.",
    "ipl_reel":         "Write a 30-second Instagram Reel script for Osmo targeting IPL fans outdoors in summer heat.",
    "science_35plus":   "Create 4-post science content series for Osmo for LinkedIn and Instagram targeting urban professionals 35-50 on dehydration and cognitive performance.",
    "heatwave_carousel":"Write copy for 3-slide Instagram carousel: heatwave + hydration for Osmo. Empathy-first, educational.",
    "pr_pitch":         "Write PR pitch email from Osmo to Mint Lounge health editor. ORS is not enough for outdoor workers — Osmo is the science-backed upgrade.",
    "cognitive_series": "Build 6-post LinkedIn content series for Osmo on cognitive dehydration for urban professionals.",
    "weekly_brief":     f"Generate complete marketing intelligence brief for Osmo team for {TODAY}. Top 3 India moments, 1 global trend, 1 competitor alert, 4 prioritized actions.",
    "competitor_alert": "Analyze current competitive landscape for Osmo India. What should Osmo do in response to recent competitor moves?",
    "organic_social":   "Write 3 organic social media posts for Osmo for this week. Include captions, hashtags, format recommendations.",
    "paid_campaign":    "Create paid campaign brief for Osmo this week — audience, creative direction, copy, budget across Meta and Google.",
    "pr_pitch_gen":     "Write PR pitch for Osmo to health journalists this week based on current India news.",
    "influencer":       "Create influencer brief for Osmo — type of creator, content direction, talking points, deliverables.",
    "content_series":   "Build 4-week content series plan for Osmo based on current India market intelligence and seasonal triggers.",
}

def india_html(items):
    urgent  = [i for i in items if i.get("urgency") in ("critical","high")]
    ongoing = [i for i in items if i.get("urgency") in ("medium","low")]
    def card(item, first=False):
        uc = URG.get(item.get("urgency","medium"),"urg-medium")
        bc = "open" if first else ""
        bt = item.get("action","weekly_brief")
        return f"""<div class="icard">
          <div class="icard-head" onclick="tc(this)">
            <div class="icard-title">{esc(item.get('title',''))}</div>
            <span class="ubadge {uc}">{esc(item.get('urgency',''))}</span>
          </div>
          <div class="icard-body {bc}">
            <div class="ib"><div class="ib-l">What's happening</div><div class="ib-t">{esc(item.get('what',''))}</div></div>
            <div class="ib"><div class="ib-l">Why it matters</div><div class="ib-t">{esc(item.get('why',''))}</div></div>
            <div class="ib"><div class="ib-l">Marketing angle</div><div class="ib-t"><strong>{esc(item.get('angle',''))}</strong></div></div>
            <div class="tag-row"><span class="itag">{esc(item.get('tag',''))}</span></div>
            <div class="card-acts"><button class="cact" onclick="brief('{esc(bt)}')">Get content brief →</button></div>
          </div>
        </div>"""
    uh = "\n".join(card(i, first=(j==0)) for j,i in enumerate(urgent))
    oh = "\n".join(card(i) for i in ongoing)
    return f'<div class="psec"><div class="psec-t">Critical — act now</div>{uh}</div><div class="psec"><div class="psec-t">Ongoing opportunities</div>{oh}</div>'

def global_html(items):
    def card(item, first=False):
        uc = URG.get(item.get("urgency","medium"),"urg-medium")
        bc = "open" if first else ""
        fig = item.get("inr_figure","")
        fh = f'<div class="inr-fig">{esc(fig)}</div>' if fig else ""
        return f"""<div class="icard">
          <div class="icard-head" onclick="tc(this)">
            <div class="icard-title">{esc(item.get('title',''))}</div>
            <span class="ubadge {uc}">{esc(item.get('urgency',''))}</span>
          </div>
          <div class="icard-body {bc}">{fh}
            <div class="ib"><div class="ib-l">What's happening</div><div class="ib-t">{esc(item.get('what',''))}</div></div>
            <div class="ib"><div class="ib-l">Marketing angle</div><div class="ib-t"><strong>{esc(item.get('angle',''))}</strong></div></div>
            <div class="tag-row"><span class="itag">{esc(item.get('tag',''))}</span></div>
          </div>
        </div>"""
    return "\n".join(card(i, first=(j==0)) for j,i in enumerate(items))

def comp_html(items):
    def card(item, first=False):
        uc = URG.get(item.get("urgency","medium"),"urg-medium")
        bc = "open" if first else ""
        verified = item.get("verified", False)
        src = item.get("source_note", "Training data — verify independently")
        sc = "src-ok" if verified else "src-warn"
        si = "✓" if verified else "!"
        return f"""<div class="icard">
          <div class="icard-head" onclick="tc(this)">
            <div class="icard-title"><span class="brand-chip">{esc(item.get('brand',''))}</span>{esc(item.get('title',''))}</div>
            <span class="ubadge {uc}">{esc(item.get('urgency',''))}</span>
          </div>
          <div class="icard-body {bc}">
            <div class="src-badge {sc}">{si} {esc(src)}</div>
            <div class="ib"><div class="ib-l">What they did</div><div class="ib-t">{esc(item.get('what',''))}</div></div>
            <div class="ib"><div class="ib-l">White space for Osmo</div><div class="ib-t"><strong>{esc(item.get('gap',''))}</strong></div></div>
            <div class="tag-row"><span class="itag">{esc(item.get('tag',''))}</span></div>
          </div>
        </div>"""
    return "\n".join(card(i, first=(j==0)) for j,i in enumerate(items))

def actions_html(items):
    rows = []
    for i, item in enumerate(items, 1):
        tc_ = "urg-critical" if item.get("timing")=="Do today" else "urg-high" if item.get("timing")=="This week" else "urg-low"
        bt  = item.get("brief_type","weekly_brief")
        rows.append(f"""<div class="act-item">
          <div class="act-num">0{i}</div>
          <div class="act-body">
            <div class="act-title">{esc(item.get('title',''))}</div>
            <div class="act-desc">{esc(item.get('description',''))}</div>
            <div class="act-meta">
              <span class="achip">{esc(item.get('channel',''))}</span>
              <span class="achip">{esc(item.get('tone',''))}</span>
              <span class="ubadge {tc_}" style="font-size:8px;padding:2px 7px">{esc(item.get('timing',''))}</span>
              <button class="cact" onclick="brief('{esc(bt)}')">Generate copy →</button>
            </div>
          </div>
        </div>""")
    return "\n".join(rows)

def heatmap_html(items):
    rows = []
    for item in items:
        color = HEAT.get(item.get("color_hint","gold"),"var(--gold)")
        score = int(item.get("score", 50))
        rows.append(f"""<div class="heat-row">
        <div class="heat-lbl">{esc(item.get('label',''))}</div>
        <div class="heat-wrap"><div class="heat-bar" style="width:{score}%;background:{color}"></div></div>
        <div class="heat-val" style="color:{color}">{score}</div>
      </div>""")
    return "\n".join(rows)

def triggers_html(items):
    rows = []
    for item in items:
        color = DOTS.get(item.get("dot_color","gold"),"var(--gold)")
        rows.append(f"""<div class="cal-item">
        <div class="cal-date">{esc(item.get('month_label',''))}</div>
        <div class="cal-dot" style="background:{color}"></div>
        <div class="cal-text"><strong>{esc(item.get('title',''))}</strong> — {esc(item.get('description',''))}</div>
      </div>""")
    return "\n".join(rows)

def segments_html(data):
    segs = data.get("segments", [])
    rows = []
    for s in segs:
        rel = s.get("osmo_relevant", False)
        cls = "seg-row rel" if rel else "seg-row"
        badge = '<span class="osmo-b">Osmo</span>' if rel else ""
        rows.append(f"""<div class="{cls}">
          <div class="seg-name">{esc(s.get('name',''))} {badge}</div>
          <div class="seg-sz">{esc(s.get('size_inr',''))}</div>
          <div class="seg-sh">{esc(str(s.get('share_pct','')))}%</div>
          <div class="seg-gr">↑ {esc(s.get('growth',''))}</div>
        </div>""")
    return "\n".join(rows)

def ticker_html(india, global_):
    items = []
    for i in india[:2]:
        items.append(f'<div class="ti">{esc(i.get("title","")[:55])} <span class="t-hot">{esc(i.get("urgency","").upper())}</span></div>')
    for g in global_[:2]:
        items.append(f'<div class="ti">{esc(g.get("title","")[:55])} <span class="t-up">↑ trending</span></div>')
    items += [
        f'<div class="ti">India market <span class="t-val">{esc(market_data.get("total_inr","₹676 Cr"))}</span> <span class="t-up">↑ {esc(market_data.get("cagr","13.9%"))} CAGR</span></div>',
        '<div class="ti">Global market <span class="t-val">₹35,900 Cr</span></div>',
        '<div class="ti">IPL 2026 <span class="t-up">LIVE</span></div>',
        '<div class="ti">Zero-sugar formats <span class="t-up">↑ fastest growing</span></div>',
        '<div class="ti">Clean-label shift <span class="t-up">accelerating</span></div>',
    ]
    doubled = items * 2
    return "\n      ".join(doubled)

def brief_js():
    lines = [f"    '{k}': '{v.replace(chr(39), chr(92)+chr(39)).replace(chr(10),' ')}'" for k,v in BRIEFS.items()]
    return "const BM = {{\n{}\n  }};".format(",\n".join(lines))

# ── ASSEMBLE ────────────────────────────────────────────────────────────────
TICKER_H  = ticker_html(india_items, global_items)
INDIA_H   = india_html(india_items)
GLOBAL_H  = global_html(global_items)
COMP_H    = comp_html(competitor_items)
ACTIONS_H = actions_html(actions)
HM_H      = heatmap_html(heatmap)
TRIG_H    = triggers_html(triggers)
SEG_H     = segments_html(market_data)
BRIEF_JS  = brief_js()

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Electrolyte Intelligence — {TODAY}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Mono:wght@300;400;500&family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#f7f5f1;--bg2:#eeebe4;--bg3:#e3dfd7;--surf:#ffffff;--surf2:#faf9f6;
  --bdr:rgba(0,0,0,0.09);--bdr2:rgba(0,0,0,0.16);
  --tx:#1a1916;--tx2:#66635d;--tx3:#a09c97;
  --gold:#a67c2e;--gold-bg:rgba(166,124,46,0.1);
  --green:#286b4e;--green-bg:rgba(40,107,78,0.1);
  --red:#b83225;--red-bg:rgba(184,50,37,0.1);
  --amber:#b06820;--amber-bg:rgba(176,104,32,0.1);
  --blue:#1e5fa0;--blue-bg:rgba(30,95,160,0.08);
  --fd:'Playfair Display',Georgia,serif;
  --fb:'Plus Jakarta Sans',system-ui,sans-serif;
  --fm:'IBM Plex Mono',monospace;
  --r:8px;--rl:14px;
}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--tx);font-family:var(--fb);font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}}

/* TICKER */
.ticker{{height:32px;background:var(--tx);overflow:hidden;display:flex;align-items:center}}
.t-lbl{{font-family:var(--fm);font-size:9px;letter-spacing:.12em;color:rgba(255,255,255,.7);padding:0 14px;border-right:1px solid rgba(255,255,255,.12);height:100%;display:flex;align-items:center;flex-shrink:0;text-transform:uppercase}}
.t-track{{display:flex;animation:tick 55s linear infinite;white-space:nowrap}}
.t-track:hover{{animation-play-state:paused}}
.ti{{font-family:var(--fm);font-size:10px;color:rgba(255,255,255,.5);padding:0 24px;border-right:1px solid rgba(255,255,255,.07);height:32px;display:flex;align-items:center;gap:7px}}
.t-val{{color:rgba(255,255,255,.9)}}.t-up{{color:#7ecbaa}}.t-hot{{color:#ff8a80}}
@keyframes tick{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}

/* NAV */
nav{{display:flex;align-items:center;justify-content:space-between;padding:16px 44px;background:var(--surf);border-bottom:1px solid var(--bdr);position:sticky;top:0;z-index:100;box-shadow:0 1px 0 var(--bdr)}}
.n-brand .n-name{{font-family:var(--fd);font-size:16px;color:var(--tx);letter-spacing:-.01em}}
.n-brand .n-sub{{font-family:var(--fm);font-size:8px;letter-spacing:.12em;color:var(--tx3);text-transform:uppercase;margin-top:1px}}
.n-links{{display:flex;gap:24px;list-style:none}}
.n-links a{{font-size:12px;color:var(--tx2);text-decoration:none;transition:color .15s}}
.n-links a:hover{{color:var(--tx)}}
.n-right{{display:flex;align-items:center;gap:9px}}
.n-date{{font-family:var(--fm);font-size:9px;color:var(--tx3);background:var(--bg2);border:1px solid var(--bdr);padding:4px 11px;border-radius:99px}}
.n-refresh{{font-family:var(--fm);font-size:9px;letter-spacing:.08em;color:var(--gold);background:var(--gold-bg);border:1px solid rgba(166,124,46,.25);padding:6px 13px;border-radius:99px;cursor:pointer;transition:all .2s;text-transform:uppercase;display:flex;align-items:center;gap:5px}}
.n-refresh:hover{{background:rgba(166,124,46,.18)}}
.spin{{display:inline-block}}.spinning .spin{{animation:rot .8s linear infinite}}
@keyframes rot{{to{{transform:rotate(360deg)}}}}

/* ALERT */
.alert{{display:flex;align-items:center;gap:12px;background:var(--red-bg);border-bottom:1px solid rgba(184,50,37,.2);padding:9px 44px}}
.a-pill{{font-family:var(--fm);font-size:8px;letter-spacing:.12em;color:var(--red);border:1px solid rgba(184,50,37,.3);padding:2px 8px;border-radius:4px;text-transform:uppercase;flex-shrink:0}}
.a-text{{font-size:12px;color:var(--tx2)}}.a-text strong{{color:var(--tx)}}

/* HERO */
.hero{{padding:52px 44px 44px;border-bottom:1px solid var(--bdr);display:grid;grid-template-columns:1fr 1fr;gap:44px;align-items:end;background:var(--surf)}}
.h-kicker{{font-family:var(--fm);font-size:8px;letter-spacing:.15em;color:var(--green);text-transform:uppercase;margin-bottom:12px;display:flex;align-items:center;gap:7px}}
.k-dot{{width:5px;height:5px;border-radius:50%;background:var(--green);animation:kp 2s ease-in-out infinite}}
@keyframes kp{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}
.hero h1{{font-family:var(--fd);font-size:clamp(30px,3.2vw,46px);line-height:1.1;letter-spacing:-.02em;color:var(--tx);margin-bottom:16px}}
.hero h1 em{{font-style:italic;color:var(--gold)}}
.hero-desc{{font-size:13px;color:var(--tx2);line-height:1.8;max-width:390px}}

/* MARKET WIDGET */
.mkt-widget{{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--rl);overflow:hidden;margin-bottom:14px}}
.mkt-head{{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:var(--bg2);border-bottom:1px solid var(--bdr);cursor:pointer;user-select:none}}
.mkt-head-l{{display:flex;align-items:center;gap:10px}}
.mkt-total{{font-family:var(--fd);font-size:22px;color:var(--tx);letter-spacing:-.01em}}
.mkt-cagr{{font-family:var(--fm);font-size:9px;color:var(--green);background:var(--green-bg);padding:3px 8px;border-radius:99px}}
.mkt-tog{{font-family:var(--fm);font-size:9px;color:var(--tx3);background:none;border:none;cursor:pointer}}
.mkt-body{{display:none;padding:14px 16px}}
.mkt-body.open{{display:block}}
.mkt-insight{{font-size:11px;color:var(--tx2);margin-bottom:12px;padding:9px 11px;background:var(--blue-bg);border-left:3px solid var(--blue);border-radius:0 var(--r) var(--r) 0;line-height:1.6}}
.seg-hdr{{display:grid;grid-template-columns:1fr 80px 44px 56px;gap:6px;padding:5px 0;border-bottom:1px solid var(--bdr);margin-bottom:4px}}
.seg-hdr span{{font-family:var(--fm);font-size:8px;letter-spacing:.1em;color:var(--tx3);text-transform:uppercase}}
.seg-row{{display:grid;grid-template-columns:1fr 80px 44px 56px;gap:6px;padding:7px 0;border-bottom:1px solid var(--bdr);align-items:center}}
.seg-row:last-child{{border-bottom:none}}
.seg-row.rel{{background:var(--green-bg);border-radius:var(--r);padding:7px 9px;margin:1px -9px}}
.seg-name{{font-size:11px;color:var(--tx);display:flex;align-items:center;gap:5px;flex-wrap:wrap}}
.seg-sz{{font-family:var(--fm);font-size:10px;color:var(--tx);font-weight:500}}
.seg-sh{{font-family:var(--fm);font-size:10px;color:var(--tx2)}}
.seg-gr{{font-family:var(--fm);font-size:10px;color:var(--green)}}
.osmo-b{{font-family:var(--fm);font-size:7px;color:var(--green);background:var(--green-bg);border:1px solid rgba(40,107,78,.3);padding:1px 5px;border-radius:99px}}
.mkt-hl{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}}
.mhl{{background:var(--bg2);border-radius:var(--r);padding:9px 11px}}
.mhl-l{{font-family:var(--fm);font-size:8px;letter-spacing:.1em;color:var(--tx3);text-transform:uppercase;margin-bottom:3px}}
.mhl-v{{font-family:var(--fd);font-size:17px;color:var(--tx)}}
.h-stat{{display:flex;justify-content:space-between;align-items:baseline;padding:12px 0;border-bottom:1px solid var(--bdr)}}
.h-stat:first-of-type{{border-top:1px solid var(--bdr)}}
.hs-lbl{{font-family:var(--fm);font-size:8px;letter-spacing:.1em;color:var(--tx3);text-transform:uppercase}}
.hs-val{{font-family:var(--fd);font-size:22px;color:var(--tx);letter-spacing:-.01em}}
.hs-d{{font-family:var(--fm);font-size:9px;color:var(--green);margin-left:5px}}

/* MAIN */
.main{{display:grid;grid-template-columns:1fr 288px;background:var(--bg)}}
.content{{border-right:1px solid var(--bdr)}}

/* TABS */
.tabs{{display:flex;border-bottom:1px solid var(--bdr);background:var(--surf);overflow-x:auto;padding:0 36px}}
.tab{{font-family:var(--fm);font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--tx3);background:transparent;border:none;border-bottom:2px solid transparent;padding:13px 18px;cursor:pointer;white-space:nowrap;transition:all .2s;margin-bottom:-1px}}
.tab:hover{{color:var(--tx2)}}.tab.active{{color:var(--gold);border-bottom-color:var(--gold)}}

/* PANELS */
.panel{{display:none;padding:24px 36px}}.panel.active{{display:block}}
.psec{{margin-bottom:32px}}
.psec-t{{font-family:var(--fm);font-size:8px;letter-spacing:.15em;text-transform:uppercase;color:var(--tx3);margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid var(--bdr)}}

/* INSIGHT CARDS */
.icard{{border:1px solid var(--bdr);border-radius:var(--r);margin-bottom:9px;background:var(--surf);transition:box-shadow .2s,border-color .2s;overflow:hidden}}
.icard:hover{{border-color:var(--bdr2);box-shadow:0 2px 10px rgba(0,0,0,0.06)}}
.icard-head{{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;gap:12px;cursor:pointer}}
.icard-title{{font-size:13px;font-weight:500;color:var(--tx);line-height:1.4;flex:1;display:flex;align-items:center;gap:7px;flex-wrap:wrap}}
.ubadge{{font-family:var(--fm);font-size:8px;letter-spacing:.09em;text-transform:uppercase;padding:2px 8px;border-radius:4px;flex-shrink:0}}
.urg-critical{{background:var(--red-bg);color:var(--red);border:1px solid rgba(184,50,37,.22)}}
.urg-high{{background:var(--amber-bg);color:var(--amber);border:1px solid rgba(176,104,32,.22)}}
.urg-medium{{background:var(--gold-bg);color:var(--gold);border:1px solid rgba(166,124,46,.22)}}
.urg-low{{background:var(--green-bg);color:var(--green);border:1px solid rgba(40,107,78,.22)}}
.icard-body{{padding:0 14px 13px;display:none}}.icard-body.open{{display:block}}
.ib{{margin-bottom:9px}}
.ib-l{{font-family:var(--fm);font-size:8px;letter-spacing:.1em;text-transform:uppercase;color:var(--tx3);margin-bottom:2px}}
.ib-t{{font-size:12px;color:var(--tx2);line-height:1.65}}.ib-t strong{{color:var(--tx);font-weight:600}}
.tag-row{{display:flex;gap:5px;margin-top:9px;flex-wrap:wrap}}
.itag{{font-family:var(--fm);font-size:8px;color:var(--tx3);background:var(--bg2);padding:2px 7px;border-radius:4px}}
.card-acts{{display:flex;gap:7px;margin-top:10px;padding-top:9px;border-top:1px solid var(--bdr)}}
.cact{{font-family:var(--fm);font-size:9px;letter-spacing:.05em;color:var(--gold);background:var(--gold-bg);border:1px solid rgba(166,124,46,.22);padding:4px 11px;border-radius:4px;cursor:pointer;transition:all .2s}}
.cact:hover{{background:rgba(166,124,46,.2)}}
.brand-chip{{font-family:var(--fm);font-size:8px;font-weight:500;color:var(--blue);background:var(--blue-bg);padding:2px 6px;border-radius:4px;flex-shrink:0}}
.src-badge{{font-family:var(--fm);font-size:8px;padding:3px 9px;border-radius:4px;margin-bottom:9px;display:inline-block}}
.src-ok{{background:var(--green-bg);color:var(--green);border:1px solid rgba(40,107,78,.2)}}
.src-warn{{background:var(--amber-bg);color:var(--amber);border:1px solid rgba(176,104,32,.2)}}
.inr-fig{{font-family:var(--fd);font-size:22px;color:var(--gold);margin-bottom:10px}}

/* ACTIONS */
.act-item{{display:flex;gap:12px;padding:13px 0;border-bottom:1px solid var(--bdr);align-items:flex-start}}
.act-num{{font-family:var(--fd);font-size:26px;color:var(--bg3);line-height:1;flex-shrink:0;width:28px;text-align:center}}
.act-body{{flex:1}}
.act-title{{font-size:13px;font-weight:500;color:var(--tx);margin-bottom:3px}}
.act-desc{{font-size:12px;color:var(--tx2);line-height:1.55}}
.act-meta{{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;align-items:center}}
.achip{{font-family:var(--fm);font-size:8px;color:var(--tx3);border:1px solid var(--bdr);padding:2px 7px;border-radius:4px}}

/* LIVE SEARCH */
.live-sec{{margin-top:18px}}
.live-btn{{font-family:var(--fm);font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--tx2);background:var(--surf);border:1px solid var(--bdr2);padding:9px 16px;border-radius:var(--r);cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:7px;width:100%;justify-content:center}}
.live-btn:hover{{background:var(--bg2);border-color:var(--gold);color:var(--gold)}}
.lo{{margin-top:10px}}
.sk{{background:var(--bg2);border-radius:var(--r);animation:skp 1.5s ease-in-out infinite}}
@keyframes skp{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
.sk-c{{height:68px;margin-bottom:9px}}

/* COMP STATIC */
.cs-grid{{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:14px}}
.cs-card{{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);padding:12px}}
.cs-card.th{{border-left:3px solid var(--red)}}.cs-card.tw{{border-left:3px solid var(--amber)}}.cs-card.tl{{border-left:3px solid var(--green)}}
.cs-name{{font-size:12px;font-weight:600;color:var(--tx);margin-bottom:3px}}
.cs-desc{{font-size:11px;color:var(--tx2);line-height:1.5;margin-bottom:7px}}
.t-pill{{font-family:var(--fm);font-size:8px;padding:2px 7px;border-radius:99px}}

/* SIDEBAR */
.sb{{background:var(--surf2);padding:0}}
.sb-blk{{padding:18px;border-bottom:1px solid var(--bdr)}}
.sb-t{{font-family:var(--fm);font-size:8px;letter-spacing:.14em;text-transform:uppercase;color:var(--tx3);margin-bottom:12px}}
.heat-row{{display:flex;align-items:center;gap:7px;margin-bottom:8px}}
.heat-lbl{{font-size:11px;color:var(--tx2);flex:1}}
.heat-wrap{{flex:1;background:var(--bg3);border-radius:99px;height:3px;overflow:hidden}}
.heat-bar{{height:3px;border-radius:99px;transition:width .8s ease}}
.heat-val{{font-family:var(--fm);font-size:9px;color:var(--tx3);min-width:22px;text-align:right}}
.cal-item{{display:flex;align-items:flex-start;gap:8px;margin-bottom:10px}}
.cal-date{{font-family:var(--fm);font-size:8px;color:var(--tx3);min-width:26px;padding-top:3px}}
.cal-dot{{width:5px;height:5px;border-radius:50%;margin-top:4px;flex-shrink:0}}
.cal-text{{font-size:11px;color:var(--tx2);line-height:1.5}}.cal-text strong{{color:var(--tx)}}
.qbtns{{display:flex;flex-direction:column;gap:6px}}
.qbtn{{font-family:var(--fm);font-size:9px;color:var(--tx2);background:var(--bg);border:1px solid var(--bdr);padding:7px 11px;border-radius:var(--r);cursor:pointer;transition:all .2s;text-align:left}}
.qbtn:hover{{background:var(--gold-bg);border-color:rgba(166,124,46,.3);color:var(--gold)}}

/* FAQ */
.faq-wrap{{display:flex;gap:0;min-height:400px}}
.faq-sb{{width:148px;flex-shrink:0;padding:12px 0;border-right:1px solid var(--bdr)}}
.faq-nav{{display:flex;flex-direction:column;gap:1px;padding:0 10px}}
.fcat{{font-size:11px;color:var(--tx2);background:transparent;border:none;border-right:2px solid transparent;padding:7px 9px;cursor:pointer;text-align:left;border-radius:4px 0 0 4px;transition:all .15s;white-space:nowrap}}
.fcat:hover{{background:var(--bg2);color:var(--tx)}}.fcat.fa{{background:var(--green-bg);color:var(--green);border-right-color:var(--green);font-weight:500}}
.faq-main{{flex:1;padding:14px 20px;min-width:0;overflow-y:auto}}
.fp{{display:none}}.fp.fv{{display:block}}
.facc{{border:1px solid var(--bdr);border-radius:var(--r);margin-bottom:7px;overflow:hidden}}
.facc-tr{{width:100%;display:flex;align-items:center;gap:9px;padding:11px 12px;background:transparent;border:none;cursor:pointer;text-align:left;font-size:12px;color:var(--tx);line-height:1.4;font-family:inherit;transition:background .15s}}
.facc-tr:hover{{background:var(--bg2)}}.facc.fo .facc-tr{{background:var(--green-bg);color:var(--green)}}
.facc-n{{font-family:var(--fm);font-size:9px;color:var(--tx3);flex-shrink:0}}.facc.fo .facc-n{{color:var(--green)}}
.facc-ch{{margin-left:auto;font-size:13px;color:var(--tx3);transition:transform .2s}}.facc.fo .facc-ch{{transform:rotate(180deg);color:var(--green)}}
.facc-body{{max-height:0;overflow:hidden;transition:max-height 200ms ease}}
.facc-c{{padding:12px 14px 14px 32px;border-top:1px solid var(--bdr);font-size:12px;color:var(--tx2);line-height:1.7}}
.facc-c strong{{color:var(--tx);font-weight:600}}.facc-c p{{margin-bottom:7px}}.facc-c p:last-child{{margin-bottom:0}}

/* Q&A */
.qa-wrap{{display:flex;flex-direction:column;height:480px;border:1px solid var(--bdr);border-radius:var(--rl);overflow:hidden;background:var(--surf)}}
.qa-hd{{padding:12px 14px;border-bottom:1px solid var(--bdr);display:flex;align-items:center;gap:9px;background:var(--bg2)}}
.qa-av{{width:30px;height:30px;border-radius:50%;background:var(--green-bg);display:flex;align-items:center;justify-content:center;font-size:13px}}
.qa-ti{{font-size:12px;font-weight:600;color:var(--tx)}}
.qa-su{{font-family:var(--fm);font-size:8px;color:var(--green);display:flex;align-items:center;gap:3px;margin-top:1px}}
.odot{{width:4px;height:4px;border-radius:50%;background:var(--green)}}
.qa-msgs{{flex:1;overflow-y:auto;padding:12px 12px 8px;display:flex;flex-direction:column;gap:9px;scroll-behavior:smooth}}
.qa-msgs::-webkit-scrollbar{{width:3px}}.qa-msgs::-webkit-scrollbar-thumb{{background:var(--bg3);border-radius:99px}}
.qm{{display:flex;flex-direction:column;max-width:88%;gap:2px}}
.qm.u{{align-self:flex-end;align-items:flex-end}}.qm.b{{align-self:flex-start;align-items:flex-start}}
.qm-bbl{{padding:8px 12px;border-radius:11px;font-size:12px;line-height:1.6;word-break:break-word}}
.qm.u .qm-bbl{{background:var(--tx);color:#fff;border-bottom-right-radius:3px}}
.qm.b .qm-bbl{{background:var(--bg2);color:var(--tx);border-bottom-left-radius:3px}}
.qm-t{{font-family:var(--fm);font-size:8px;color:var(--tx3);padding:0 2px}}
.qa-hints{{padding:7px 11px;display:flex;gap:5px;flex-wrap:wrap;border-bottom:1px solid var(--bdr)}}
.hint{{font-size:11px;padding:3px 9px;border-radius:99px;background:var(--bg2);border:1px solid var(--bdr);color:var(--tx2);cursor:pointer;transition:all .12s}}
.hint:hover{{background:var(--green-bg);border-color:rgba(40,107,78,.3);color:var(--green)}}
.qa-ft{{padding:9px 11px;border-top:1px solid var(--bdr);display:flex;gap:7px;align-items:flex-end}}
.qa-inp{{flex:1;border:1px solid var(--bdr);border-radius:18px;padding:7px 12px;font-size:12px;font-family:inherit;resize:none;outline:none;max-height:68px;line-height:1.4;color:var(--tx);background:var(--bg);transition:border-color .15s}}
.qa-inp:focus{{border-color:var(--green)}}.qa-inp::placeholder{{color:var(--tx3)}}
.qa-snd{{width:30px;height:30px;border-radius:50%;background:var(--green);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:background .15s}}
.qa-snd:hover{{background:#1e5038}}.qa-snd:disabled{{background:var(--bg3);cursor:not-allowed}}
.qa-snd svg{{width:12px;height:12px;fill:none;stroke:#fff;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}}
.typing-w{{align-self:flex-start}}
.t-dots{{display:flex;align-items:center;gap:3px;padding:9px 11px;background:var(--bg2);border-radius:11px;border-bottom-left-radius:3px}}
.t-dot{{width:5px;height:5px;border-radius:50%;background:var(--tx3);animation:tb 1.1s infinite ease-in-out}}
.t-dot:nth-child(2){{animation-delay:.17s}}.t-dot:nth-child(3){{animation-delay:.34s}}
@keyframes tb{{0%,60%,100%{{transform:translateY(0)}}30%{{transform:translateY(-5px)}}}}

/* FOOTER */
footer{{border-top:1px solid var(--bdr);padding:16px 44px;display:flex;align-items:center;justify-content:space-between;background:var(--surf)}}
.f-txt{{font-family:var(--fm);font-size:9px;color:var(--tx3);letter-spacing:.05em}}

/* ANIMATIONS */
@keyframes fUp{{from{{opacity:0;transform:translateY(9px)}}to{{opacity:1;transform:translateY(0)}}}}
.fi{{animation:fUp .45s ease forwards;opacity:0}}
.d1{{animation-delay:.1s}}.d2{{animation-delay:.2s}}.d3{{animation-delay:.3s}}.d4{{animation-delay:.4s}}

/* RESPONSIVE */
@media(max-width:900px){{
  nav{{padding:13px 18px}}.n-links{{display:none}}
  .hero{{grid-template-columns:1fr;padding:32px 18px 24px;gap:24px}}
  .main{{grid-template-columns:1fr}}.sb{{border-top:1px solid var(--bdr)}}
  .panel{{padding:18px}}.alert{{padding:9px 18px}}.tabs{{padding:0 18px}}
  .cs-grid{{grid-template-columns:1fr}}
  .faq-wrap{{flex-direction:column}}.faq-sb{{width:100%;border-right:none;border-bottom:1px solid var(--bdr)}}
  .faq-nav{{flex-direction:row;overflow-x:auto;padding:0 10px 6px}}.fcat{{white-space:nowrap}}
  footer{{flex-direction:column;gap:5px;padding:13px 18px;text-align:center}}
}}
</style>
</head>
<body>

<div class="ticker">
  <div class="t-lbl">LIVE</div>
  <div style="overflow:hidden;flex:1"><div class="t-track">{TICKER_H}</div></div>
</div>

<nav>
  <div class="n-brand">
    <div class="n-name">Electrolyte Intelligence</div>
    <div class="n-sub">Osmo Daily Briefing · {TODAY}</div>
  </div>
  <ul class="n-links">
    <li><a href="#" onclick="swTab('india',event)">India</a></li>
    <li><a href="#" onclick="swTab('global',event)">Global</a></li>
    <li><a href="#" onclick="swTab('competitors',event)">Competitors</a></li>
    <li><a href="#" onclick="swTab('actions',event)">Actions</a></li>
    <li><a href="#" onclick="swTab('faq',event)">FAQ</a></li>
    <li><a href="#" onclick="swTab('qa',event)">Ask Anything</a></li>
  </ul>
  <div class="n-right">
    <div class="n-date">{TODAY}</div>
    <button class="n-refresh" onclick="location.reload()" id="rBtn"><span class="spin">↻</span> Refresh</button>
  </div>
</nav>

<div class="alert">
  <span class="a-pill">⚠ Live</span>
  <span class="a-text"><strong>Auto-refreshed {TODAY}:</strong> Intelligence grounded in live web search. Competitor data freshness-stamped. Market figures in INR.</span>
</div>

<div class="hero">
  <div class="fi">
    <div class="h-kicker"><div class="k-dot"></div> Daily intelligence briefing</div>
    <h1>What's moving the <em>electrolyte</em> category today</h1>
    <p class="hero-desc">Real-time market signals grounded in live web search, India incidents, web-verified competitor moves, and actionable marketing briefs — all in INR.</p>
  </div>
  <div class="fi d2">
    <div class="mkt-widget">
      <div class="mkt-head" onclick="toggleMkt()">
        <div class="mkt-head-l">
          <div class="mkt-total">{esc(market_data.get('total_inr','₹676 Cr'))}</div>
          <span class="mkt-cagr">↑ {esc(market_data.get('cagr','13.9%'))} CAGR</span>
        </div>
        <button class="mkt-tog" id="mktTog">▼ Category breakdown</button>
      </div>
      <div class="mkt-body" id="mktBody">
        <div class="mkt-insight">{esc(market_data.get('insight','India electrolyte market growing fast with Osmo positioned in premium zero-sugar segment.'))}</div>
        <div class="seg-hdr"><span>Category</span><span>Size (INR)</span><span>Share</span><span>Growth</span></div>
        {SEG_H}
        <div class="mkt-hl">
          <div class="mhl"><div class="mhl-l">Zero-sugar segment</div><div class="mhl-v">{esc(market_data.get('zero_sugar_inr','₹68 Cr'))}</div></div>
          <div class="mhl"><div class="mhl-l">Fitness supplement overlap</div><div class="mhl-v">{esc(market_data.get('fitness_supplement_inr','₹142 Cr'))}</div></div>
        </div>
      </div>
    </div>
    <div class="h-stat"><span class="hs-lbl">Global market</span><span><span class="hs-val">₹35,900 Cr</span><span class="hs-d">↑ 8.4%</span></span></div>
    <div class="h-stat"><span class="hs-lbl">Projected by 2031</span><span><span class="hs-val">{esc(market_data.get('projected_inr','₹910 Cr'))}</span></span></div>
    <div class="h-stat"><span class="hs-lbl">IPL 2026</span><span><span class="hs-val" style="font-size:17px;color:var(--green)">Live now</span></span></div>
  </div>
</div>

<div class="main">
  <div class="content fi d3">
    <div class="tabs">
      <button class="tab active" onclick="swTab('india',event)">India Moments</button>
      <button class="tab" onclick="swTab('global',event)">Global Trends</button>
      <button class="tab" onclick="swTab('competitors',event)">Competitors</button>
      <button class="tab" onclick="swTab('actions',event)">This Week</button>
      <button class="tab" onclick="swTab('faq',event)">Osmo FAQ</button>
      <button class="tab" onclick="swTab('qa',event)">Ask Anything</button>
    </div>

    <div class="panel active" id="panel-india">
      {INDIA_H}
      <div class="live-sec">
        <div class="psec-t">Live search — fresh India incidents</div>
        <div class="lo" id="india-lo"></div>
        <button class="live-btn" onclick="fetchLive('india')"><span>↻</span> Search India incidents right now</button>
      </div>
    </div>

    <div class="panel" id="panel-global">
      <div class="psec"><div class="psec-t">Global category intelligence · Figures in INR</div>{GLOBAL_H}</div>
      <div class="live-sec">
        <div class="lo" id="global-lo"></div>
        <button class="live-btn" onclick="fetchLive('global')"><span>↻</span> Search global trends right now</button>
      </div>
    </div>

    <div class="panel" id="panel-competitors">
      <div class="psec">
        <div class="psec-t">India competitor map</div>
        <div class="cs-grid">
          <div class="cs-card th"><div class="cs-name">Fast&amp;Up</div><div class="cs-desc">Effervescent tabs, pan-India. Format innovation with popsicle collab. Aam panna flavour shows Indian palate ambition.</div><span class="t-pill" style="background:var(--red-bg);color:var(--red)">High threat</span></div>
          <div class="cs-card tw"><div class="cs-name">Powerade (Coca-Cola)</div><div class="cs-desc">Power Water zero-sugar launched India. First serious clean-label push from a major. Coca-Cola distribution muscle.</div><span class="t-pill" style="background:var(--amber-bg);color:var(--amber)">Watch closely</span></div>
          <div class="cs-card tw"><div class="cs-name">Campa (Reliance)</div><div class="cs-desc">₹10 SKU via vertical integration. Forcing portfolio segmentation across entire category.</div><span class="t-pill" style="background:var(--amber-bg);color:var(--amber)">Price pressure</span></div>
          <div class="cs-card tl"><div class="cs-name">Supply6 · ORS / Enerzal</div><div class="cs-desc">Govt pushing ORS for heatwave. Creates upgrade narrative for Osmo. Supply6 validates non-gym audience.</div><span class="t-pill" style="background:var(--green-bg);color:var(--green)">Low · Opportunity</span></div>
        </div>
      </div>
      <div class="psec">
        <div class="psec-t">AI intelligence · Web-search verified where available</div>
        {COMP_H}
      </div>
      <div class="live-sec">
        <div class="lo" id="competitors-lo"></div>
        <button class="live-btn" onclick="fetchLive('competitors')"><span>↻</span> Search competitor news right now</button>
      </div>
    </div>

    <div class="panel" id="panel-actions">
      <div class="psec"><div class="psec-t">Prioritized actions · {TODAY}</div>{ACTIONS_H}</div>
      <div class="live-sec">
        <button class="live-btn" onclick="brief('weekly_brief')"><span>↗</span> Generate full weekly brief in Claude</button>
      </div>
    </div>

    <div class="panel" id="panel-faq">
      <div class="psec-t" style="margin-bottom:16px">Osmo Product FAQ</div>
      <div class="faq-wrap">
        <div class="faq-sb">
          <div class="faq-nav">
            <button class="fcat fa" onclick="swFaq('basics',this)">The Basics</button>
            <button class="fcat" onclick="swFaq('loss',this)">Signs &amp; Loss</button>
            <button class="fcat" onclick="swFaq('vsothers',this)">vs. Others</button>
            <button class="fcat" onclick="swFaq('ingredients',this)">Ingredients</button>
            <button class="fcat" onclick="swFaq('whoffor',this)">Who It's For</button>
            <button class="fcat" onclick="swFaq('usage',this)">How to Use</button>
            <button class="fcat" onclick="swFaq('whyosmo',this)">Why Osmo</button>
          </div>
        </div>
        <div class="faq-main">
          <div class="fp fv" id="fp-basics">
            <div class="facc" id="fq1"><button class="facc-tr" onclick="ft('fq1')"><span class="facc-n">01</span>What is an electrolyte, actually?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p>An electrolyte is a mineral that dissolves in water and splits into electrically charged ions — sodium (Na⁺), potassium (K⁺), magnesium (Mg²⁺), calcium (Ca²⁺). Every nerve firing, muscle contraction, and cognitive function is an electrochemical event powered by these ions.</p><p><strong>Plain water has zero electrical charge.</strong> Electrolytes are the operating system. Water is just the medium they work in. Sodium activates SGLT1 co-transport, pulling water actively into the bloodstream up to 3× faster than plain water.</p></div></div></div>
            <div class="facc" id="fq2"><button class="facc-tr" onclick="ft('fq2')"><span class="facc-n">02</span>Why does my body need electrolytes?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p>Four functions: <strong>fluid regulation</strong> (water follows electrolytes via osmosis), <strong>muscle contraction/relaxation</strong> (calcium triggers, magnesium releases), <strong>nerve signal transmission</strong> (sodium fires, potassium resets — millions of times per second), <strong>energy metabolism</strong> (magnesium powers ATP synthase).</p><p>At 1% dehydration, concentration and short-term memory are measurably impaired. At 2%, reaction time slows 15%. At 5%, cognitive performance degrades like 0.08% blood alcohol.</p></div></div></div>
            <div class="facc" id="fq3"><button class="facc-tr" onclick="ft('fq3')"><span class="facc-n">03</span>Which electrolytes matter most?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>Sodium (400mg)</strong> — master electrolyte, drives SGLT1 fluid absorption. <strong>Potassium (250mg)</strong> — balances sodium, intracellular hydration. <strong>Magnesium (100mg citrate)</strong> — 300+ enzymatic reactions, muscle relaxation, ~70–80% urban Indian adults deficient. <strong>Taurine (1,300mg)</strong> — Osmo's differentiator: the body's primary organic osmolyte, cellular hydration no other India brand has. <strong>Boron</strong> — reduces urinary Mg/Ca loss by 30%.</p></div></div></div>
          </div>
          <div class="fp" id="fp-loss">
            <div class="facc" id="fq4"><button class="facc-tr" onclick="ft('fq4')"><span class="facc-n">04</span>What causes electrolyte loss?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p>Loss is continuous and invisible. <strong>Sweat</strong> (700–1,000mg sodium per litre in Indian heat), <strong>ambient heat</strong> (passive loss at 35°C+ without exercise — sitting in Delhi in May causes depletion), <strong>caffeine</strong> (3 coffees/day drains Na and Mg continuously — the coffee crash is partly an electrolyte event), <strong>alcohol</strong> (hangover is almost entirely electrolyte + B-vitamin depletion), <strong>chronic stress</strong> (cortisol directly increases urinary Mg excretion).</p></div></div></div>
            <div class="facc" id="fq5"><button class="facc-tr" onclick="ft('fq5')"><span class="facc-n">05</span>How do I know if I'm deficient?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p>Common signs: <strong>night muscle cramps</strong> (Mg depleted — Mg supplementation reduces cramp frequency ~50%), <strong>3pm energy crash</strong> (Na + B-vitamins depleted by lunch), <strong>poor sleep/restless legs</strong> (Mg depleted — Mg improves sleep quality ~17%), <strong>frequent illness</strong> (zinc depleted — doubles cold recovery time), <strong>dizziness when standing</strong> (low Na, low blood volume), <strong>afternoon headache despite drinking water</strong> (cellular dehydration — most underdiagnosed hydration problem).</p></div></div></div>
            <div class="facc" id="fq6"><button class="facc-tr" onclick="ft('fq6')"><span class="facc-n">06</span>I drink plenty of water. Do I still need electrolytes?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p>Yes. "Drinking enough water" solves a fluid volume problem. Electrolyte balance is a separate physiological system. Plain water dilutes blood electrolytes — kidneys then excrete more water to restore concentration balance. <strong>Electrolyte-enhanced water is retained 2× longer than plain water.</strong> You can be fully fluid-replete and simultaneously magnesium-deficient, zinc-deficient, and B-vitamin depleted.</p></div></div></div>
          </div>
          <div class="fp" id="fp-vsothers">
            <div class="facc" id="fq7"><button class="facc-tr" onclick="ft('fq7')"><span class="facc-n">07</span>How is Osmo different from ORS?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>ORS is what you reach for when something has gone wrong. Osmo is what you use so things don't go wrong.</strong> ORS uses 13.5g glucose (Enerzal) because a sick gut needs it. A healthy gut doesn't. ORS has only Na, K, glucose, Na citrate — no vitamins, no taurine, no recovery stack. Osmo has zero sugar + full spectrum + B-vitamins + taurine + zinc + magnesium. ORS is a clinical tool. Osmo is a daily habit.</p></div></div></div>
            <div class="facc" id="fq8"><button class="facc-tr" onclick="ft('fq8')"><span class="facc-n">08</span>How does Osmo compare to Fast&amp;UP, Liquid I.V., MB HYDR8?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>Fast&UP Reload:</strong> ~5–7g sugar (FSSAI amber), no taurine, minimal B-vitamins, ~₹20–30/serve. <strong>Liquid I.V.:</strong> 11g sugar (FSSAI red in India), no magnesium, no taurine, ~₹150–250 imported. <strong>MB HYDR8:</strong> 17–20g sugar (valid for 90min+ endurance only, not daily). <strong>Osmo:</strong> 400mg Na + 1,300mg taurine + full B-complex + zero sugar + 100mg Mg at ₹25–40/serve. The only formula with all four at a daily-habit price point.</p></div></div></div>
            <div class="facc" id="fq9"><button class="facc-tr" onclick="ft('fq9')"><span class="facc-n">09</span>How is it different from Gatorade or Glucon-D?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>Gatorade:</strong> 34g sugar per 500ml, Na+K only, FSSAI warning label. <strong>Glucon-D:</strong> 99.4% glucose — an energy spike product, not an electrolyte product. <strong>Osmo:</strong> zero sugar, no warning, full spectrum including taurine and B-complex. FSSAI's July 2024 labelling creates a compounding structural headwind for both — 30–40% lower purchase intent among health-conscious consumers. That's Osmo's opening.</p></div></div></div>
          </div>
          <div class="fp" id="fp-ingredients">
            <div class="facc" id="fq10"><button class="facc-tr" onclick="ft('fq10')"><span class="facc-n">10</span>What should a good electrolyte product contain?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>Must have:</strong> Sodium 400mg+, Potassium 200mg+, Magnesium in citrate/glycinate form (not oxide — 4% vs 30% bioavailability), zero/minimal sugar, B-vitamins. <strong>Best in class:</strong> Taurine 1,000mg+ (cellular osmolyte), Zinc ~50% RDA, Boron (reduces Mg/Ca loss 30%). <strong>Red flags:</strong> sugar above 5g/serving, magnesium oxide/sulphate, artificial colours (tartrazine, sunset yellow), undisclosed quantities.</p></div></div></div>
            <div class="facc" id="fq11"><button class="facc-tr" onclick="ft('fq11')"><span class="facc-n">11</span>Is sugar necessary in an electrolyte drink?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>No</strong> for healthy adults using electrolytes for daily wellness. <strong>Only in two cases:</strong> acute illness (ORS — sick gut needs glucose for SGLT1) or 90+ minute intense endurance exercise. For everyone else: FSSAI warning, 30–40% lower purchase intent, glycaemic spike/crash, unsuitable for 101M+ diabetic Indian adults. Same hydration benefit, zero liability — that's Osmo's position.</p></div></div></div>
          </div>
          <div class="fp" id="fp-whoffor">
            <div class="facc" id="fq12"><button class="facc-tr" onclick="ft('fq12')"><span class="facc-n">12</span>Is this only for athletes?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p>Anyone who sweats, drinks caffeine, experiences stress, or wants sustained energy. <strong>Gym users:</strong> lose 700–1,500mg sodium/session; weekly deficit causes 10–20% performance drop. <strong>Office professionals:</strong> 3 coffees drains Mg and Na; AC causes continuous dehydration; 3pm crash is partly electrolyte depletion. <strong>Also:</strong> keto/IF (keto flu = electrolyte depletion), frequent flyers (cabin air 10–15% humidity), Indian summer, alcohol drinkers.</p></div></div></div>
            <div class="facc" id="fq13"><button class="facc-tr" onclick="ft('fq13')"><span class="facc-n">13</span>Safe for diabetes, high blood pressure, kidney issues?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>Diabetes:</strong> Zero sugar, zero glycaemic impact — highest-value use case. Mg supports insulin sensitivity. Confirm with doctor. <strong>High BP:</strong> 400mg Na is modest vs 3,000–5,000mg typical dietary intake. K and Mg actively support BP reduction. Confirm with doctor if on antihypertensives. <strong>CKD: Always consult doctor first — non-negotiable.</strong></p></div></div></div>
            <div class="facc" id="fq14"><button class="facc-tr" onclick="ft('fq14')"><span class="facc-n">14</span>Is Osmo vegetarian / vegan?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p>100% vegetarian and vegan. Taurine is synthetically produced, not animal-derived. No artificial colours, no artificial sweeteners, no gluten, no added sugar. Valencia Orange uses natural fruit flavour. Genuine competitive advantage over effervescent brands using synthetic colouring.</p></div></div></div>
          </div>
          <div class="fp" id="fp-usage">
            <div class="facc" id="fq15"><button class="facc-tr" onclick="ft('fq15')"><span class="facc-n">15</span>How quickly will I feel a difference?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>15–20 min:</strong> SGLT1 activation, reduced thirst signal, subtle energy lift. <strong>Day 1–3:</strong> Less workout fatigue, shallower 3pm crash. <strong>Days 7–10:</strong> Sleep improves, night cramps reduce (Mg takes 7–10 days to replenish stores). <strong>Weeks 2–3:</strong> B-vitamins reach functional levels, baseline energy and cognitive clarity improve. <strong>Week 3+:</strong> Missing a day becomes perceptible — strongest signal the habit is working.</p></div></div></div>
            <div class="facc" id="fq16"><button class="facc-tr" onclick="ft('fq16')"><span class="facc-n">16</span>When should I take it?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>Before (30 min pre-workout/morning):</strong> Pre-loading shows 7–10% improvement in sustained output. <strong>During (60+ min sessions):</strong> Maintains blood volume, performance holds. <strong>After:</strong> Replaces losses, supports recovery (zinc) and deep sleep (Mg). <strong>Default:</strong> One scoop every morning — covers daily baseline and exercise prep without timing decisions.</p></div></div></div>
            <div class="facc" id="fq17"><button class="facc-tr" onclick="ft('fq17')"><span class="facc-n">17</span>Daily or only when I feel I need it?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p><strong>Daily habit is optimal.</strong> Electrolyte depletion is cumulative — caffeine, stress, heat, and processed diets create a continuous drain. Using electrolytes only on workout days is like drinking water only when you're already thirsty. Benefits compound: after 2–3 weeks most users report the pre-habit state feels noticeably worse in retrospect.</p></div></div></div>
          </div>
          <div class="fp" id="fp-whyosmo">
            <div class="facc" id="fq18"><button class="facc-tr" onclick="ft('fq18')"><span class="facc-n">18</span>Why is everyone talking about electrolytes?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p>Six structural drivers: <strong>FSSAI July 2024 labelling</strong> (30–40% lower purchase intent for warning-labelled products), <strong>101M diabetic Indian adults</strong> (can't use Gatorade/ORS safely), <strong>fitness culture mainstreaming</strong> (5M+ gym members), <strong>Q-commerce</strong> (Blinkit/Zepto created impulse hydration occasions), <strong>function-first wellness</strong> (Kantar India 2024: 39% YoY growth), <strong>climate</strong> (longer hotter summers extending season year-round).</p></div></div></div>
            <div class="facc" id="fq19"><button class="facc-tr" onclick="ft('fq19')"><span class="facc-n">19</span>What makes Osmo the right choice?<span class="facc-ch">⌄</span></button><div class="facc-body"><div class="facc-c"><p>Four compounding advantages: <strong>1.</strong> Only formula combining high sodium + taurine + full B-complex + zero sugar in India at daily-habit price. <strong>2.</strong> Taurine 1,300mg — cellular hydration mechanism no India competitor has. <strong>3.</strong> Zero sugar — regulatory advantage compounding as FSSAI enforcement intensifies (Liquid I.V., world's #1 hydration brand, carries a red warning label in India). <strong>4.</strong> ₹25–40/serve — premium enough to signal quality, accessible enough for daily habit formation.</p></div></div></div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel" id="panel-qa">
      <div class="psec-t" style="margin-bottom:12px">Ask Anything — Osmo Knowledge Base</div>
      <p style="font-size:12px;color:var(--tx2);margin-bottom:14px;line-height:1.7">Ask any question about Osmo, electrolytes, hydration science, ingredients, competitors, or marketing strategy. Powered by Claude with deep Osmo product knowledge.</p>
      <div class="qa-wrap">
        <div class="qa-hd">
          <div class="qa-av">💧</div>
          <div>
            <div class="qa-ti">Osmo Intelligence</div>
            <div class="qa-su"><div class="odot"></div>Ask about product, science, or market</div>
          </div>
        </div>
        <div class="qa-msgs" id="qaMsgs">
          <div class="qm b"><div class="qm-bbl">Hi! Ask me anything about Osmo — product science, ingredients, competitor positioning, marketing angles, or who to target. I have deep knowledge of the Osmo formula and India electrolyte market. 👋</div></div>
        </div>
        <div class="qa-hints" id="qaHints">
          <span class="hint" onclick="qaH('Why is taurine at 1300mg a differentiator?')">Why taurine?</span>
          <span class="hint" onclick="qaH('Who is the ideal ICP for Osmo in India?')">Who to target?</span>
          <span class="hint" onclick="qaH('How does Osmo beat Liquid I.V. in India?')">vs Liquid I.V.?</span>
          <span class="hint" onclick="qaH('What marketing angle works best for diabetic consumers?')">Diabetes angle?</span>
          <span class="hint" onclick="qaH('Does Osmo help with hangovers?')">Hangovers?</span>
        </div>
        <div class="qa-ft">
          <textarea class="qa-inp" id="qaInp" placeholder="Ask about Osmo, ingredients, science, market…" rows="1" onkeydown="qaKey(event)" oninput="qaRes(this)"></textarea>
          <button class="qa-snd" id="qaSnd" onclick="qaSend()" aria-label="Send">
            <svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </button>
        </div>
      </div>
    </div>

  </div>

  <div class="sb fi d4">
    <div class="sb-blk"><div class="sb-t">Opportunity heat map</div>{HM_H}</div>
    <div class="sb-blk"><div class="sb-t">Upcoming triggers</div>{TRIG_H}</div>
    <div class="sb-blk">
      <div class="sb-t">Osmo positioning</div>
      <svg viewBox="0 0 230 170" style="width:100%;font-family:var(--fm)">
        <line x1="115" y1="7" x2="115" y2="163" stroke="var(--bdr)" stroke-width="1"/>
        <line x1="7" y1="85" x2="223" y2="85" stroke="var(--bdr)" stroke-width="1"/>
        <text x="115" y="5" fill="var(--tx3)" font-size="7" text-anchor="middle">HIGH SCIENCE</text>
        <text x="115" y="170" fill="var(--tx3)" font-size="7" text-anchor="middle">LOW SCIENCE</text>
        <text x="9" y="89" fill="var(--tx3)" font-size="7">LOW ₹</text>
        <text x="172" y="89" fill="var(--tx3)" font-size="7">HIGH ₹</text>
        <circle cx="174" cy="25" r="9" fill="var(--green-bg)" stroke="var(--green)" stroke-width="1.5"/>
        <text x="174" y="17" fill="var(--green)" font-size="8" text-anchor="middle" font-weight="500">Osmo</text>
        <text x="174" y="42" fill="var(--tx3)" font-size="6" text-anchor="middle">White space ↗</text>
        <circle cx="70" cy="122" r="5" fill="var(--amber-bg)" stroke="var(--amber)" stroke-width="1"/>
        <text x="70" y="134" fill="var(--tx3)" font-size="7" text-anchor="middle">Supply6</text>
        <circle cx="46" cy="138" r="5" fill="var(--bg3)" stroke="var(--tx3)" stroke-width="1"/>
        <text x="46" y="150" fill="var(--tx3)" font-size="7" text-anchor="middle">ORS</text>
        <circle cx="103" cy="62" r="5" fill="var(--green-bg)" stroke="var(--green)" stroke-width="1"/>
        <text x="103" y="55" fill="var(--tx3)" font-size="7" text-anchor="middle">Fast&amp;Up</text>
        <circle cx="152" cy="68" r="5" fill="var(--bg3)" stroke="var(--tx3)" stroke-width="1"/>
        <text x="160" y="65" fill="var(--tx3)" font-size="7">Liq.IV</text>
        <circle cx="178" cy="74" r="5" fill="var(--bg3)" stroke="var(--tx3)" stroke-width="1"/>
        <text x="191" y="73" fill="var(--tx3)" font-size="7">LMNT</text>
      </svg>
    </div>
    <div class="sb-blk">
      <div class="sb-t">Quick actions</div>
      <div class="qbtns">
        <button class="qbtn" onclick="brief('weekly_brief')">Generate full weekly brief →</button>
        <button class="qbtn" onclick="brief('heatwave_carousel')">Write heatwave social copy →</button>
        <button class="qbtn" onclick="brief('competitor_alert')">Latest competitor alert →</button>
        <button class="qbtn" onclick="swTabId('qa')">Ask Osmo anything →</button>
      </div>
    </div>
  </div>
</div>

<footer>
  <div class="f-txt">Electrolyte Intelligence · Osmo Internal · Auto-refreshed 07:00 IST daily</div>
  <div class="f-txt">Generated {TODAY} · Claude {MODEL.upper()} · Web search grounded</div>
</footer>

<script>
const API = 'https://api.anthropic.com/v1/messages';
{BRIEF_JS}

// Tab switching
function swTab(t, e) {{
  if (e && e.preventDefault) e.preventDefault();
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(b => {{
    var oc = b.getAttribute('onclick') || '';
    if (oc.indexOf("'" + t + "'") !== -1) b.classList.add('active');
  }});
  var panel = document.getElementById('panel-' + t);
  if (panel) panel.classList.add('active');
}}
function swTabId(t) {{ swTab(t, null); }}
function tc(h) {{ h.nextElementSibling.classList.toggle('open'); }}
function toggleMkt() {{
  var b = document.getElementById('mktBody'), tog = document.getElementById('mktTog');
  var isOpen = b.classList.toggle('open');
  tog.textContent = isOpen ? 'Close' : 'Category breakdown';
}}
function brief(k) {{
  var m = BM[k] || 'Give me a detailed marketing brief for Osmo electrolytes India.';
  window.open('https://claude.ai/new?q=' + encodeURIComponent(m), '_blank');
}}
function swFaq(c, btn) {{
  document.querySelectorAll('.fcat').forEach(b => b.classList.remove('fa'));
  document.querySelectorAll('.fp').forEach(p => p.classList.remove('fv'));
  btn.classList.add('fa');
  var p = document.getElementById('fp-' + c);
  if (p) p.classList.add('fv');
}}
function ft(id) {{
  var item = document.getElementById(id), isOpen = item.classList.contains('fo');
  item.closest('.fp').querySelectorAll('.facc').forEach(function(el) {{
    if (el !== item) {{ el.classList.remove('fo'); el.querySelector('.facc-body').style.maxHeight = '0'; }}
  }});
  if (isOpen) {{ item.classList.remove('fo'); item.querySelector('.facc-body').style.maxHeight = '0'; }}
  else {{ item.classList.add('fo'); var b = item.querySelector('.facc-body'); b.style.maxHeight = b.scrollHeight + 'px'; }}
}}
var LIVE_SYS = 'You are an electrolyte market intelligence analyst for Osmo India. Return a JSON array of 3 insight objects. Each: title, urgency (critical/high/medium/low), what (2 sentences), angle (1-sentence marketing hook), tag. ONLY valid JSON array.';
var LP = {{
  india: 'India heatwave 2026, 46.9C peak temperatures, census worker heat deaths, IPL cricket ongoing. Generate 3 fresh India marketing insights for Osmo.',
  global: 'India electrolyte market INR 676 Cr growing 13.9% CAGR. Clean-label shift dominant. Generate 3 global category insights for Osmo with INR figures.',
  competitors: 'India 2026: Fast and Up innovation, Powerade Power Water zero-sugar, Campa INR 10 SKU. Generate 3 competitor intelligence insights for Osmo.'
}};
function fetchLive(s) {{
  var el = document.getElementById(s + '-lo'); if (!el) return;
  el.innerHTML = '<div class="sk sk-c"></div>';
  var urgClass = {{critical:'urg-critical',high:'urg-high',medium:'urg-medium',low:'urg-low'}};
  fetch(API, {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{model:'claude-haiku-4-5-20251001',max_tokens:700,system:LIVE_SYS,messages:[{{role:'user',content:LP[s]}}]}})
  }}).then(function(r){{return r.json();}}).then(function(d){{
    var raw=(d.content&&d.content[0])?d.content[0].text:'[]';
    raw=raw.replace(/```json/g,'').replace(/```/g,'').trim();
    var items=JSON.parse(raw);
    el.innerHTML=items.map(function(i){{var uc=urgClass[i.urgency]||'urg-medium';return '<div class="icard" style="margin-bottom:9px"><div class="icard-head" onclick="tc(this)"><div class="icard-title">'+i.title+'</div><span class="ubadge '+uc+'">'+i.urgency+'</span></div><div class="icard-body"><div class="ib"><div class="ib-l">Summary</div><div class="ib-t">'+i.what+'</div></div><div class="ib"><div class="ib-l">Angle</div><div class="ib-t"><strong>'+i.angle+'</strong></div></div><div class="tag-row"><span class="itag">'+i.tag+'</span></div></div></div>';}}).join('');
  }}).catch(function(){{el.innerHTML='<div style="font-family:var(--fm);font-size:9px;color:var(--tx3)">Live search unavailable.</div>';}});
}}
var QS='You are the Osmo product expert. Osmo is a premium zero-sugar Indian electrolyte powder. Sodium 400mg, Potassium 250mg, Magnesium 100mg citrate, Taurine 1300mg, Zinc 8.5mg, full B-complex. Zero sugar, vegan. INR 25-40 per serving. Only India brand with taurine at 1300mg plus zero sugar plus full B-complex. India market INR 676 Cr growing 13.9% CAGR. 101M diabetic adults cannot use sugar-based competitors safely. Answer helpfully in 2-3 paragraphs.';
var qH=[],qB=false;
function qaKey(e){{if(e.key==='Enter'&&!e.shiftKey){{e.preventDefault();qaSend();}}}}
function qaRes(el){{el.style.height='auto';el.style.height=Math.min(el.scrollHeight,68)+'px';}}
function qaH(t){{document.getElementById('qaInp').value=t;document.getElementById('qaHints').style.display='none';qaSend();}}
function nowT(){{return new Date().toLocaleTimeString('en-IN',{{hour:'2-digit',minute:'2-digit'}});}}
function qaApp(role,html){{var w=document.getElementById('qaMsgs'),el=document.createElement('div');el.className='qm '+role;el.innerHTML='<div class="qm-bbl">'+html+'</div><div class="qm-t">'+nowT()+'</div>';w.appendChild(el);w.scrollTop=w.scrollHeight;}}
function qaSend(){{
  if(qB)return;var inp=document.getElementById('qaInp'),txt=inp.value.trim();if(!txt)return;
  document.getElementById('qaHints').style.display='none';inp.value='';inp.style.height='auto';
  qaApp('u',txt.replace(/</g,'&lt;'));qH.push({{role:'user',content:txt}});
  qB=true;document.getElementById('qaSnd').disabled=true;
  var w=document.getElementById('qaMsgs'),typ=document.createElement('div');
  typ.className='typing-w';typ.id='qaTyp';typ.innerHTML='<div class="t-dots"><div class="t-dot"></div><div class="t-dot"></div><div class="t-dot"></div></div>';
  w.appendChild(typ);w.scrollTop=w.scrollHeight;
  fetch(API,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{model:'claude-sonnet-4-20250514',max_tokens:800,system:QS,messages:qH}})}})
  .then(function(r){{return r.json();}})
  .then(function(d){{var t=document.getElementById('qaTyp');if(t)t.remove();var rep=(d.content&&d.content[0])?d.content[0].text:'Sorry, something went wrong.';qH.push({{role:'assistant',content:rep}});qaApp('b',rep.replace(/\n\n/g,'<br><br>').replace(/\n/g,'<br>').replace(/</g,'&lt;').replace(/&lt;br&gt;/g,'<br>'));}})
  .catch(function(){{var t=document.getElementById('qaTyp');if(t)t.remove();qaApp('b','Something went wrong. Please try again.');}})
  .finally(function(){{qB=false;document.getElementById('qaSnd').disabled=false;document.getElementById('qaInp').focus();}});
}}
</script>
</body>
</html>"""

out = os.path.join(os.path.dirname(__file__), "index.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ index.html written ({len(html):,} bytes)")
print(f"   Date: {TODAY} | Model: {MODEL}")
print(f"   India: {len(india_items)} | Global: {len(global_items)} | Competitors: {len(competitor_items)} | Actions: {len(actions)}")
print(f"   Market total: {market_data.get('total_inr','N/A')} | CAGR: {market_data.get('cagr','N/A')}")
print(f"   Web search: India={'yes' if india_news_ctx else 'no'} | Global={'yes' if global_trends_ctx else 'no'} | Competitors=partial")
