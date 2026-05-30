"""
Electrolyte Intelligence — Daily Page Generator (v3 with v2 design)

Produces the v2 light-editorial dark-theme page with:
  - 6 AI-refreshed sections (India, Global, Competitor AI, Actions, Heatmap, Triggers) — daily Claude fetch
  - 1 NEW Radar section — daily AI scan for new launches & brand moves in India
  - Curated data lists (Events, Entrants, Pricing, Competitor landscape) — edit in Python, push, regenerates
  - Auto-calculated countdowns ("in N days") and "X days ago" labels
  - Today's date stamps auto-fresh

Run: ANTHROPIC_API_KEY=sk-ant-... python3 generate.py
Triggered daily at 07:00 IST via .github/workflows/daily-refresh.yml
"""

import anthropic
import json
import os
import sys
import re
import time
from datetime import datetime, timezone, timedelta, date

# ── CONFIG ──────────────────────────────────────────────────────────────────
MODEL = "claude-sonnet-4-6"

# Manually-verified date for the competitor PRICING_DATA table below.
# IMPORTANT: bump this ONLY when you actually re-check the live prices.
# It must NOT auto-update with the page — that would falsely imply prices
# were re-verified every morning when they're hardcoded.
PRICING_VERIFIED = "May 29, 2026"
IST   = timezone(timedelta(hours=5, minutes=30))
NOW   = datetime.now(IST)
TODAY_DATE  = NOW.date()
TODAY = NOW.strftime("%B %d, %Y")        # "May 11, 2026"
DOW   = NOW.strftime("%A")
MONTH = NOW.strftime("%B")
YEAR  = NOW.strftime("%Y")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM = f"""You are a senior market intelligence analyst for Osmo, a premium science-backed
electrolyte brand in India. Your job is to produce sharp, actionable intelligence briefs.
Always return ONLY valid JSON — no markdown fences, no preamble, no trailing text.
Today is {TODAY} ({DOW}). Current month: {MONTH} {YEAR}.
India context: Always factor in seasonal triggers, heatwave data, cricket/IPL calendar,
festival calendar, and health advisories. Osmo's positioning: high science credibility,
premium price, D2C, targeting urban professionals and serious athletes."""


def fetch(prompt: str, schema_hint: str = "", max_tokens: int = 1500, use_search: bool = False) -> list:
    """Call Claude and return parsed JSON list.

    use_search=True turns on Anthropic's live web_search tool so the model
    pulls REAL, current results instead of writing plausible content from memory.
    Use it for anything labelled 'live' or 'today's' (India moments, global
    trends, competitor moves, radar). Adds ~1-2 cents per call.
    """
    full_prompt = f"{prompt}\n\nReturn a JSON array. {schema_hint}"
    kwargs = dict(
        model=MODEL,
        max_tokens=max_tokens,
        system=SYSTEM,
        messages=[{"role": "user", "content": full_prompt}],
    )
    if use_search:
        # max_uses=1: each web result is fed back as INPUT tokens, and this
        # org's limit is only 30k input tokens/min. One search per section
        # keeps a single call safely under the limit while still grounding
        # the content in a real source. (Was 5 — that blew the limit.)
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 1}]
    # Retry with backoff. Web search spikes input tokens and can trip the
    # per-minute rate limit (429). When that happens, wait out the 1-minute
    # window and retry instead of crashing the whole build.
    msg = None
    for attempt in range(5):
        try:
            msg = client.messages.create(**kwargs)
            break
        except anthropic.RateLimitError:
            wait = 65
            print(f"  Rate limited (429) — waiting {wait}s, retry {attempt+1}/5...", file=sys.stderr)
            time.sleep(wait)
    if msg is None:
        print("  Gave up after repeated rate limits — section left empty.", file=sys.stderr)
        return []
    # Pace searched calls so consecutive ones don't stack input tokens within
    # the same minute window (reduces how often we hit the 429 above).
    if use_search:
        time.sleep(30)
    # When web_search runs, msg.content holds several blocks (tool calls,
    # search results, then the final answer). Grab the LAST text block —
    # that's the model's final JSON answer. (content[0] would be a tool call.)
    text_blocks = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    raw = (text_blocks[-1] if text_blocks else "").strip()
    # Strip non-ASCII and markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()
    raw = re.sub(r'[\x00-\x1f\x7f]', '', raw)
    # If the model wrapped the JSON in prose, pull out the array/object.
    if raw and raw[0] not in "[{":
        m = re.search(r'(\[.*\]|\{.*\})', raw, re.DOTALL)
        if m:
            raw = m.group(1)
    try:
        parsed = json.loads(raw)
    except Exception as e:
        print(f"JSON parse error: {e}\nRaw: {raw[:300]}", file=sys.stderr)
        return []
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("items", "data", "results", "triggers", "scores", "moves"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        return [v for v in parsed.values() if isinstance(v, dict)]
    return []


def esc(s) -> str:
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def days_until(date_str: str) -> int:
    """date_str: 'YYYY-MM-DD'."""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (target - TODAY_DATE).days
    except Exception:
        return 0


def days_ago(date_str: str) -> int:
    try:
        past = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (TODAY_DATE - past).days
    except Exception:
        return 0


def format_event_date(date_str: str) -> str:
    """'2026-07-24' → 'JUL 24'. Returns 'TBD' if invalid."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%b %d").upper()
    except Exception:
        return "TBD"


# ════════════════════════════════════════════════════════════════════════════
# CURATED DATA — edit these lists when adding new content, then push.
# Bot regenerates the page daily; these values persist.
# ════════════════════════════════════════════════════════════════════════════

# COMPETITORS_LANDSCAPE is now AI-generated daily (see fetch below)

# date format: 'YYYY-MM-DD' OR None for TBD
EVENTS_DATA = [
    {"name":"HYROX Delhi", "sport_type":"hybrid", "sport_label":"HYROX", "color":"#5BA3D4",
     "date":"2026-07-24", "tentative":False, "venue":"TBA · per HYROX India calendar · Delhi",
     "organiser":"HYROX India", "athletes":"Open registration · 2,500+ entries projected",
     "hyd_score":10, "hyd_color":"var(--accent-2)",
     "hover":"8 functional stations + 8 km of running. 90-minute average finish. Delhi heat in July routinely tips into 1.5–1.8 L/hour sweat rates.",
     "hydration":"8 functional stations + 8 km of running. 90-minute average finish. Delhi heat in July routinely tips into 1.5–1.8 L/hour sweat rates.",
     "activation":"Hydration partner status, on-course pods every 2 km, finisher-line single-serve drops, and post-event Reels with top-10 finishers.",
     "verify":"https://india.hyrox.co.in/", "tags":["Verified · Tier-1 hybrid event","Hybrid"]},
    {"name":"HYROX Mumbai", "sport_type":"hybrid", "sport_label":"HYROX", "color":"#5BA3D4",
     "date":"2026-09-18", "tentative":False, "venue":"TBA · per HYROX India calendar · Mumbai",
     "organiser":"HYROX India", "athletes":"Open registration · 3,000+ entries projected",
     "hyd_score":10, "hyd_color":"var(--accent-2)",
     "hover":"Mumbai humidity 78%+ at September peak. Fluid-loss is hidden — athletes under-drink and crash at station 5 onward. Highest-LTV ICP overlap of any event.",
     "hydration":"Mumbai humidity 78%+ at September peak. Fluid-loss is hidden — athletes under-drink and crash at station 5 onward. Highest-LTV ICP overlap of any event.",
     "activation":"Hydration partner status + co-branded finisher pack + content rights on top finishers + box-owner sampling pre-event.",
     "verify":"https://india.hyrox.co.in/", "tags":["Verified · highest-priority moment","Hybrid"]},
    {"name":"Matrix Fight Night 19", "sport_type":"combat", "sport_label":"MMA", "color":"#9CA3AF",
     "date":None, "tentative":True, "date_note":"Date pending · MFN 18 was 02 May 2026",
     "venue":"Shaheed Vijay Singh Pathik Complex (last venue) · Greater Noida",
     "organiser":"Matrix Fight Night", "athletes":"TBA · MFN 19 typically 8–10 weeks after MFN 18",
     "hyd_score":9, "hyd_color":"var(--accent-2)",
     "hover":"5-fight cards with same-day weigh-ins. Athletes lose 4–7% bodyweight pre-fight — the 24-hour rehydration window is where Osmo wins or loses.",
     "hydration":"5-fight cards with same-day weigh-ins. Athletes lose 4–7% bodyweight pre-fight — the 24-hour rehydration window is where Osmo wins or loses.",
     "activation":"Locker-room pre-mix sampling + Anshul Jubli–led content series on weight-cut science.",
     "verify":"https://www.mfnofficial.com/events/", "tags":["Tentative · check source","Combat"]},
    {"name":"ONE Championship India 2026", "sport_type":"combat", "sport_label":"MMA", "color":"#9CA3AF",
     "date":None, "tentative":True, "date_note":"Date pending · ONE India edition unconfirmed",
     "venue":"TBA · Mumbai (likely)",
     "organiser":"ONE Championship", "athletes":"TBA · ONE has 72 events globally in 2026",
     "hyd_score":9, "hyd_color":"var(--accent-2)",
     "hover":"First ONE India event would deliver massive earned-media tail and tier-1 athlete weigh-ins.",
     "hydration":"First ONE India event would deliver massive earned-media tail and tier-1 athlete weigh-ins.",
     "activation":"Co-branded weigh-in hydration kit + Ritu Phogat post-fight recovery reel.",
     "verify":"https://www.onefc.com/?country=in", "tags":["Tentative · monitor for confirmation","Combat"]},
    {"name":"9th Elite Men/Women National Boxing Championships", "sport_type":"combat", "sport_label":"Boxing", "color":"#C75B5B",
     "date":None, "tentative":True, "date_note":"Per BFI 2026 calendar",
     "venue":"TBA · TBA",
     "organiser":"Boxing Federation of India", "athletes":"Nikhat Zareen · Lovlina Borgohain · Amit Panghal · Pooja Rani",
     "hyd_score":8, "hyd_color":"var(--accent-2)",
     "hover":"7-day tournament, 2 fights/day for finalists. Inter-bout recovery hydration decides medals — sodium-loss is the bottleneck.",
     "hydration":"7-day tournament, 2 fights/day for finalists. Inter-bout recovery hydration decides medals — sodium-loss is the bottleneck.",
     "activation":"Federation-tier sponsorship + Nikhat Zareen long-form interview on hydration in weight categories.",
     "verify":"https://boxingfederation.in/", "tags":["Tentative · check BFI calendar","Combat"]},
    {"name":"CrossFit India Throwdown", "sport_type":"hybrid", "sport_label":"CrossFit", "color":"#4A8FB8",
     "date":None, "tentative":True, "date_note":"Date pending",
     "venue":"TBA · Pune (likely)",
     "organiser":"CrossFit India", "athletes":"Box-level qualifiers + Asia Regionals slot",
     "hyd_score":9, "hyd_color":"var(--accent-2)",
     "hover":"3-day event, 6 workouts. Athletes need to recover within 2 hours between WODs — electrolytes are non-negotiable.",
     "hydration":"3-day event, 6 workouts. Athletes need to recover within 2 hours between WODs — electrolytes are non-negotiable.",
     "activation":"Per-station hydration pods + box-owner sampling kit pre-event in 60 boxes.",
     "verify":"https://games.crossfit.com/", "tags":["Tentative · box-owner play","Hybrid"]},
    {"name":"Spartan Race India", "sport_type":"hybrid", "sport_label":"Spartan", "color":"#6BB4A1",
     "date":None, "tentative":True, "date_note":"Date pending · 2026 calendar live",
     "venue":"Della Adventure Park · Lonavala (likely)",
     "organiser":"Spartan Race India", "athletes":"Open registration · 2,400+ entries last year",
     "hyd_score":8, "hyd_color":"var(--accent-2)",
     "hover":"Monsoon trail + 30+ obstacles. Hidden sweat under cool air = under-hydration, performance crash at obstacle 18.",
     "hydration":"Monsoon trail + 30+ obstacles. Hidden sweat under cool air = under-hydration, performance crash at obstacle 18.",
     "activation":"On-course hydration belt + finisher pack co-branding.",
     "verify":"https://in.spartan.com/en/race/find-race", "tags":["Tentative · check Spartan India","Hybrid"]},
    {"name":"WAKO Kickboxing Nationals", "sport_type":"combat", "sport_label":"Kickboxing", "color":"#B8704A",
     "date":None, "tentative":True, "date_note":"Date pending",
     "venue":"TBA · TBA",
     "organiser":"WAKO India", "athletes":"320+ athletes across 9 weight classes (typical)",
     "hyd_score":7, "hyd_color":"var(--accent)",
     "hover":"5-day tournament. Athletes fight up to 4 bouts. Biggest under-served combat audience in the country — open-tier sponsor cost is low.",
     "hydration":"5-day tournament. Athletes fight up to 4 bouts. Biggest under-served combat audience in the country — open-tier sponsor cost is low.",
     "activation":"Federation-tier sponsor + content series on lesser-known combat athletes.",
     "verify":"https://www.wakoindia.in/", "tags":["Tentative · under-served audience","Combat"]},
]

# Threat colors for entrants
ENTRANT_THREAT = {
    "disruptor":  ("var(--red)",      "rgba(199,91,91,.16)",     "var(--red)",      "rgba(199,91,91,.4)"),
    "high-alert": ("var(--accent-3)", "rgba(212,165,116,.16)",   "var(--accent-3)", "rgba(212,165,116,.4)"),
    "watch":      ("var(--accent-2)", "rgba(107,142,123,.14)",   "var(--accent-2)", "rgba(107,142,123,.4)"),
    "monitor":    ("var(--accent)",   "rgba(200,169,126,.14)",   "var(--accent)",   "rgba(200,169,126,.4)"),
}

ENTRANTS_DATA = [
    {"brand":"hydRo365", "parent":"by Founded by Rohit Sharma · hydRo365 Daily Hydration Powder · Powder · Stick",
     "date":"2026-04-30", "threat":"disruptor", "verified":"2026-05-29",
     "mrp":"Per official D2C site", "pser":"TBA / serving",
     "summary":"Rohit Sharma's birthday launch positions hydRo365 as a daily-hydration lifestyle brand — explicitly NOT just for athletes. Celebrity-led, monk-fruit clean-label, and the 365 messaging hits Osmo's everyday-premium narrative dead-centre.",
     "claims":"6 essential electrolytes · Vitamin C · Zinc · B-vitamins · L-theanine · Monk-fruit sweetened · Clean-label",
     "distribution":"D2C (hydro365.com) · Marketplaces (rolling)", "target":"Premium · Wellness",
     "vs_osmo":"Same clean-label playbook with celebrity firepower Osmo can't match on cost. Osmo wins on science depth, athlete proof, and combat/hybrid sports positioning.",
     "verify":"https://www.hydro365.com/"},
    {"brand":"Liquid I.V. India", "parent":"by HUL · Unilever · Hydration Multiplier · Powder · Stick",
     "date":"2025-02-24", "threat":"disruptor", "verified":"2026-05-29",
     "mrp":"₹1,496 / 16 sticks", "pser":"₹94 / serving",
     "summary":"HUL launched Liquid I.V. in India (debut Feb 2025, full rollout Apr 2025) in 3 flavours (Acai Berry · Brazilian Orange · Lemon Lime). Unilever distribution muscle + global brand authority + quick-commerce play makes this one of the biggest competitive events in the category.",
     "claims":"3× more electrolytes · No artificial sweeteners · No caffeine · All-natural flavours · Gluten-free",
     "distribution":"Amazon · Blinkit · liquid-iv.co.in", "target":"Premium · Wellness",
     "vs_osmo":"Unbeatable distribution and trade marketing budget. Osmo wins on India-specific positioning, athlete tie-ups, and category education depth (Liquid I.V. plays on convenience, not science).",
     "verify":"https://www.liquidivindia.com/"},
    {"brand":"Protyze HYDRA-X", "parent":"by Protyze · HYDRA-X Clear Whey Protein + Electrolytes · Powder · Stick",
     "date":"2026-03-12", "threat":"high-alert",
     "mrp":"Per pack · 12 sachets", "pser":"Mid-premium / serving",
     "summary":"Protyze created an 'electrolyte + protein + creatine' all-in-one performance category. Targets gym-goers and athletes who currently take 3 separate products — collapses 30% of the post-workout occasion.",
     "claims":"Whey isolate + creatine + glutamine + EAAs/BCAAs + 5 electrolytes + Vitamin C · Zero added sugar · Clear-formula sachets",
     "distribution":"D2C (protyze.com) · Amazon", "target":"Premium · Sports",
     "vs_osmo":"Different occasion (post-workout protein) but eats into Osmo's intra/post-workout shelf. Osmo wins on pure-hydration purity (no protein for hot-day/IPL/heatwave use cases).",
     "verify":"https://www.protyze.com/products/hydra-x-clear-whey-protein-lemon-lime-pack-of-12-sachets"},
    {"brand":"MuscleBlaze Sports Hydr8 PRO", "parent":"by HealthKart · Sports Hydr8 PRO · Powder · Tub",
     "date":"2026-02-24", "threat":"high-alert",
     "mrp":"₹549 / 300 g", "pser":"~₹13 / serving",
     "summary":"MuscleBlaze leveraging gym-channel distribution and HealthKart trust. Aggressive price-per-serving and the 'PRO' positioning competes directly for serious gym-goers.",
     "claims":"950 mg electrolytes · B1 + B6 + Vitamin C + Zinc · Hydro Infusion Technology · Zesty Orange",
     "distribution":"MuscleBlaze D2C · HealthKart stores · Amazon", "target":"Mass · Gym",
     "vs_osmo":"Wider gym retail and lower price. Lower science credibility and no clean-label story. Osmo wins on athlete authority.",
     "verify":"https://www.muscleblaze.com/sv/muscleblaze-sports-hydr8-pro/SP-107210"},
    {"brand":"Plix Tender Coconut Hydration", "parent":"by Plix Life · Tender Coconut Hydration Premix · Powder · Stick",
     "date":"2025-11-01", "threat":"watch",
     "mrp":"Per pack · 15 sachets", "pser":"Mass-mid / serving",
     "summary":"Plix piggybacking on coconut-water familiarity. Wellness-led narrative, not athletic. Strong with women 25–40.",
     "claims":"Coconut-water base · Potassium + Sodium + Magnesium + Chloride · Plant-based · Daily-hydration positioning",
     "distribution":"Tata 1mg · Amazon · D2C", "target":"Mass · Wellness",
     "vs_osmo":"Different ICP entirely. Wellness shelf, not athletic. Limited direct overlap.",
     "verify":"https://www.1mg.com/otc/plix-tender-coconut-water-daily-hydration-premix-10gm-each-otc869185"},
    {"brand":"Lucofast", "parent":"by Lucofast Foods & Beverages · Hydration RTD · RTD · 300 ml",
     "date":"2025-08-15", "threat":"monitor",
     "mrp":"₹49 / bottle", "pser":"₹49 / serving",
     "summary":"Pan-India RTD undercutting Powerade and Gatorade on price. Marketed as the 'modern Indian electrolyte' — caffeine-free, fruit-forward, non-carbonated.",
     "claims":"5 electrolytes · B-vitamins · Zinc · Vitamin C · Caffeine-free · Non-carbonated · 3 flavours",
     "distribution":"Amazon · Flipkart · D2C", "target":"Mass · Everyday",
     "vs_osmo":"Different ICP (everyday mass) and different format (RTD). Validates category at price-tier Osmo doesn't compete in.",
     "verify":"https://lucofast.com/"},
    {"brand":"Reliance Spinner", "parent":"by Reliance Consumer Products · Spinner Sports Drink · RTD · 150 ml",
     "date":"2025-02-18", "threat":"monitor", "verified":"2026-05-29",
     "mrp":"₹10 / bottle", "pser":"₹10 / serving",
     "summary":"₹10 RTD with Muttiah Muralitharan as co-creator. 5 IPL franchises (LSG, SRH, PBKS, GT, MI) tied in. Mass-priced sweat-replacement positioning.",
     "claims":"Electrolytes for sweat replacement · Lemon / Orange / Nitro Blue · IPL partnership with 5 teams",
     "distribution":"Reliance retail · Kirana · Quick-commerce", "target":"Mass · Everyday",
     "vs_osmo":"Validates category at scale + drives top-of-funnel awareness. Does not compete with Osmo's premium ICP.",
     "verify":"https://www.business-standard.com/companies/news/reliance-launches-spinner-sports-drink-with-muttiah-muralitharan-125021001021_1.html"},
]

PRICING_DATA = [
    {"brand":"Osmo","sku":"Electrolyte Hydration Blend — Valencia Orange","pack":"270g · 45 servings","mrp":599,"price":449,"servings":45,
     "link":"https://wellversed.in/products/osmo-electrolyte-hydration-blend-advanced-salts-taurine-vitamins-orange-flavour-270g-45-servings",
     "source":"wellversed.in","is_osmo":True},
    {"brand":"Fast&Up","sku":"Reload Effervescent — Aam Panna","pack":"Tube · 20 tablets","mrp":265,"price":246,"servings":20,
     "link":"https://in.fastandup.com/products/reload-instant-electrolytes-for-hydration-and-energy-aampanna",
     "source":"fastandup.com","is_osmo":False},
    {"brand":"Supply6","sku":"Salts Electrolyte Mix — Lime","pack":"Jar · 18 sachets (4g each)","mrp":535,"price":456,"servings":18,
     "link":"https://www.amazon.in/Electrolyte-Potassium-Magnesium-Friendly-Preservatives/dp/B0F6MTSHL3",
     "source":"amazon.in","is_osmo":False},
    {"brand":"Liquid I.V.","sku":"Hydration Multiplier — Variety Pack","pack":"16 sticks (16g each)","mrp":1496,"price":1496,"servings":16,
     "link":"https://www.liquidivindia.com/product/liquid-i-v-india-liquid-i-v-hydration-multiplier-electrolyte-drink-mix-powder-packets-16-sticks-variety-pack/",
     "source":"liquidivindia.com","is_osmo":False},
    {"brand":"MuscleBlaze","sku":"Sports Hydr8 PRO — Lemon Lime","pack":"300g · ~30 servings","mrp":549,"price":389,"servings":30,
     "link":"https://www.muscleblaze.com/sv/muscleblaze-sports-hydr8-pro/SP-107210",
     "source":"muscleblaze.com","is_osmo":False},
    {"brand":"Enerzal","sku":"Energy & Electrolyte Powder — Orange","pack":"1 kg · ~40 servings","mrp":450,"price":450,"servings":40,
     "link":"https://www.bigbasket.com/pd/40330979/enerzal-enerzal-enerzal-energy-electrolyte-drink-with-5-vital-electrolytes-for-stomach-care-flavour-powder-orange-1-kg/",
     "source":"bigbasket.com","is_osmo":False},
]

BRIEF_PROMPTS = {
    'heatwave_content': 'Create a full marketing content brief for Osmo around the current India heatwave — empathy-first, science-backed, 3 content pieces across Instagram, X, and email.',
    'heatwave_carousel': 'Write copy for a 3-slide Instagram carousel: heatwave + hydration for Osmo. Empathy-first, educational.',
    'ors_upgrade': 'Write a brand positioning brief for Osmo around the ORS moment — government pushing ORS for outdoor workers. How does Osmo position as the science upgrade?',
    'ipl_reel': 'Write a 30-second Instagram Reel script for Osmo targeting IPL fans watching outdoors in summer heat. Fun, relatable, ends with product hook.',
    'cognitive_series': 'Build a 6-post LinkedIn content series for Osmo on cognitive dehydration — for urban professionals in Bangalore, Mumbai, Delhi.',
    'pr_pitch': 'Write a PR pitch email from Osmo to Mint Lounge health editor. Angle: ORS is not enough for outdoor workers — Osmo is the science-backed upgrade.',
    'weekly_brief': f'Generate a complete marketing intelligence brief for the Osmo team for the week of {TODAY}. Include top 3 India moments, 1 global trend, 1 competitor alert, 4 prioritized actions.',
    'competitor_alert': 'Analyze the competitive landscape for Osmo in India right now. Fast&Up popsicles, Reliance Spinner ₹10 RTD, hydRo365 (Rohit Sharma), Liquid I.V. India (HUL) — what should Osmo do?',
    'events_brief': 'Build a 90-day combat & hybrid sport activation calendar for Osmo. Include sampling, athlete tie-ups, and sponsorship for top events.',
    'entrants_brief': 'Generate a competitive response plan for Osmo against the latest electrolyte launches in India. Include hydRo365, Liquid I.V. India, Protyze HYDRA-X, MuscleBlaze Sports Hydr8 PRO.',
    'athlete_tieup': 'Draft an athlete-partnership pitch for Osmo to a tier-1 Indian combat athlete. Include compensation framework, content deliverables, and exclusivity terms.',
    'radar_verify': 'Help me verify this potential new electrolyte launch in India. Search for: official brand site, product page, claims, distribution, and assess threat to Osmo.',
}


# ════════════════════════════════════════════════════════════════════════════
# DAILY AI FETCH — 7 calls (6 original + 1 NEW Radar)
# ════════════════════════════════════════════════════════════════════════════

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
  tag (short descriptor like "Time-sensitive · 7-day window")
Use web search to ground every insight in a REAL, recent event, advisory, or news item — do not invent incidents.""",
    "Fields: title, urgency, what, why, angle, action, tag",
    use_search=True,
)

print("Fetching global trends...")
global_items = fetch(
    f"""Generate 3 global electrolyte category trend insights relevant to an Indian
premium brand in {MONTH} {YEAR}.
Consider: market size ($43B global, $81M India growing 13.9% CAGR), clean-label shift,
zero-sugar formats, functional stacking, science credibility trend, competitor moves globally.
Each object: title, urgency, what, angle, tag
Use web search to ground every trend in a REAL, recent source — do not invent developments.""",
    "Fields: title, urgency, what, angle, tag",
    use_search=True,
)

print("Fetching competitor intelligence (focused on new launches and brand moves)...")
competitor_items = fetch(
    f"""Generate 3 competitor intelligence insights for Osmo in India as of {TODAY}.
EMPHASIS: Focus on NEW launches, new SKUs, new initiatives, or brand moves made by
competitors in the last 14 days. Known context: Fast&Up popsicles with NOTO (Apr),
hydRo365 launched by Rohit Sharma (Apr 30), Liquid I.V. India by HUL, Reliance Spinner
(₹10 RTD), MuscleBlaze Sports Hydr8 PRO, Protyze HYDRA-X all-in-one.
Each object: title, urgency, what (what the competitor did NEW), gap (white space Osmo can claim), tag
Use web search to confirm each move actually happened and is recent — do not invent launches or ad-spend figures.""",
    "Fields: title, urgency, what, gap, tag",
    use_search=True,
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
dot_color ("red"|"gold"|"green"|"amber")""",
    "Fields: month_label, title, description, dot_color. Exactly 6 items."
)

print("Fetching RADAR — new launches & brand initiatives flagged this week...")
radar_items = fetch(
    f"""You are scanning the Indian electrolyte and hydration market for NEW signals as of {TODAY}.
List 3-4 RECENT signals (last 7-14 days) that the Osmo team should investigate and possibly add
to their verified competitive intelligence database. Focus on:
  - New product launches or SKU expansions by any electrolyte/hydration brand in India
  - New brand initiatives, celebrity partnerships, distribution moves, ad campaigns
  - Cross-category entrants (protein, ORS, sports drinks) moving into electrolytes
  - Quick-commerce or D2C distribution shifts
For each signal, return: brand (string), what (1-2 sentence summary of what they did),
source_hint (where to find more — e.g. "brand D2C site" or "Amazon listing" or "Mint Lounge article"),
threat ("disruptor"|"high-alert"|"watch"|"monitor"),
days_ago_estimate (integer, your best estimate of how many days ago this happened, 0-14)
Use web search to find signals that are REAL and genuinely recent. In source_hint, name the actual source you found.""",
    "Fields: brand, what, source_hint, threat, days_ago_estimate. 3-4 items.",
    use_search=True,
)

print("Fetching competitor landscape (daily refreshed)...")
landscape_items = fetch(
    f"""Generate 6 competitor landscape cards for Osmo's India electrolyte market as of {TODAY}.
For each brand, give their CURRENT positioning and most recent move in {MONTH} {YEAR} — not historical.
Brands: Fast&Up, Liquid I.V. (HUL), Reliance Spinner, MuscleBlaze, hydRo365, Enerzal/ORS.
For each: name (string), desc (2 sharp sentences on what they are doing RIGHT NOW and why it matters to Osmo),
threat ("high"|"watch"|"pressure"|"monitor"|"disruptor"|"opportunity")
Use web search to confirm each brand's current activity. Do NOT state launch dates, ad-spend figures, or moves you cannot find a real source for.""",
    "Fields: name, desc, threat. Exactly 6 items.",
    max_tokens=900,
    use_search=True,
)
# Fallback to static if fetch fails (verified facts only — no unsourced figures)
if not landscape_items or len(landscape_items) < 3:
    landscape_items = [
        {"name":"Fast&Up", "desc":"Effervescent tabs, pan-India. IPL playoff push with NOTO popsicle collab and Aam Panna flavour expansion — targeting Indian palate at mass price.", "threat":"high"},
        {"name":"Liquid I.V. (HUL)", "desc":"HUL-backed US import (debut Feb 2025) in 3 flavours via Amazon/Blinkit. Unilever distribution + global brand authority make it a top-tier premium rival.", "threat":"disruptor"},
        {"name":"Reliance Spinner", "desc":"₹10 RTD co-created with Muttiah Muralitharan, tied to 5 IPL teams. Validates the category at the bottom while Osmo holds premium.", "threat":"pressure"},
        {"name":"MuscleBlaze", "desc":"India's largest sports nutrition brand scaling electrolytes (Sports Hydr8 PRO) via the HealthKart gym channel. Distribution moat is the threat.", "threat":"monitor"},
        {"name":"hydRo365", "desc":"Rohit Sharma's clean-label daily-hydration brand (launched Apr 30, 2026). Celebrity firepower aimed squarely at Osmo's everyday-premium narrative.", "threat":"disruptor"},
        {"name":"Enerzal / ORS", "desc":"Govt pushing ORS hard for heatwave season — creates a clear upgrade narrative Osmo can own with science messaging.", "threat":"opportunity"},
    ]

print("All data fetched. Building HTML...")

# ════════════════════════════════════════════════════════════════════════════
# PAGE TEMPLATE — OSMO_RADAR dashboard (plain string; tokens replaced below)
# ════════════════════════════════════════════════════════════════════════════
TEMPLATE = r'''<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OSMO_RADAR — Electrolyte Market Briefing · __TODAY__</title>
<script>(function(){try{var t=localStorage.getItem('osmo-theme')||'light';document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#F4F5F7; --surface:#FFFFFF; --surface-2:#FFFFFF; --surface-3:#EEF0F3; --border:#E4E7EC; --border-2:#EEF0F3;
  --text:#0B1020; --text-2:#3A4256; --text-3:#7C8398;
  --primary:#1D4ED8; --primary-dim:#3B82F6; --primary-ink:#FFFFFF; --accent:#FF5A1F; --accent-2:#16A34A;
  --crit:#E11D48; --crit-bg:#FFE4EA; --high:#C2410C; --high-bg:#FFEDE5; --med:#1D4ED8; --med-bg:#EAF0FF; --low:#5B6472; --low-bg:#EEF0F3;
  --watch:#B45309; --watch-bg:#FFF4E0; --opp:#0F7A43; --opp-bg:#E6F6EC; --mono:#5B6472; --mono-bg:#EEF0F3;
  --card-shadow:0 1px 2px rgba(11,16,32,.04),0 10px 30px -14px rgba(11,16,32,.13);
  --obsidian:#0B1020; --demo-tx:#AFC2FF; --navbg:rgba(255,255,255,.88);
  --d:'Archivo Narrow',sans-serif; --b:'Inter',sans-serif; --m:'JetBrains Mono',monospace; --rad:16px;
}
html[data-theme="dark"]{
  --bg:#0E1014; --surface:#171A20; --surface-2:#1B1F26; --surface-3:#232831; --border:#2A2F39; --border-2:#20242C;
  --text:#E8EAEE; --text-2:#A6ADB8; --text-3:#717A86;
  --primary:#5B8DEF; --primary-dim:#3B82F6; --primary-ink:#08101F; --accent:#FF7A45; --accent-2:#34D17F;
  --crit:#FF6B7A; --crit-bg:rgba(225,29,72,.18); --high:#FF8A5B; --high-bg:rgba(255,90,31,.16); --med:#7FA8FF; --med-bg:rgba(29,78,216,.22); --low:#9AA2AE; --low-bg:rgba(255,255,255,.06);
  --watch:#FBBF24; --watch-bg:rgba(245,158,11,.16); --opp:#4ADE80; --opp-bg:rgba(34,197,94,.16); --mono:#9AA2AE; --mono-bg:rgba(255,255,255,.06);
  --card-shadow:0 0 0 1px rgba(255,255,255,.04); --obsidian:#05070C; --demo-tx:#8AA6FF; --navbg:rgba(14,16,20,.85);
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--b);font-size:14px;line-height:1.55;-webkit-font-smoothing:antialiased;
  background-image:radial-gradient(900px 480px at 88% -8%,rgba(29,78,216,.06),transparent 62%),radial-gradient(700px 420px at -4% 24%,rgba(255,90,31,.05),transparent 60%);background-attachment:fixed;transition:background .3s,color .3s}
.demo{background:var(--obsidian);color:var(--demo-tx);text-align:center;padding:7px;font-family:var(--m);font-size:11px;letter-spacing:.05em}
.demo b{color:#fff}
.ticker{background:var(--surface);border-bottom:1px solid var(--border);height:34px;display:flex;align-items:center;overflow:hidden}
.ticker .lbl{background:var(--primary);color:#fff;height:100%;display:flex;align-items:center;padding:0 14px;font-family:var(--m);font-weight:700;font-size:10px;letter-spacing:.1em;flex-shrink:0}
.ticker .track{display:flex;white-space:nowrap;animation:tk 42s linear infinite}.ticker .track:hover{animation-play-state:paused}
.ticker .it{padding:0 20px;font-family:var(--m);font-size:11px;display:flex;align-items:center;gap:7px;color:var(--text-2)}
.ticker .it b{color:var(--text)}.ticker .hot{color:var(--accent)}.ticker .up{color:var(--accent-2)}
@keyframes tk{to{transform:translateX(-50%)}}
nav{position:sticky;top:0;z-index:60;display:flex;align-items:center;justify-content:space-between;padding:13px 28px;background:var(--navbg);backdrop-filter:saturate(140%) blur(12px);border-bottom:1px solid var(--border);gap:14px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:11px}
.brand .rad{width:30px;height:30px;border-radius:8px;background:var(--primary);color:var(--primary-ink);display:flex;align-items:center;justify-content:center;font-size:16px}
.brand .nm{font-family:var(--m);font-weight:700;font-size:15px;letter-spacing:.04em}.brand .nm b{color:var(--primary)}
.brand .live{margin-left:4px;color:var(--primary)}
.tabs{display:flex;gap:3px;flex:1;justify-content:center}
.tab{font-family:var(--m);font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);background:none;border:none;padding:9px 14px;border-radius:8px;cursor:pointer;transition:.18s}
.tab:hover{color:var(--text-2);background:var(--surface-3)}.tab.on{color:var(--primary-ink);background:var(--primary)}
.tab .n{font-size:9px;opacity:.7;margin-left:3px}
.nav-r{display:flex;align-items:center;gap:8px}
.pill{font-family:var(--m);font-size:10px;padding:6px 10px;border-radius:99px;letter-spacing:.05em;border:1px solid var(--border)}
.pill.live{color:var(--primary);display:flex;align-items:center;gap:6px;border-color:var(--border)}
.pill.live .d{width:6px;height:6px;border-radius:50%;background:var(--primary);animation:pulse 1.5s infinite}
.pill.date{color:var(--text-3)}
.tgl{font-family:var(--m);font-size:13px;background:var(--surface-3);border:1px solid var(--border);color:var(--text-2);width:34px;height:30px;border-radius:8px;cursor:pointer;transition:.18s}
.tgl:hover{color:var(--primary);border-color:var(--primary)}
@keyframes pulse{50%{opacity:.3}}
.wrap{max-width:1280px;margin:0 auto;padding:26px 28px 80px}
.panel{display:none;animation:fade .35s ease}.panel.on{display:block}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.sechead{display:flex;align-items:baseline;justify-content:space-between;margin:0 0 16px;flex-wrap:wrap;gap:8px}
.sechead .ey{font-family:var(--m);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--primary);display:flex;align-items:center;gap:7px}
.sechead .ey .d{width:6px;height:6px;border-radius:50%;background:var(--primary)}
.sechead h2{font-family:var(--d);font-weight:800;font-size:34px;letter-spacing:-.02em;line-height:1}
.sechead .rt{font-family:var(--m);font-size:10px;letter-spacing:.07em;color:var(--text-3);text-transform:uppercase}
.subhead{font-family:var(--d);font-weight:700;font-size:19px;margin:28px 0 13px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.subhead .tagn{font-family:var(--m);font-size:9px;font-weight:700;color:var(--text-3);background:var(--surface-3);padding:4px 9px;border-radius:6px;letter-spacing:.05em}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--rad);padding:22px;box-shadow:var(--card-shadow)}
.grid{display:grid;gap:16px}
.alert{display:flex;align-items:center;gap:12px;padding:13px 18px;border:1px solid var(--crit);background:var(--crit-bg);border-radius:12px;margin-bottom:18px;cursor:pointer}
.alert .ic{color:var(--crit);font-size:15px}.alert .tx{font-family:var(--m);font-size:12px;letter-spacing:.04em;color:var(--crit);flex:1}.alert .ar{color:var(--crit)}
.kpis{grid-template-columns:repeat(4,1fr);margin-bottom:18px}
.kpi{padding:18px 20px}
.kpi .lab{font-family:var(--m);font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-3);display:flex;justify-content:space-between}
.kpi .lab .cagr{color:var(--accent-2)}
.kpi .val{font-family:var(--d);font-weight:800;font-size:38px;line-height:1;margin:8px 0 2px}
.kpi.p .val{color:var(--primary)}.kpi.o .val{color:var(--accent)}.kpi.r .val{color:var(--crit)}.kpi.g .val{color:var(--accent-2)}
.kpi .sub{font-family:var(--m);font-size:10px;color:var(--text-3)}
.two{grid-template-columns:2fr 1fr}
.land{grid-template-columns:repeat(3,1fr)}
.btn{font-family:var(--m);font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:12px 18px;border-radius:9px;border:none;cursor:pointer;display:inline-flex;align-items:center;gap:8px;transition:.18s;text-decoration:none}
.btn.primary{background:var(--primary);color:var(--primary-ink)}.btn.primary:hover{filter:brightness(.95)}
.btn.ghost{background:transparent;border:1px solid var(--border);color:var(--text)}.btn.ghost:hover{border-color:var(--text-2)}
.ctrls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:16px}
.search{flex:1;min-width:200px;display:flex;align-items:center;gap:9px;background:var(--surface);border:1.5px solid var(--border);border-radius:10px;padding:10px 13px;transition:.2s;box-shadow:var(--card-shadow)}
.search:focus-within{border-color:var(--primary)}
.search input{flex:1;border:none;outline:none;background:none;font-family:var(--b);font-size:13px;color:var(--text)}
.chip{font-family:var(--m);font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:9px 13px;border-radius:8px;border:1.5px solid var(--border);background:var(--surface);color:var(--text-3);cursor:pointer;transition:.18s}
.chip:hover{color:var(--text-2)}.chip.on{background:var(--primary);color:var(--primary-ink);border-color:var(--primary)}
.sort{font-family:var(--m);font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:9px 12px;border-radius:8px;border:1.5px solid var(--border);background:var(--surface);color:var(--text-2);cursor:pointer;outline:none}
.feed{display:flex;flex-direction:column;gap:11px}
.item{border:1px solid var(--border);border-radius:12px;padding:14px 16px;border-left:4px solid var(--text-3);transition:.18s;background:var(--surface)}
.item:hover{box-shadow:var(--card-shadow)}
.item[data-sev="crit"]{border-left-color:var(--crit)}.item[data-sev="high"]{border-left-color:var(--accent)}.item[data-sev="med"]{border-left-color:var(--primary)}.item[data-sev="low"]{border-left-color:var(--text-3)}
.itop{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:7px}
.badge{font-family:var(--m);font-size:8px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:4px 8px;border-radius:6px}
.badge.crit{background:var(--crit-bg);color:var(--crit)}.badge.high{background:var(--high-bg);color:var(--high)}.badge.med{background:var(--med-bg);color:var(--med)}.badge.low{background:var(--low-bg);color:var(--low)}
.region{font-family:var(--m);font-size:9px;color:var(--text-3)}
.item h4{font-family:var(--d);font-weight:700;font-size:16px;line-height:1.2;margin-bottom:4px}
.item p{font-size:13px;color:var(--text-2)}
.item .ang{font-size:12px;color:var(--text-2);margin-top:6px}.item .ang b{color:var(--primary)}
.copy{margin-top:9px;font-family:var(--m);font-size:9px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--text-3);background:none;border:1px solid var(--border);border-radius:6px;padding:5px 10px;cursor:pointer;transition:.18s}
.copy:hover{color:var(--primary);border-color:var(--primary)}
.empty{display:none;text-align:center;padding:26px;color:var(--text-3);font-family:var(--m);font-size:12px}
.heat{display:flex;flex-direction:column;gap:13px}
.heat-row .hh{display:flex;justify-content:space-between;font-size:12px;margin-bottom:5px}.heat-row .hh .sc{font-family:var(--d);font-weight:800}
.heat-track{height:9px;border-radius:99px;background:var(--surface-3);overflow:hidden}.heat-fill{height:100%;border-radius:99px;transition:width .6s}
.trig-row{display:flex;gap:13px;padding:12px 0;border-bottom:1px solid var(--border-2)}.trig-row:last-child{border:none}
.trig-row .mo{font-family:var(--m);font-size:10px;font-weight:700;color:#fff;border-radius:6px;padding:5px 9px;height:fit-content;letter-spacing:.04em;min-width:44px;text-align:center}
.trig-row .tt{font-family:var(--d);font-weight:700;font-size:15px}.trig-row p{font-size:12px;color:var(--text-2);margin-top:2px}
.land-card{padding:16px 18px}.land-card .lh{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}
.land-card .nm{font-family:var(--d);font-weight:700;font-size:17px}.land-card p{font-size:12px;color:var(--text-2)}
.tg{font-family:var(--m);font-size:8px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:3px 8px;border-radius:99px;white-space:nowrap}
.tg.crit{background:var(--crit-bg);color:var(--crit)}.tg.accent{background:var(--high-bg);color:var(--high)}.tg.watch{background:var(--watch-bg);color:var(--watch)}.tg.mono{background:var(--mono-bg);color:var(--mono)}.tg.opp{background:var(--opp-bg);color:var(--opp)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{font-family:var(--m);font-size:9px;letter-spacing:.07em;text-transform:uppercase;color:var(--text-3);text-align:left;padding:10px 12px;border-bottom:2px solid var(--border);cursor:pointer;user-select:none;white-space:nowrap}
th:hover,th.sorted{color:var(--primary)}th .ar{opacity:.4}th.sorted .ar{opacity:1}
td{padding:12px;border-bottom:1px solid var(--border-2);color:var(--text-2)}tr:hover td{background:var(--surface-3)}
td.brand{font-family:var(--d);font-weight:700;font-size:15px;color:var(--text)}td.brand .sku{display:block;font-family:var(--b);font-weight:400;font-size:11px;color:var(--text-3)}
td.num{font-family:var(--m)}td.per{font-family:var(--d);font-weight:800;font-size:18px}
.leader td{background:var(--med-bg)!important}.leader td.brand,.leader td.per{color:var(--primary)}
.lead-tag{font-family:var(--m);font-size:8px;font-weight:700;background:var(--primary);color:var(--primary-ink);padding:3px 7px;border-radius:5px;margin-left:8px}
.srclink{font-family:var(--m);font-size:10px;color:var(--primary);text-decoration:none}.srclink:hover{text-decoration:underline}
.insight{margin-top:14px;font-family:var(--m);font-size:12px;color:var(--text-2);line-height:1.6;padding:14px;border:1px dashed var(--border);border-radius:10px}.insight b{color:var(--primary)}
.launch{display:flex;flex-direction:column;gap:10px}
.lrow{display:flex;align-items:center;gap:13px;padding:13px 15px;border:1px solid var(--border);border-radius:12px;background:var(--surface)}
.lrow.flagged{border-style:dashed}
.lrow .ld{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.lrow .ld.crit{background:var(--crit)}.lrow .ld.accent{background:var(--accent)}.lrow .ld.watch{background:var(--watch)}.lrow .ld.mono{background:var(--text-3)}.lrow .ld.opp{background:var(--opp)}
.lrow .linfo{min-width:0}.lrow .lname{font-family:var(--d);font-weight:700;font-size:15px}
.lrow .flag{font-family:var(--m);font-size:8px;color:var(--primary);background:var(--med-bg);padding:2px 6px;border-radius:4px;letter-spacing:.04em}
.lrow .lsub{font-family:var(--b);font-size:11px;color:var(--text-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:340px}
.lrow .lsp{flex:1}.lrow .lwhen{font-family:var(--m);font-size:10px;color:var(--text-3);white-space:nowrap}
.vbadge{font-family:var(--m);font-size:8px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:4px 8px;border-radius:6px;background:var(--opp-bg);color:var(--opp);white-space:nowrap}
.vbadge.warn{background:var(--watch-bg);color:var(--watch)}
.evt-hero{padding:0;overflow:hidden}
.evt-hero .ehead{padding:18px 20px;border-bottom:1px solid var(--border-2);display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.evt-hero .when{font-family:var(--m);font-size:10px;letter-spacing:.07em;color:var(--text-3);text-transform:uppercase}
.evt-hero h3{font-family:var(--d);font-weight:800;font-size:28px;line-height:1;margin-top:4px}
.evt-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border-2)}
.evt-stat{background:var(--surface);padding:15px 18px}.evt-stat .l{font-family:var(--m);font-size:9px;letter-spacing:.07em;text-transform:uppercase;color:var(--text-3)}
.evt-stat .v{font-family:var(--d);font-weight:800;font-size:24px;color:var(--primary);margin-top:4px}.evt-stat .v.sm{font-size:16px;color:var(--text)}
.evt-body{padding:18px 20px}.evt-body .q{font-family:var(--d);font-style:italic;font-weight:700;font-size:15px;color:var(--text-2);margin-bottom:14px;line-height:1.4}
.evt-actions{display:flex;gap:10px;flex-wrap:wrap}
.sec-evt{display:flex;align-items:center;gap:14px;padding:14px 16px;margin-bottom:10px}
.sec-evt .score{font-family:var(--d);font-weight:800;font-size:14px;color:var(--primary);background:var(--med-bg);border-radius:8px;padding:8px 11px;flex-shrink:0}
.sec-evt .info{flex:1}.sec-evt .info .nm{font-family:var(--d);font-weight:700;font-size:16px}
.sec-evt .info .meta{font-family:var(--m);font-size:9px;color:var(--text-3);text-transform:uppercase;letter-spacing:.05em}.sec-evt .info p{font-size:12px;color:var(--text-2);margin-top:4px}
.brief{padding:18px 20px;margin-bottom:13px}.brief .top{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:9px}
.brief h3{font-family:var(--d);font-weight:800;font-size:21px;line-height:1.1}
.prio{font-family:var(--m);font-size:9px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:5px 11px;border-radius:99px;white-space:nowrap}
.prio.urgent{background:var(--crit-bg);color:var(--crit)}.prio.med{background:var(--watch-bg);color:var(--watch)}.prio.low{background:var(--surface-3);color:var(--text-3)}
.brief p{color:var(--text-2);font-size:14px;margin-bottom:12px}.brief .metric{font-family:var(--m);font-size:11px;color:var(--text-3);margin-bottom:13px}
.brief-actions{display:flex;gap:10px;flex-wrap:wrap}
.gen-grid{grid-template-columns:repeat(4,1fr);margin-top:8px}
.gen-btn{font-family:var(--m);font-size:10px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;text-align:left;padding:14px;border-radius:11px;border:1px solid var(--border);background:var(--surface);color:var(--text-2);cursor:pointer;transition:.18s;box-shadow:var(--card-shadow)}
.gen-btn:hover{border-color:var(--primary);color:var(--primary);transform:translateY(-2px)}
.quote{padding:18px 22px;border-left:3px solid var(--primary)}.quote p{font-family:var(--d);font-weight:700;font-size:17px;font-style:italic;color:var(--text);line-height:1.35}
.mini{grid-template-columns:1fr 1fr;margin-top:16px}.counter{padding:18px 20px}
.counter .lab{font-family:var(--m);font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-3)}.counter .val{font-family:var(--d);font-weight:800;font-size:36px;line-height:1;margin-top:8px}
.foot{max-width:1280px;margin:30px auto 0;padding:18px 28px;border-top:1px solid var(--border);font-family:var(--m);font-size:10px;color:var(--text-3);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.toast{position:fixed;bottom:26px;left:50%;transform:translateX(-50%) translateY(80px);background:var(--primary);color:var(--primary-ink);font-family:var(--m);font-size:12px;font-weight:700;padding:13px 22px;border-radius:10px;transition:.25s;z-index:200}.toast.show{transform:translateX(-50%) translateY(0)}
@media(max-width:980px){.tabs{order:3;width:100%;justify-content:flex-start;overflow-x:auto}.kpis,.two,.land,.gen-grid,.mini{grid-template-columns:1fr}.wrap{padding:20px 16px 60px}nav{padding:12px 16px}}
</style>
</head>
<body>
<div class="demo">REDESIGN PREVIEW · <b>OSMO_RADAR</b> — light default, dark toggle (top-right ◐). Generated __TODAY__.</div>
<div class="ticker"><div class="lbl">● LIVE</div><div class="track">__TICKER__</div></div>
<nav>
  <div class="brand"><div class="rad">◉</div><span class="nm">OSMO<b>_RADAR</b></span><span class="live">((•))</span></div>
  <div class="tabs" id="tabs">
    <button class="tab on" data-p="radar">Radar</button>
    <button class="tab" data-p="intel">Intel</button>
    <button class="tab" data-p="events">Events<span class="n">__EVENTS_CT__</span></button>
    <button class="tab" data-p="briefs">Briefs</button>
    <button class="tab" data-p="global">Global</button>
  </div>
  <div class="nav-r">
    <button class="tgl" id="tgl" onclick="toggleTheme()" title="Toggle light/dark">◐</button>
    <span class="pill live"><span class="d"></span>LIVE</span><span class="pill date">__TODAY__</span>
  </div>
</nav>
<div class="wrap">

  <section class="panel on" id="p-radar">
    <div class="sechead"><div><div class="ey"><span class="d"></span>Real-time intel</div><h2>Market Radar</h2></div><span class="rt">Web-searched · 07:00 IST</span></div>
    <div class="alert" onclick="go('intel')"><span class="ic">⚠</span><span class="tx">__RADAR_CT__ NEW SIGNALS ON RADAR — unverified, review before acting</span><span class="ar">›</span></div>
    <div class="grid kpis">
      <div class="card kpi p"><div class="lab"><span>India 2026</span><span class="cagr">↗ 13.9%</span></div><div class="val">$81M</div><div class="sub">CAGR · growing fast</div></div>
      <div class="card kpi g"><div class="lab"><span>Global category</span><span class="cagr">↗ 8.4%</span></div><div class="val">$43B</div><div class="sub">zero-sugar +41% share</div></div>
      <div class="card kpi r"><div class="lab">Critical signals</div><div class="val">__CRIT_CT__</div><div class="sub">today</div></div>
      <div class="card kpi o"><div class="lab">Osmo ₹/serving</div><div class="val">₹__OSMO_PER__</div><div class="sub">cheapest premium</div></div>
    </div>
    <div class="ctrls">
      <label class="search"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#7C8398" stroke-width="2.2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg><input id="q" placeholder="Search India moments…" oninput="applyFeed()"></label>
      <div id="radar-chips" style="display:flex;gap:7px;flex-wrap:wrap">
        <button class="chip on" data-sev="all" onclick="chipSel(this,'radar-chips','applyFeed')">All</button>
        <button class="chip" data-sev="crit" onclick="chipSel(this,'radar-chips','applyFeed')">Critical</button>
        <button class="chip" data-sev="high" onclick="chipSel(this,'radar-chips','applyFeed')">High</button>
        <button class="chip" data-sev="med" onclick="chipSel(this,'radar-chips','applyFeed')">Medium</button>
        <button class="chip" data-sev="low" onclick="chipSel(this,'radar-chips','applyFeed')">Low</button>
      </div>
      <select class="sort" id="sort" onchange="applyFeed()"><option value="severity">Sort · Severity</option><option value="az">Sort · A–Z</option></select>
    </div>
    <div class="grid two">
      <div>
        <div class="subhead">Today's India Moments <span class="tagn" id="cnt"></span></div>
        <div class="feed" id="feed">__INDIA_FEED__</div>
        <div class="empty" id="empty">No matches — clear filters.</div>
      </div>
      <div>
        <div class="subhead">Opportunity Heat Map</div><div class="card"><div class="heat">__HEAT__</div></div>
        <div class="subhead">Upcoming Triggers</div><div class="card">__TRIG__</div>
      </div>
    </div>
  </section>

  <section class="panel" id="p-intel">
    <div class="sechead"><div><div class="ey"><span class="d"></span>Competitive landscape</div><h2>Competitor Intelligence</h2></div><span class="rt">Last 90 days</span></div>
    <div class="subhead">India Competitor Landscape</div>
    <div class="grid land">__LAND__</div>
    <div class="subhead">Price Efficiency Benchmarking <span class="tagn">verified __PRICING_VERIFIED__ · re-check monthly</span></div>
    <div class="card"><table id="tbl"><thead><tr>
      <th data-k="brand">Brand / SKU <span class="ar">↕</span></th>
      <th data-k="price" data-n="1">Price <span class="ar">↕</span></th>
      <th data-k="per" data-n="1">Per serve <span class="ar">↕</span></th>
      <th>Source</th>
    </tr></thead><tbody id="tb">__PRICING__</tbody></table>
      <div class="insight"><b>INSIGHT:</b> Osmo is the cheapest premium option per serve at ₹__OSMO_PER__ — undercutting every listed competitor while keeping the science depth they lack. The lead depends on the current sale price holding; re-check monthly.</div>
    </div>
    <div class="subhead">Market Entry Stream <span class="tagn">verified launches + radar-flagged</span></div>
    <div class="ctrls">
      <label class="search"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#7C8398" stroke-width="2.2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg><input id="q2" placeholder="Search launches…" oninput="applyLaunch()"></label>
      <div id="intel-chips" style="display:flex;gap:7px;flex-wrap:wrap">
        <button class="chip on" data-th="all" onclick="chipSel(this,'intel-chips','applyLaunch')">All</button>
        <button class="chip" data-th="disruptor" onclick="chipSel(this,'intel-chips','applyLaunch')">Disruptor</button>
        <button class="chip" data-th="high-alert" onclick="chipSel(this,'intel-chips','applyLaunch')">High-alert</button>
        <button class="chip" data-th="watch" onclick="chipSel(this,'intel-chips','applyLaunch')">Watch</button>
        <button class="chip" data-th="monitor" onclick="chipSel(this,'intel-chips','applyLaunch')">Monitor</button>
      </div>
    </div>
    <div class="launch" id="launch">__LAUNCHES__</div>
    <div class="empty" id="empty2">No matches — clear filters.</div>
    <div class="subhead">AI Competitor Moves <span class="tagn">web-searched · this week</span></div>
    <div class="feed">__COMPAI__</div>
  </section>

  <section class="panel" id="p-events">
    <div class="sechead"><div><div class="ey"><span class="d"></span>Live intelligence</div><h2>Events Tracker</h2></div><span class="rt">__EVENTS_CT__ events · __TODAY__</span></div>
    __EVENTS__
  </section>

  <section class="panel" id="p-briefs">
    <div class="sechead"><div><div class="ey"><span class="d"></span>Live strategic briefing</div><h2>Priority Actions</h2></div><span class="rt">Osmo Team · This Week</span></div>
    __BRIEFS__
    <div class="subhead">Generate Custom Brief <span class="tagn">opens in Claude</span></div>
    <div class="grid gen-grid">
      <button class="gen-btn" onclick="brief('weekly_brief')">↗ Full weekly brief</button>
      <button class="gen-btn" onclick="brief('events_brief')">↗ 90-day events plan</button>
      <button class="gen-btn" onclick="brief('entrants_brief')">↗ Competitor response</button>
      <button class="gen-btn" onclick="brief('heatwave_carousel')">↗ Heatwave social copy</button>
      <button class="gen-btn" onclick="brief('ipl_reel')">↗ IPL reel script</button>
      <button class="gen-btn" onclick="brief('ors_upgrade')">↗ ORS upgrade pitch</button>
      <button class="gen-btn" onclick="brief('cognitive_series')">↗ Cognitive hydration series</button>
      <button class="gen-btn" onclick="brief('athlete_tieup')">↗ Athlete partnership pitch</button>
    </div>
    <div class="grid mini">
      <div class="card counter"><div class="lab">◉ Radar signals</div><div class="val">__RADAR_CT__ <span style="font-size:13px;color:var(--text-3);font-family:var(--m)">FLAGGED</span></div></div>
      <div class="card counter"><div class="lab">✓ Verified launches</div><div class="val">__ENTRANTS_CT__ <span style="font-size:13px;color:var(--text-3);font-family:var(--m)">TRACKED</span></div></div>
    </div>
  </section>

  <section class="panel" id="p-global">
    <div class="sechead"><div><div class="ey"><span class="d"></span>Web-searched live</div><h2>Global Trends</h2></div><span class="rt">__TODAY__</span></div>
    <div class="grid two">
      <div class="feed">__GLOBAL__</div>
      <div class="card quote"><p>Global hydration category at $43B; India $81M growing 13.9% CAGR — zero-sugar formats now ~41% of new launches.</p></div>
    </div>
  </section>

</div>
<div class="foot"><span>Electrolyte Intelligence · Internal use · Auto-refreshed daily 07:00 IST</span><span>Generated __TODAY__ · __MODEL__</span></div>
<div class="toast" id="toast">Copied to clipboard</div>
<script>
const BRIEF_PROMPTS=__BRIEF_JSON__;
function toggleTheme(){var h=document.documentElement;var t=h.getAttribute('data-theme')==='dark'?'light':'dark';h.setAttribute('data-theme',t);try{localStorage.setItem('osmo-theme',t);}catch(e){}document.getElementById('tgl').textContent=t==='dark'?'☀':'◐';}
(function(){try{var t=localStorage.getItem('osmo-theme')||'light';document.getElementById('tgl');}catch(e){}})();
function go(p){var b=document.querySelector('.tab[data-p="'+p+'"]');if(b)b.click();window.scrollTo({top:0,behavior:'smooth'});}
document.getElementById('tabs').onclick=function(e){var b=e.target.closest('.tab');if(!b)return;document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('on');});b.classList.add('on');document.querySelectorAll('.panel').forEach(function(p){p.classList.remove('on');});document.getElementById('p-'+b.dataset.p).classList.add('on');};
function chipSel(el,group,fn){document.querySelectorAll('#'+group+' .chip').forEach(function(c){c.classList.remove('on');});el.classList.add('on');window[fn]();}
function applyFeed(){
  var q=document.getElementById('q').value.toLowerCase();
  var chip=document.querySelector('#radar-chips .chip.on').dataset.sev;
  var sort=document.getElementById('sort').value;
  var feed=document.getElementById('feed');var items=[].slice.call(feed.querySelectorAll('.item'));
  var vis=0;
  items.forEach(function(it){var show=(chip==='all'||it.dataset.sev===chip)&&(!q||it.dataset.text.indexOf(q)>=0);it.style.display=show?'':'none';if(show)vis++;});
  if(sort==='severity')items.sort(function(a,b){return a.dataset.rank-b.dataset.rank;});
  else if(sort==='az')items.sort(function(a,b){return a.dataset.title.localeCompare(b.dataset.title);});
  items.forEach(function(it){feed.appendChild(it);});
  document.getElementById('empty').style.display=vis?'none':'block';
  document.getElementById('cnt').textContent=vis+' showing';
}
function applyLaunch(){
  var q=document.getElementById('q2').value.toLowerCase();
  var chip=document.querySelector('#intel-chips .chip.on').dataset.th;
  var rows=[].slice.call(document.querySelectorAll('#launch .lrow'));var vis=0;
  rows.forEach(function(r){var show=(chip==='all'||r.dataset.th===chip)&&(!q||r.dataset.text.indexOf(q)>=0);r.style.display=show?'':'none';if(show)vis++;});
  document.getElementById('empty2').style.display=vis?'none':'block';
}
var psk='per',psd=1;
document.querySelectorAll('#tbl th[data-k]').forEach(function(th){th.onclick=function(){var k=th.dataset.k;if(k===psk)psd*=-1;else{psk=k;psd=1;}sortTable();};});
function sortTable(){
  var tb=document.getElementById('tb');var rows=[].slice.call(tb.querySelectorAll('tr'));
  var num=document.querySelector('#tbl th[data-k="'+psk+'"]').dataset.n;
  rows.sort(function(a,b){var x=a.dataset[psk],y=b.dataset[psk];if(num){return (parseFloat(x)-parseFloat(y))*psd;}return x.localeCompare(y)*psd;});
  rows.forEach(function(r){tb.appendChild(r);});
  document.querySelectorAll('#tbl th').forEach(function(t){t.classList.toggle('sorted',t.dataset.k===psk);});
}
function brief(t){window.open('https://claude.ai/new?q='+encodeURIComponent(BRIEF_PROMPTS[t]||'Give me a marketing brief for Osmo electrolytes India.'),'_blank');}
function cp(e,t){e.stopPropagation();try{navigator.clipboard.writeText('Osmo — '+t);}catch(err){}var x=document.getElementById('toast');x.classList.add('show');setTimeout(function(){x.classList.remove('show');},1500);}
applyFeed();
</script>
</body>
</html>'''

# ════════════════════════════════════════════════════════════════════════════
# RENDER HELPERS — OSMO_RADAR dashboard (light default + dark toggle)
# ════════════════════════════════════════════════════════════════════════════

URG = {"critical":"crit","high":"high","medium":"med","low":"low"}
URG_RANK = {"critical":0,"high":1,"medium":2,"low":3}
HEAT_HEX = {"red":"var(--crit)","amber":"var(--watch)","gold":"var(--accent)","green":"var(--accent-2)"}
DOT_HEX  = {"red":"var(--crit)","gold":"var(--accent)","green":"var(--accent-2)","amber":"var(--watch)"}
# threat -> (css class, label)
THREAT = {
    "high":("crit","High threat"), "disruptor":("crit","Disruptor"),
    "high-alert":("accent","High-alert"), "pressure":("accent","Price pressure"),
    "watch":("watch","Watch"), "monitor":("mono","Monitor"),
    "opportunity":("opp","Opportunity"),
}

def _feed_card(item, kind="india"):
    sev = URG.get(item.get("urgency","medium"),"med")
    rank = URG_RANK.get(item.get("urgency","medium"),2)
    text = (item.get("title","")+" "+item.get("what","")+" "+item.get("tag","")).lower().replace('"',"")
    angle = item.get("angle","")
    extra = ""
    if kind=="india":
        extra = f'<div class="ang"><b>Angle:</b> {esc(angle)}</div>' if angle else ""
        action = esc(item.get("action","weekly_brief"))
        btn = f'<button class="copy" onclick="brief(\'{action}\')">Get content brief →</button>'
    elif kind=="global":
        extra = f'<div class="ang"><b>Angle:</b> {esc(angle)}</div>' if angle else ""
        btn = f'<button class="copy" onclick="cp(event,\'{esc(item.get("title",""))}\')">Copy insight</button>'
    else:  # competitor
        extra = f'<div class="ang"><b>White space:</b> {esc(item.get("gap",""))}</div>' if item.get("gap") else ""
        btn = f'<button class="copy" onclick="brief(\'competitor_alert\')">Response brief →</button>'
    return f"""<div class="item" data-sev="{sev}" data-rank="{rank}" data-text="{esc(text)}" data-title="{esc(item.get('title','').lower())}">
      <div class="itop"><span class="badge {sev}">{esc(item.get('urgency','signal'))}</span><span class="region">{esc(item.get('tag',''))}</span></div>
      <h4>{esc(item.get('title',''))}</h4>
      <p>{esc(item.get('what',''))}</p>{extra}
      {btn}</div>"""

def radar_feed_html(items):
    if not items: return '<div class="empty" style="display:block">No India moments returned this morning.</div>'
    return "\n".join(_feed_card(i,"india") for i in items)

def global_feed_html(items):
    if not items: return '<div class="empty" style="display:block">No global trends returned this morning.</div>'
    return "\n".join(_feed_card(i,"global") for i in items)

def compai_feed_html(items):
    if not items: return '<div class="empty" style="display:block">No competitor moves flagged this morning.</div>'
    return "\n".join(_feed_card(i,"competitor") for i in items)

def heat_html(items):
    out=[]
    for it in items:
        c = HEAT_HEX.get(it.get("color_hint","gold"),"var(--accent)")
        s = int(it.get("score",50))
        out.append(f'<div class="heat-row"><div class="hh"><span>{esc(it.get("label",""))}</span><span class="sc" style="color:{c}">{s}</span></div><div class="heat-track"><div class="heat-fill" style="width:{s}%;background:{c}"></div></div></div>')
    return "\n".join(out)

def trig_html(items):
    out=[]
    for it in items:
        c = DOT_HEX.get(it.get("dot_color","gold"),"var(--accent)")
        now = "now" if it.get("month_label","").upper()=="NOW" else ""
        out.append(f'<div class="trig-row {now}"><span class="mo" style="background:{c}">{esc(it.get("month_label",""))}</span><div><div class="tt">{esc(it.get("title",""))}</div><p>{esc(it.get("description",""))}</p></div></div>')
    return "\n".join(out)

def land_html(brands):
    out=[]
    for b in brands:
        cls,label = THREAT.get(b.get("threat","monitor"),("mono","Monitor"))
        out.append(f'<div class="card land-card"><div class="lh"><span class="nm">{esc(b.get("name",""))}</span><span class="tg {cls}">{esc(label)}</span></div><p>{esc(b.get("desc",""))}</p></div>')
    return "\n".join(out)

def pricing_html(rows):
    enr=[]
    for r in rows:
        per = r["price"]/max(r.get("servings",1),1)
        enr.append((r,per))
    enr.sort(key=lambda x:(not x[0].get("is_osmo"), x[1]))
    out=[]
    for r,per in enr:
        leader = "leader" if r.get("is_osmo") else ""
        tag = '<span class="lead-tag">LEADER</span>' if r.get("is_osmo") else ""
        strike = ""
        if r.get("mrp") and r["price"]<r["mrp"]:
            pct = round((1-r["price"]/r["mrp"])*100)
            strike = f' <span style="color:var(--text-3);text-decoration:line-through;font-size:11px">₹{r["mrp"]}</span> <span style="color:var(--accent-2);font-size:10px;font-family:var(--m)">-{pct}%</span>'
        out.append(f'<tr class="{leader}" data-brand="{esc(r["brand"].lower())}" data-price="{r["price"]}" data-per="{per:.2f}">'
                   f'<td class="brand">{esc(r["brand"])}{tag}<span class="sku">{esc(r.get("sku",""))} · {esc(r.get("pack",""))}</span></td>'
                   f'<td class="num">₹{r["price"]}{strike}</td>'
                   f'<td class="per">₹{round(per)}</td>'
                   f'<td><a class="srclink" href="{esc(r.get("link","#"))}" target="_blank" rel="noopener">{esc(r.get("source",""))} ↗</a></td></tr>')
    return "\n".join(out)

def _verified_badge(ent):
    v = ent.get("verified")
    if v:
        try:
            vo = datetime.strptime(v,"%Y-%m-%d").strftime("%d %b %y")
        except Exception:
            vo = v
        return f'<span class="vbadge">✓ verified {vo}</span>'
    return '<span class="vbadge warn">⚠ needs re-verify</span>'

def launches_html(entrants, radar):
    out=[]
    for e in entrants:
        cls,_ = THREAT.get(e.get("threat","monitor"),("mono","Monitor"))
        when = format_event_date(e["date"]) if e.get("date") else "—"
        text = (e.get("brand","")+" "+e.get("parent","")+" "+e.get("summary","")).lower().replace('"',"")
        out.append(f'<div class="lrow" data-th="{esc(e.get("threat","monitor"))}" data-text="{esc(text)}">'
                   f'<span class="ld {cls}"></span>'
                   f'<div class="linfo"><div class="lname">{esc(e.get("brand",""))}</div><div class="lsub">{esc(e.get("parent",""))}</div></div>'
                   f'<span class="lsp"></span><span class="lwhen">{esc(when)}</span>{_verified_badge(e)}'
                   f'<a class="srclink" href="{esc(e.get("verify","#"))}" target="_blank" rel="noopener" style="margin-left:10px">verify ↗</a></div>')
    for r in radar:
        cls,_ = THREAT.get(r.get("threat","watch"),("watch","Watch"))
        days = r.get("days_ago_estimate",0)
        when = f"~{days}d ago" if days else "this week"
        text = (r.get("brand","")+" "+r.get("what","")).lower().replace('"',"")
        out.append(f'<div class="lrow flagged" data-th="{esc(r.get("threat","watch"))}" data-text="{esc(text)}">'
                   f'<span class="ld {cls}"></span>'
                   f'<div class="linfo"><div class="lname">{esc(r.get("brand",""))} <span class="flag">⚡ RADAR</span></div><div class="lsub">{esc(r.get("what","")[:90])}</div></div>'
                   f'<span class="lsp"></span><span class="lwhen">{esc(when)}</span><span class="vbadge warn">⚠ flagged · unverified</span></div>')
    return "\n".join(out)

def events_full_html(events):
    if not events: return ""
    def evt_block(ev, hero=False):
        score = ev.get("hyd_score",0)
        if ev.get("date"):
            when = f'{format_event_date(ev["date"])} · {esc(ev.get("venue","").split("·")[-1].strip()[:24])}'
            d = days_until(ev["date"]); cd = f"in {d} days" if d>0 else ("today" if d==0 else "past")
        else:
            when = esc(ev.get("date_note","Date pending")); cd = "TBD"
        tentative = '<span class="tg watch">Tentative</span>' if ev.get("tentative") else '<span class="tg opp">Confirmed</span>'
        if hero:
            return f"""<div class="card evt-hero">
      <div class="ehead"><div><div class="when">{when} · {cd}</div><h3>{esc(ev.get("name",""))}</h3></div>{tentative}</div>
      <div class="evt-stats">
        <div class="evt-stat"><div class="l">Hydration fit</div><div class="v">{score}/10</div></div>
        <div class="evt-stat"><div class="l">Sport</div><div class="v sm">{esc(ev.get("sport_label",""))}</div></div>
        <div class="evt-stat"><div class="l">Organiser</div><div class="v sm">{esc(ev.get("organiser","")[:18])}</div></div>
      </div>
      <div class="evt-body"><div class="q">{esc(ev.get("hydration",""))}</div>
        <div class="evt-actions"><button class="btn primary" onclick="brief('events_brief')">Athlete tie-up brief →</button>
        <a class="btn ghost" href="{esc(ev.get("verify","#"))}" target="_blank" rel="noopener">Verify event ↗</a></div></div></div>"""
        return f"""<div class="card sec-evt"><span class="score">{score}/10</span>
      <div class="info"><div class="meta">{esc(ev.get("sport_label",""))} · {when} · {cd}</div>
      <div class="nm">{esc(ev.get("name",""))}</div><p>{esc(ev.get("hydration",""))}</p></div></div>"""
    parts=[evt_block(events[0],hero=True)]
    parts.append('<div class="subhead">All tracked events <span class="tagn">hydration-fit scored</span></div>')
    parts += [evt_block(e) for e in events[1:]]
    return "\n".join(parts)

def briefs_html(items):
    out=[]
    for it in items:
        timing = it.get("timing","This week")
        prio = "urgent" if timing=="Do today" else ("med" if timing=="This week" else "low")
        out.append(f"""<div class="card brief"><div class="top"><h3>{esc(it.get("title",""))}</h3><span class="prio {prio}">{esc(timing)}</span></div>
      <p>{esc(it.get("description",""))}</p>
      <div class="metric">{esc(it.get("channel",""))} · {esc(it.get("tone",""))}</div>
      <div class="brief-actions"><button class="btn primary" onclick="brief('{esc(it.get("brief_type","weekly_brief"))}')">Generate copy ⚡</button>
      <button class="btn ghost" onclick="cp(event,'{esc(it.get("title",""))}')">Copy title</button></div></div>""")
    return "\n".join(out)

def ticker_html(india, global_, radar):
    items=[]
    for i in india[:2]:
        items.append(f'<div class="it">{esc(i.get("title","")[:60])} <b class="hot">{esc(i.get("urgency","").upper())}</b></div>')
    for r in radar[:2]:
        items.append(f'<div class="it">NEW · {esc(r.get("brand",""))} <b class="hot">{esc(r.get("threat","watch").upper())}</b></div>')
    items += [
        '<div class="it">India 2026 <b class="up">$81M</b> ↑ 13.9% CAGR</div>',
        '<div class="it">Global <b>$43B</b></div>',
        '<div class="it">Zero-sugar <b class="up">↑ 41% share</b></div>',
    ]
    return "".join(items+items)

# ── computed KPI values ─────────────────────────────────────────────────────
_crit_ct = len([i for i in india_items if i.get("urgency")=="critical"])
_osmo = next((r for r in PRICING_DATA if r.get("is_osmo")), None)
_osmo_per = round(_osmo["price"]/max(_osmo.get("servings",1),1)) if _osmo else 0
BRIEF_JSON = json.dumps(BRIEF_PROMPTS)

# ── assemble fragments ──────────────────────────────────────────────────────
REPL = {
    "__TODAY__": TODAY,
    "__MODEL__": MODEL.upper(),
    "__PRICING_VERIFIED__": PRICING_VERIFIED,
    "__TICKER__": ticker_html(india_items, global_items, radar_items),
    "__CRIT_CT__": str(_crit_ct),
    "__OSMO_PER__": str(_osmo_per),
    "__RADAR_CT__": str(len(radar_items)),
    "__EVENTS_CT__": str(len(EVENTS_DATA)),
    "__ENTRANTS_CT__": str(len(ENTRANTS_DATA)),
    "__INDIA_FEED__": radar_feed_html(india_items),
    "__HEAT__": heat_html(heatmap),
    "__TRIG__": trig_html(triggers),
    "__LAND__": land_html(landscape_items),
    "__PRICING__": pricing_html(PRICING_DATA),
    "__LAUNCHES__": launches_html(ENTRANTS_DATA, radar_items),
    "__COMPAI__": compai_feed_html(competitor_items),
    "__EVENTS__": events_full_html(EVENTS_DATA),
    "__BRIEFS__": briefs_html(actions),
    "__GLOBAL__": global_feed_html(global_items),
    "__BRIEF_JSON__": BRIEF_JSON,
}

html = TEMPLATE
for k,v in REPL.items():
    html = html.replace(k, v)

# ── WRITE OUTPUT ─────────────────────────────────────────────────────────────
out_path = os.path.join(os.path.dirname(__file__), "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ index.html written ({len(html):,} bytes)")
print(f"   Date: {TODAY} · Model: {MODEL}")
print(f"   India: {len(india_items)} · Global: {len(global_items)} · CompAI: {len(competitor_items)} · Radar: {len(radar_items)}")
print(f"   Events: {len(EVENTS_DATA)} · Entrants: {len(ENTRANTS_DATA)} · Landscape: {len(landscape_items)}")
