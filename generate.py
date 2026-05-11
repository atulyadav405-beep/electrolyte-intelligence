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
from datetime import datetime, timezone, timedelta, date

# ── CONFIG ──────────────────────────────────────────────────────────────────
MODEL = "claude-sonnet-4-6"
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


def fetch(prompt: str, schema_hint: str = "", max_tokens: int = 1500) -> list:
    """Call Claude and return parsed JSON list."""
    full_prompt = f"{prompt}\n\nReturn a JSON array. {schema_hint}"
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=SYSTEM,
        messages=[{"role": "user", "content": full_prompt}]
    )
    raw = msg.content[0].text.strip()
    # Strip non-ASCII and markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()
    raw = re.sub(r'[\x00-\x1f\x7f]', '', raw)
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

COMPETITORS_LANDSCAPE = [
    {"name":"Fast&Up", "desc":"Effervescent tabs, pan-India. Launched electrolyte popsicles with NOTO (₹102). Aam panna + cola flavours show Indian palate ambition.", "threat":"high"},
    {"name":"Powerade (Coca-Cola)", "desc":"Power Water zero-sugar launched India Nov 2025. First serious clean-label move from a major. Watch for wider rollout.", "threat":"watch"},
    {"name":"Campa (Reliance)", "desc":"₹10 SKU via vertical integration. Forcing portfolio segmentation decisions across all incumbents.", "threat":"pressure"},
    {"name":"MuscleBlaze", "desc":"India's largest sports nutrition brand. If they scale electrolytes with their distribution, it's a direct threat.", "threat":"monitor"},
    {"name":"LMNT India", "desc":"Just landed. Same positioning, higher sodium dose, lower per-serving cost. Already running US-style influencer playbook.", "threat":"disruptor"},
    {"name":"Enerzal / ORS", "desc":"Govt actively pushing ORS for heatwave victims — creates 'upgrade narrative' opportunity for Osmo.", "threat":"opportunity"},
]

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
     "date":"2026-04-30", "threat":"disruptor",
     "mrp":"Per official D2C site", "pser":"TBA / serving",
     "summary":"Rohit Sharma's birthday launch positions hydRo365 as a daily-hydration lifestyle brand — explicitly NOT just for athletes. Celebrity-led, monk-fruit clean-label, and the 365 messaging hits Osmo's everyday-premium narrative dead-centre.",
     "claims":"6 essential electrolytes · Vitamin C · Zinc · B-vitamins · L-theanine · Monk-fruit sweetened · Clean-label",
     "distribution":"D2C (hydro365.com) · Marketplaces (rolling)", "target":"Premium · Wellness",
     "vs_osmo":"Same clean-label playbook with celebrity firepower Osmo can't match on cost. Osmo wins on science depth, athlete proof, and combat/hybrid sports positioning.",
     "verify":"https://www.hydro365.com/"},
    {"brand":"Liquid I.V. India", "parent":"by HUL · Unilever · Hydration Multiplier · Powder · Stick",
     "date":"2026-04-11", "threat":"disruptor",
     "mrp":"₹1,496 / 16 sticks", "pser":"₹94 / serving",
     "summary":"HUL has fully launched Liquid I.V. in India in 3 flavours (Acai Berry · Brazilian Orange · Lemon Lime). Unilever distribution muscle + global brand authority + quick-commerce play makes this the single biggest competitive event of the year.",
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
    {"brand":"Powerade Power Water", "parent":"by Coca-Cola India · Power Water Zero-Sugar · RTD · 500 ml",
     "date":"2025-11-15", "threat":"high-alert",
     "mrp":"TBC", "pser":"Mass-premium / serving",
     "summary":"Coca-Cola's first serious clean-label entry into Indian hydration. ₹40 Cr ad spend reported through summer 2026.",
     "claims":"Zero sugar · Electrolytes · Coca-Cola distribution",
     "distribution":"Modern trade · Quick-commerce · Kirana (rolling)", "target":"Mass · Everyday",
     "vs_osmo":"Big spend ≠ credibility. Osmo's science depth, athlete proof, and clean-label authenticity beat ad volume.",
     "verify":"https://www.cocacolaindia.com/"},
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
     "date":"2025-02-18", "threat":"monitor",
     "mrp":"₹10 / bottle", "pser":"₹10 / serving",
     "summary":"₹10 RTD with Muttiah Muralitharan as co-creator. 5 IPL franchises tied in for 2026 season. Mass-priced sweat-replacement positioning.",
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
    'competitor_alert': 'Analyze the competitive landscape for Osmo in India right now. Fast&Up popsicles, Powerade Power Water, Campa ₹10 SKU, LMNT India launch, Liquid I.V. India — what should Osmo do?',
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

print("Fetching competitor intelligence (focused on new launches and brand moves)...")
competitor_items = fetch(
    f"""Generate 3 competitor intelligence insights for Osmo in India as of {TODAY}.
EMPHASIS: Focus on NEW launches, new SKUs, new initiatives, or brand moves made by
competitors in the last 14 days. Known context: Fast&Up popsicles with NOTO (Apr),
hydRo365 launched by Rohit Sharma (Apr 30), Liquid I.V. India by HUL (full launch),
Powerade Power Water (Nov 2025), Campa ₹10 SKU, MuscleBlaze Sports Hydr8 PRO,
Protyze HYDRA-X all-in-one.
Each object: title, urgency, what (what the competitor did NEW), gap (white space Osmo can claim), tag""",
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
days_ago_estimate (integer, your best estimate of how many days ago this happened, 0-14)""",
    "Fields: brand, what, source_hint, threat, days_ago_estimate. 3-4 items."
)

print("All data fetched. Building HTML...")


# ════════════════════════════════════════════════════════════════════════════
# HTML HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

URG_CLASS = {"critical":"urg-critical", "high":"urg-high", "medium":"urg-medium", "low":"urg-low"}
DOT_COLORS = {"red":"var(--red)", "gold":"var(--accent)", "green":"var(--accent-2)", "amber":"var(--accent-3)"}
HEAT_COLORS = {"red":"var(--red)", "amber":"var(--accent-3)", "gold":"var(--accent)", "green":"var(--accent-2)"}
LANDSCAPE_THREAT = {
    "high":       ("High threat",        "rgba(199,91,91,.14)",   "#e07474",         "rgba(199,91,91,.3)"),
    "watch":      ("Watch closely",       "rgba(212,165,116,.14)", "var(--accent-3)", "rgba(212,165,116,.28)"),
    "pressure":   ("Price pressure",      "rgba(212,165,116,.14)", "var(--accent-3)", "rgba(212,165,116,.28)"),
    "monitor":    ("Monitor",             "rgba(200,169,126,.12)", "var(--accent)",   "rgba(200,169,126,.22)"),
    "disruptor":  ("Disruptor",           "rgba(199,91,91,.14)",   "#e07474",         "rgba(199,91,91,.3)"),
    "opportunity":("Low · Opportunity",  "rgba(107,142,123,.14)", "var(--accent-2)", "rgba(107,142,123,.25)"),
}


def india_cards_html(items):
    urgent = [i for i in items if i.get("urgency") in ("critical","high")]
    ongoing = [i for i in items if i.get("urgency") in ("medium","low")]
    def card(item, open_body=False):
        uc = URG_CLASS.get(item.get("urgency","medium"), "urg-medium")
        body_class = "insight-card-body open" if open_body else "insight-card-body"
        return f"""
        <div class="insight-card">
          <div class="insight-card-head" onclick="toggleCard(this)">
            <div class="insight-card-title">{esc(item.get('title',''))}</div>
            <span class="urgency-badge {uc}">{esc(item.get('urgency',''))}</span>
          </div>
          <div class="{body_class}">
            <div class="insight-block"><div class="insight-block-label">What's happening</div><div class="insight-block-text">{esc(item.get('what',''))}</div></div>
            <div class="insight-block"><div class="insight-block-label">Why it matters</div><div class="insight-block-text">{esc(item.get('why',''))}</div></div>
            <div class="insight-block"><div class="insight-block-label">Marketing angle</div><div class="insight-block-text"><strong>{esc(item.get('angle',''))}</strong></div></div>
            <div class="card-tag-row"><span class="card-tag">{esc(item.get('tag',''))}</span></div>
            <div class="card-actions">
              <button class="card-action-btn" onclick="brief('{esc(item.get('action','weekly_brief'))}')">Get content brief →</button>
            </div>
          </div>
        </div>"""
    urgent_html = "\n".join(card(i, open_body=(j==0)) for j,i in enumerate(urgent))
    ongoing_html = "\n".join(card(i) for i in ongoing)
    return f"""
      <div class="panel-section">
        <div class="panel-section-title">Critical · act immediately</div>
        {urgent_html}
      </div>
      <div class="panel-section">
        <div class="panel-section-title">Ongoing opportunities</div>
        {ongoing_html}
      </div>"""


def global_cards_html(items):
    def card(item, first=False):
        uc = URG_CLASS.get(item.get("urgency","medium"), "urg-medium")
        body_class = "insight-card-body open" if first else "insight-card-body"
        return f"""
        <div class="insight-card">
          <div class="insight-card-head" onclick="toggleCard(this)">
            <div class="insight-card-title">{esc(item.get('title',''))}</div>
            <span class="urgency-badge {uc}">{esc(item.get('urgency',''))}</span>
          </div>
          <div class="{body_class}">
            <div class="insight-block"><div class="insight-block-label">What's happening</div><div class="insight-block-text">{esc(item.get('what',''))}</div></div>
            <div class="insight-block"><div class="insight-block-label">Marketing angle</div><div class="insight-block-text"><strong>{esc(item.get('angle',''))}</strong></div></div>
            <div class="card-tag-row"><span class="card-tag">{esc(item.get('tag',''))}</span></div>
          </div>
        </div>"""
    return "\n".join(card(i, first=(j==0)) for j,i in enumerate(items))


def competitor_cards_html(items):
    def card(item, first=False):
        uc = URG_CLASS.get(item.get("urgency","medium"), "urg-medium")
        body_class = "insight-card-body open" if first else "insight-card-body"
        return f"""
        <div class="insight-card">
          <div class="insight-card-head" onclick="toggleCard(this)">
            <div class="insight-card-title">{esc(item.get('title',''))}</div>
            <span class="urgency-badge {uc}">{esc(item.get('urgency',''))}</span>
          </div>
          <div class="{body_class}">
            <div class="insight-block"><div class="insight-block-label">What they did</div><div class="insight-block-text">{esc(item.get('what',''))}</div></div>
            <div class="insight-block"><div class="insight-block-label">White space for Osmo</div><div class="insight-block-text"><strong>{esc(item.get('gap',''))}</strong></div></div>
            <div class="card-tag-row"><span class="card-tag">{esc(item.get('tag',''))}</span></div>
          </div>
        </div>"""
    return "\n".join(card(i, first=(j==0)) for j,i in enumerate(items))


def actions_html(items):
    out = []
    for i, item in enumerate(items, 1):
        timing = item.get("timing","")
        timing_class = "urg-critical" if timing=="Do today" else ("urg-high" if timing=="This week" else "urg-low")
        out.append(f"""
        <div class="action-item">
          <div class="action-num">{i:02d}</div>
          <div class="action-content">
            <div class="action-title">{esc(item.get('title',''))}</div>
            <div class="action-desc">{esc(item.get('description',''))}</div>
            <div class="action-meta">
              <span class="action-chip">{esc(item.get('channel',''))}</span>
              <span class="action-chip">{esc(item.get('tone',''))}</span>
              <span class="urgency-badge {timing_class}" style="font-size:9px;padding:3px 8px">{esc(timing)}</span>
              <button class="action-cta" onclick="brief('{esc(item.get('brief_type','weekly_brief'))}')">Generate copy →</button>
            </div>
          </div>
        </div>""")
    return "\n".join(out)


def heatmap_html(items):
    rows = []
    for item in items:
        color = HEAT_COLORS.get(item.get("color_hint","gold"), "var(--accent)")
        score = int(item.get("score",50))
        rows.append(f"""
      <div class="heat-row">
        <div class="heat-label">{esc(item.get('label',''))}</div>
        <div class="heat-bar-wrap"><div class="heat-bar" style="width:{score}%;background:{color}"></div></div>
        <div class="heat-val" style="color:{color}">{score}</div>
      </div>""")
    return "\n".join(rows)


def triggers_html(items):
    rows = []
    for item in items:
        color = DOT_COLORS.get(item.get("dot_color","gold"), "var(--accent)")
        rows.append(f"""
      <div class="cal-item">
        <div class="cal-date">{esc(item.get('month_label',''))}</div>
        <div class="cal-dot" style="background:{color}"></div>
        <div class="cal-text"><strong>{esc(item.get('title',''))}</strong> — {esc(item.get('description',''))}</div>
      </div>""")
    return "\n".join(rows)


def ticker_items_html(india, global_, radar):
    items = []
    for i in india[:2]:
        items.append(f'<div class="ticker-item">{esc(i.get("title","")[:70])} <span class="hot">{esc(i.get("urgency","").upper())}</span></div>')
    for r in radar[:2]:
        items.append(f'<div class="ticker-item">NEW · {esc(r.get("brand",""))} — {esc(r.get("what","")[:50])} <span class="hot">{esc(r.get("threat","watch").upper())}</span></div>')
    for g in global_[:2]:
        items.append(f'<div class="ticker-item">{esc(g.get("title","")[:60])} <span class="up">↑ trending</span></div>')
    items += [
        '<div class="ticker-item">India market 2026 <span class="val up">$81M</span> <span class="up">↑ 13.9% CAGR</span></div>',
        '<div class="ticker-item">Global market <span class="val">$43B</span></div>',
        '<div class="ticker-item">IPL 2026 <span class="val up">LIVE</span> through May 31</div>',
        '<div class="ticker-item">Zero-sugar formats <span class="up">↑ 41% global share</span></div>',
    ]
    return "\n      ".join(items + items)  # doubled for seamless loop


def landscape_html(brands):
    cards = []
    for b in brands:
        label, bg, fg, border = LANDSCAPE_THREAT.get(b["threat"], LANDSCAPE_THREAT["monitor"])
        cards.append(f"""
          <div class="comp-card">
            <div class="comp-name">{esc(b['name'])}</div>
            <div class="comp-desc">{esc(b['desc'])}</div>
            <span class="threat-chip" style="background:{bg};color:{fg};border:1px solid {border}">{esc(label)}</span>
          </div>""")
    return "\n".join(cards)


def events_html(events):
    cards = []
    for ev in events:
        sport_color = ev["color"]
        if ev["date"]:
            date_label = format_event_date(ev["date"])
            d = days_until(ev["date"])
            countdown = f"in {d} days" if d > 0 else ("today" if d == 0 else "past")
            tbd_badge = ""
        else:
            date_label = "TBD"
            countdown = ev.get("date_note","Date pending")
            tbd_badge = '<span class="tbd-badge">⓲ Date TBD</span>'
        tentative_cls = " is-tentative" if ev.get("tentative") else ""
        tags_html = "".join(f'<span class="card-tag">{esc(t)}</span>' for t in ev.get("tags",[]))
        cards.append(f"""
      <div class="event-card{tentative_cls}" data-sport-type="{esc(ev['sport_type'])}" data-tentative="{1 if ev.get('tentative') else 0}" onclick="toggleEvent(this)">
        <div class="event-accent" style="background:{sport_color}"></div>
        <div class="event-head">
          <div>
            <div class="event-meta-row">
              <span class="event-sport-chip" style="color:{sport_color};border-color:{sport_color}40;background:{sport_color}12">{esc(ev['sport_label'])}</span>
              <span class="event-date">{date_label}</span>
              <span class="event-countdown">{esc(countdown)}</span>
              {tbd_badge}
            </div>
            <div class="event-name">{esc(ev['name'])}</div>
            <div class="event-venue">{esc(ev['venue'])}</div>
          </div>
          <div class="hyd-score" style="color:{ev['hyd_color']};border-color:{ev['hyd_color']}40">
            <div class="hyd-score-label">HYDRATION</div>
            <div class="hyd-score-num">{ev['hyd_score']}<span style="font-size:11px;color:var(--text-3)">/10</span></div>
          </div>
        </div>
        <div class="event-hover-angle">
          <div class="hover-label">HYDRATION ANGLE — why it matters</div>
          <div class="hover-text">{esc(ev['hover'])}</div>
        </div>
        <div class="event-body">
          <div class="event-block"><div class="event-block-label">Organiser</div><div class="event-block-text">{esc(ev['organiser'])}</div></div>
          <div class="event-block"><div class="event-block-label">Key athletes</div><div class="event-block-text">{esc(ev['athletes'])}</div></div>
          <div class="event-block"><div class="event-block-label">Hydration angle</div><div class="event-block-text">{esc(ev['hydration'])}</div></div>
          <div class="event-block accent">
            <div class="event-block-label">Suggested Osmo activation</div>
            <div class="event-block-text"><strong>{esc(ev['activation'])}</strong></div>
          </div>
          <div class="card-tag-row">{tags_html}</div>
          <div class="card-actions">
            <a class="card-action-btn verify-btn" href="{esc(ev['verify'])}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Verify · Read more ↗</a>
            <button class="card-action-btn" onclick="event.stopPropagation();brief('athlete_tieup')">Athlete tie-up brief →</button>
            <button class="card-action-btn" onclick="event.stopPropagation();brief('events_brief')">Full activation plan →</button>
          </div>
        </div>
      </div>""")
    return "\n".join(cards)


def entrants_html(entrants):
    rows = []
    for ent in entrants:
        threat_key = ent["threat"]
        dot_color, bg, fg, border = ENTRANT_THREAT.get(threat_key, ENTRANT_THREAT["monitor"])
        threat_label = {"disruptor":"Disruptor","high-alert":"High Alert","watch":"Watch","monitor":"Monitor"}.get(threat_key, threat_key)
        bucket = "month" if days_ago(ent["date"]) <= 30 else "older"
        if days_ago(ent["date"]) <= 7:
            bucket = "week"
        date_obj = datetime.strptime(ent["date"], "%Y-%m-%d") if ent.get("date") else None
        date_label = date_obj.strftime("%b %d %Y").upper() if date_obj else "—"
        days_label = f"· {days_ago(ent['date'])} days ago" if ent.get("date") else ""
        rows.append(f"""
      <div class="entrant-row" data-threat="{esc(threat_key)}" data-bucket="{bucket}">
        <div class="entrant-timeline">
          <div class="entrant-dot" style="background:{dot_color}"></div>
          <div class="entrant-line"></div>
        </div>
        <div class="entrant-card" onclick="toggleEntrant(this)">
          <div class="entrant-head">
            <div>
              <div class="entrant-meta-row">
                <span class="entrant-date">{esc(date_label)}</span>
                <span class="entrant-days">{esc(days_label)}</span>
                <span class="threat-pill" style="background:{bg};color:{fg};border:1px solid {border}">{esc(threat_label)}</span>
              </div>
              <div class="entrant-brand">{esc(ent['brand'])}</div>
              <div class="entrant-parent">{esc(ent['parent'])}</div>
            </div>
            <div class="entrant-pricing">
              <div class="entrant-mrp">{esc(ent['mrp'])}</div>
              <div class="entrant-pser">{esc(ent['pser'])}</div>
            </div>
          </div>
          <div class="entrant-summary">{esc(ent['summary'])}</div>
          <div class="entrant-body">
            <div class="entrant-grid">
              <div class="entrant-block"><div class="entrant-block-label">Claims</div><div class="entrant-block-text">{esc(ent['claims'])}</div></div>
              <div class="entrant-block"><div class="entrant-block-label">Distribution</div><div class="entrant-block-text">{esc(ent['distribution'])}</div></div>
              <div class="entrant-block"><div class="entrant-block-label">Target segment</div><div class="entrant-block-text">{esc(ent['target'])}</div></div>
              <div class="entrant-block accent"><div class="entrant-block-label">vs. Osmo</div><div class="entrant-block-text"><strong>{esc(ent['vs_osmo'])}</strong></div></div>
            </div>
            <div class="card-actions">
              <a class="card-action-btn verify-btn" href="{esc(ent['verify'])}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Verify · Read more ↗</a>
              <button class="card-action-btn" onclick="event.stopPropagation();brief('entrants_brief')">Response plan →</button>
              <button class="card-action-btn" onclick="event.stopPropagation();brief('competitor_alert')">Brief Osmo team →</button>
            </div>
          </div>
        </div>
      </div>""")
    return "\n".join(rows)


def radar_html(items):
    """Top-of-page RADAR section showing AI-flagged new launches this week."""
    if not items:
        return '<div style="padding:20px;color:var(--text-3);font-family:var(--font-mono);font-size:11px">No new signals detected this morning. Check back tomorrow.</div>'
    cards = []
    for item in items:
        threat_key = item.get("threat","watch")
        dot_color, bg, fg, border = ENTRANT_THREAT.get(threat_key, ENTRANT_THREAT["watch"])
        threat_label = {"disruptor":"Disruptor","high-alert":"High Alert","watch":"Watch","monitor":"Monitor"}.get(threat_key, threat_key)
        days_est = item.get("days_ago_estimate", 0)
        days_label = f"~{days_est}d ago" if days_est else "this week"
        cards.append(f"""
        <div class="radar-card">
          <div class="radar-card-head">
            <div class="radar-meta">
              <span class="radar-unverified">⚠ UNVERIFIED · AI-flagged</span>
              <span class="radar-days">{esc(days_label)}</span>
              <span class="threat-pill" style="background:{bg};color:{fg};border:1px solid {border}">{esc(threat_label)}</span>
            </div>
            <div class="radar-brand">{esc(item.get('brand',''))}</div>
          </div>
          <div class="radar-summary">{esc(item.get('what',''))}</div>
          <div class="radar-actions">
            <div class="radar-source-hint"><span class="hint-label">Where to verify:</span> {esc(item.get('source_hint','Web search'))}</div>
            <button class="card-action-btn" onclick="brief('radar_verify')">Verify with Claude →</button>
          </div>
        </div>""")
    return "\n".join(cards)


def pricing_html(rows):
    sorted_rows = sorted(rows, key=lambda r: (not r.get("is_osmo"), r["price"]/max(r["servings"],1)))
    cheapest_comp = min(r["price"]/max(r["servings"],1) for r in rows if not r.get("is_osmo"))
    osmo_per = next((r["price"]/max(r["servings"],1) for r in rows if r.get("is_osmo")), None)
    row_html = []
    for r in sorted_rows:
        per = r["price"] / max(r["servings"],1)
        discount = ""
        if r["mrp"] and r["price"] < r["mrp"]:
            pct = round((1 - r["price"]/r["mrp"])*100)
            discount = f'<span class="price-off">-{pct}%</span>'
        klass = "price-row price-osmo" if r.get("is_osmo") else "price-row"
        osmo_tag = '<span class="price-brand-tag">OSMO</span>' if r.get("is_osmo") else ""
        strike = f'<span class="price-mrp-strike">₹{r["mrp"]}</span>{discount}' if r["mrp"] != r["price"] else ""
        row_html.append(f"""
        <div class="{klass}">
          <div class="price-cell price-brand">{esc(r['brand'])} {osmo_tag}</div>
          <div class="price-cell price-sku">
            <div class="price-sku-name">{esc(r['sku'])}</div>
            <div class="price-pack">{esc(r['pack'])}</div>
          </div>
          <div class="price-cell price-mrp">
            <div class="price-mrp-val">₹{r['price']}</div>
            <div class="price-mrp-sub">{strike}</div>
          </div>
          <div class="price-cell price-perserve">
            <div class="price-perserve-val">₹{round(per)}</div>
            <div class="price-perserve-lbl">per serve</div>
          </div>
          <div class="price-cell price-link-cell">
            <a class="price-link" href="{esc(r['link'])}" target="_blank" rel="noopener">View on {esc(r['source'])} ↗</a>
          </div>
        </div>""")
    if osmo_per is not None and osmo_per <= cheapest_comp:
        takeaway = f"<strong>Osmo is the cheapest premium option per serve</strong> at ₹{round(osmo_per)} — undercutting every listed competitor while keeping science depth (Taurine + ZMA + B-complex) they don't have."
    elif osmo_per is not None:
        takeaway = f"Osmo at <strong>₹{round(osmo_per)}/serve</strong> sits ₹{round(osmo_per-cheapest_comp)} above the cheapest mass option (₹{round(cheapest_comp)}) — premium, not bargain. Lead with science depth, not price."
    else:
        takeaway = ""
    return f"""
        <div class="price-grid">
          <div class="price-row price-header">
            <div class="price-cell">Brand</div>
            <div class="price-cell">SKU</div>
            <div class="price-cell">Price</div>
            <div class="price-cell">Per serve</div>
            <div class="price-cell">Source</div>
          </div>
          {''.join(row_html)}
        </div>
        <div class="price-takeaway">{takeaway}</div>
        <div class="price-disclaimer">Prices fetched from each brand's official listing · last verified May 2026 · edit PRICING_DATA in generate.py to update</div>"""


def brief_js(prompts):
    lines = []
    for k, v in prompts.items():
        safe = v.replace("'", "\\'").replace("\n", " ")
        lines.append(f"    '{k}': '{safe}'")
    return "const BRIEF_PROMPTS = {\n" + ",\n".join(lines) + "\n  };"


# ════════════════════════════════════════════════════════════════════════════
# ASSEMBLE
# ════════════════════════════════════════════════════════════════════════════

INDIA_HTML       = india_cards_html(india_items)
GLOBAL_HTML      = global_cards_html(global_items)
COMPETITOR_HTML  = competitor_cards_html(competitor_items)
ACTIONS_HTML     = actions_html(actions)
HEATMAP_HTML     = heatmap_html(heatmap)
TRIGGERS_HTML    = triggers_html(triggers)
TICKER_HTML      = ticker_items_html(india_items, global_items, radar_items)
LANDSCAPE_HTML   = landscape_html(COMPETITORS_LANDSCAPE)
EVENTS_HTML      = events_html(EVENTS_DATA)
ENTRANTS_HTML    = entrants_html(ENTRANTS_DATA)
PRICING_HTML     = pricing_html(PRICING_DATA)
RADAR_HTML       = radar_html(radar_items)

# Build JS brief prompt map from fetched actions
for a in actions:
    bt = a.get("brief_type","")
    if bt and bt not in BRIEF_PROMPTS:
        BRIEF_PROMPTS[bt] = f"Write detailed marketing copy for: {a.get('title','')}. Channel: {a.get('channel','')}. Tone: {a.get('tone','')}. Brand: Osmo electrolytes India."
BRIEF_JS = brief_js(BRIEF_PROMPTS)

# Counts for header badges
EVENTS_COUNT = len(EVENTS_DATA)
ENTRANTS_COUNT = len(ENTRANTS_DATA)
RADAR_COUNT = len(radar_items)


html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Electrolyte Intelligence — {TODAY}</title>
<meta name="description" content="Daily electrolyte market intelligence for India — heatwave alerts, combat & hybrid sport calendar, new entrant radar, and actionable marketing briefs for Osmo.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0F1115;--bg-2:#14171C;--bg-3:#1A1D23;--bg-4:#22262E;
  --line:#2A2D35;--line-2:rgba(255,255,255,0.10);
  --text:#E8E4DF;--text-2:#B5B0A8;--text-3:#8A8580;
  --accent:#C8A97E;--accent-2:#6B8E7B;--accent-3:#D4A574;--red:#C75B5B;
  --font-display:'Instrument Serif',Georgia,serif;
  --font-body:'Inter',system-ui,sans-serif;
  --font-mono:'JetBrains Mono','SF Mono',Menlo,monospace;
  --max:1280px;--radius:12px;--t:300ms cubic-bezier(.22,.61,.36,1);
}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--text);font-family:var(--font-body);font-size:14px;line-height:1.6;min-height:100vh;-webkit-font-smoothing:antialiased;background-image:radial-gradient(ellipse 1200px 600px at 80% -10%,rgba(200,169,126,0.06),transparent 70%),radial-gradient(ellipse 800px 500px at 0% 40%,rgba(107,142,123,0.04),transparent 70%);background-attachment:fixed}}
.ticker-wrap{{border-bottom:1px solid var(--line);background:rgba(15,17,21,.85);backdrop-filter:blur(8px);overflow:hidden;height:32px;display:flex;align-items:center;position:sticky;top:0;z-index:200}}
.ticker-label{{font-family:var(--font-mono);font-size:10px;letter-spacing:.14em;color:var(--accent);padding:0 16px;border-right:1px solid var(--line);height:100%;display:flex;align-items:center;flex-shrink:0;white-space:nowrap;font-weight:500}}
.ticker-label .pulse{{width:6px;height:6px;border-radius:50%;background:var(--red);margin-right:8px;animation:pulse 1.6s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.ticker-track{{display:flex;gap:0;animation:ticker 60s linear infinite;white-space:nowrap}}
.ticker-track:hover{{animation-play-state:paused}}
.ticker-item{{font-family:var(--font-mono);font-size:10px;letter-spacing:.04em;color:var(--text-2);padding:0 24px;border-right:1px solid var(--line);height:32px;display:flex;align-items:center;gap:8px}}
.ticker-item .val{{color:var(--text)}}.ticker-item .up{{color:var(--accent-2)}}.ticker-item .hot{{color:var(--red)}}
@keyframes ticker{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
nav{{position:sticky;top:32px;z-index:150;display:flex;align-items:center;justify-content:space-between;padding:18px 48px;background:rgba(15,17,21,0.72);backdrop-filter:blur(14px) saturate(140%);-webkit-backdrop-filter:blur(14px) saturate(140%);border-bottom:1px solid var(--line)}}
.nav-brand{{display:flex;flex-direction:column;gap:2px}}
.nav-brand .brand-name{{font-family:var(--font-display);font-size:20px;letter-spacing:-.01em;color:var(--text);font-style:italic}}
.nav-brand .brand-sub{{font-family:var(--font-mono);font-size:9px;letter-spacing:.16em;color:var(--text-3);text-transform:uppercase}}
.nav-links{{display:flex;gap:28px;list-style:none}}
.nav-links a{{font-size:12px;color:var(--text-3);text-decoration:none;letter-spacing:.04em;transition:color var(--t);font-weight:500}}
.nav-links a:hover,.nav-links a.active{{color:var(--text)}}
.nav-right{{display:flex;align-items:center;gap:12px}}
.live-pill{{display:inline-flex;align-items:center;gap:6px;font-family:var(--font-mono);font-size:10px;color:var(--accent-2);border:1px solid rgba(107,142,123,.35);background:rgba(107,142,123,.08);padding:5px 10px;border-radius:99px;letter-spacing:.1em;text-transform:uppercase}}
.live-pill .live-dot{{width:6px;height:6px;border-radius:50%;background:var(--accent-2);animation:pulse 1.8s ease-in-out infinite}}
.date-pill{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);letter-spacing:.06em;border:1px solid var(--line);padding:5px 12px;border-radius:99px}}
.refresh-btn{{font-family:var(--font-mono);font-size:10px;letter-spacing:.08em;color:var(--accent);background:transparent;border:1px solid rgba(200,169,126,.3);padding:6px 14px;border-radius:99px;cursor:pointer;transition:all var(--t);text-transform:uppercase;display:flex;align-items:center;gap:6px}}
.refresh-btn:hover{{background:rgba(200,169,126,.1);border-color:rgba(200,169,126,.55);transform:translateY(-1px)}}
.spin{{display:inline-block}}.spinning .spin{{animation:rotate .8s linear infinite}}
@keyframes rotate{{to{{transform:rotate(360deg)}}}}
.hero{{max-width:var(--max);margin:0 auto;padding:80px 48px 64px;display:grid;grid-template-columns:1.2fr 1fr;gap:64px;align-items:end;border-bottom:1px solid var(--line)}}
.hero-kicker{{font-family:var(--font-mono);font-size:10px;letter-spacing:.18em;color:var(--accent);text-transform:uppercase;margin-bottom:20px;display:flex;align-items:center;gap:10px;font-weight:500}}
.kicker-dot{{width:6px;height:6px;border-radius:50%;background:var(--accent);animation:pulse 2s ease-in-out infinite}}
.hero h1{{font-family:var(--font-display);font-size:clamp(40px,4.6vw,68px);line-height:1.04;letter-spacing:-.02em;color:var(--text);margin-bottom:24px;font-weight:400}}
.hero h1 em{{font-style:italic;color:var(--accent)}}
.hero-desc{{font-size:15px;color:var(--text-2);line-height:1.7;max-width:480px}}
.hero-stats{{display:flex;flex-direction:column;gap:0;align-self:stretch;justify-content:center}}
.hero-stat-row{{display:flex;justify-content:space-between;align-items:center;padding:18px 0;border-bottom:1px solid var(--line)}}
.hero-stat-row:first-child{{border-top:1px solid var(--line)}}
.hero-stat-left{{display:flex;flex-direction:column;gap:4px}}
.stat-label{{font-family:var(--font-mono);font-size:10px;letter-spacing:.12em;color:var(--text-3);text-transform:uppercase;font-weight:500}}
.stat-trend{{font-family:var(--font-mono);font-size:10px;color:var(--accent-2)}}
.stat-trend.dn{{color:var(--accent-3)}}
.stat-right{{display:flex;align-items:center;gap:14px}}
.stat-value{{font-family:var(--font-display);font-size:32px;color:var(--text);letter-spacing:-.02em;line-height:1}}
.stat-value.sm{{font-size:22px}}
.spark{{height:28px;width:80px}}
.spark path{{fill:none;stroke:var(--accent);stroke-width:1.5}}
.spark.green path{{stroke:var(--accent-2)}}.spark.red path{{stroke:var(--red)}}
.spark .fill{{fill:var(--accent);opacity:.12;stroke:none}}
.spark.green .fill{{fill:var(--accent-2);opacity:.12}}
.alert-banner{{max-width:var(--max);margin:0 auto;display:flex;align-items:center;gap:16px;background:linear-gradient(90deg,rgba(199,91,91,.08),rgba(199,91,91,.02));border-bottom:1px solid rgba(199,91,91,.18);padding:14px 48px}}
.alert-tag{{font-family:var(--font-mono);font-size:9px;letter-spacing:.16em;color:var(--red);border:1px solid rgba(199,91,91,.35);padding:4px 10px;border-radius:99px;text-transform:uppercase;flex-shrink:0;background:rgba(199,91,91,.08);font-weight:500}}
.alert-text{{font-size:13px;color:var(--text-2)}}.alert-text strong{{color:var(--text);font-weight:500}}
.main{{max-width:var(--max);margin:0 auto;display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:0;min-height:calc(100vh - 220px)}}
.content-area{{border-right:1px solid var(--line);padding:0;min-width:0}}
.tabs{{display:flex;border-bottom:1px solid var(--line);overflow-x:auto;scrollbar-width:none;background:rgba(15,17,21,.65);backdrop-filter:blur(8px);position:sticky;top:96px;z-index:90}}
.tabs::-webkit-scrollbar{{display:none}}
.tab-btn{{font-family:var(--font-mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--text-3);background:transparent;border:none;border-bottom:2px solid transparent;padding:18px 22px;cursor:pointer;white-space:nowrap;transition:all var(--t);margin-bottom:-1px;font-weight:500}}
.tab-btn:hover{{color:var(--text-2)}}.tab-btn.active{{color:var(--accent);border-bottom-color:var(--accent)}}
.tab-btn .badge-num{{display:inline-block;font-size:9px;color:var(--text-3);margin-left:6px;font-weight:400}}
.panel{{display:none;padding:36px 44px;animation:fadeUp .35s ease forwards}}
.panel.active{{display:block}}
.panel-section{{margin-bottom:44px}}
.panel-section-title{{font-family:var(--font-mono);font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--text-3);margin-bottom:22px;padding-bottom:12px;border-bottom:1px solid var(--line);font-weight:500;display:flex;justify-content:space-between;align-items:center}}
.section-count{{color:var(--text-2);font-weight:400}}
.insight-card{{background:var(--bg-3);border:1px solid var(--line);border-radius:var(--radius);margin-bottom:12px;overflow:hidden;transition:all var(--t)}}
.insight-card:hover{{border-color:var(--line-2);transform:translateY(-1px);box-shadow:0 4px 24px rgba(0,0,0,.18)}}
.insight-card-head{{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;gap:16px;cursor:pointer}}
.insight-card-title{{font-size:14px;font-weight:500;color:var(--text);line-height:1.4;flex:1}}
.urgency-badge{{font-family:var(--font-mono);font-size:9px;letter-spacing:.12em;text-transform:uppercase;padding:4px 10px;border-radius:99px;flex-shrink:0;font-weight:500}}
.urg-critical{{background:rgba(199,91,91,.14);color:#e07474;border:1px solid rgba(199,91,91,.3)}}
.urg-high{{background:rgba(212,165,116,.14);color:var(--accent-3);border:1px solid rgba(212,165,116,.3)}}
.urg-medium{{background:rgba(200,169,126,.12);color:var(--accent);border:1px solid rgba(200,169,126,.25)}}
.urg-low{{background:rgba(107,142,123,.14);color:var(--accent-2);border:1px solid rgba(107,142,123,.28)}}
.insight-card-body{{padding:0 20px 18px;display:none}}.insight-card-body.open{{display:block}}
.insight-block{{margin-bottom:14px}}
.insight-block-label{{font-family:var(--font-mono);font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--text-3);margin-bottom:5px;font-weight:500}}
.insight-block-text{{font-size:13px;color:var(--text-2);line-height:1.6}}.insight-block-text strong{{color:var(--text);font-weight:500}}
.card-actions{{display:flex;gap:8px;margin-top:16px;padding-top:14px;border-top:1px solid var(--line);flex-wrap:wrap}}
.card-action-btn{{font-family:var(--font-mono);font-size:10px;letter-spacing:.06em;color:var(--accent);background:transparent;border:1px solid rgba(200,169,126,.25);padding:7px 13px;border-radius:99px;cursor:pointer;transition:all var(--t);text-decoration:none;display:inline-flex;align-items:center;gap:4px}}
.card-action-btn:hover{{background:rgba(200,169,126,.1);border-color:rgba(200,169,126,.5);transform:translateY(-1px)}}
.card-action-btn.verify-btn{{color:var(--accent-2);border-color:rgba(107,142,123,.35);background:rgba(107,142,123,.06)}}
.card-action-btn.verify-btn:hover{{background:rgba(107,142,123,.14);border-color:rgba(107,142,123,.6);color:var(--accent-2)}}
.tbd-badge{{font-family:var(--font-mono);font-size:9px;letter-spacing:.12em;color:var(--accent-3);background:rgba(212,165,116,.1);border:1px solid rgba(212,165,116,.28);padding:2px 8px;border-radius:99px;text-transform:uppercase;font-weight:500}}
.event-card.is-tentative{{background:linear-gradient(180deg,var(--bg-3) 0%,rgba(212,165,116,.02) 100%)}}
.event-card.is-tentative .event-name{{opacity:.95}}
.card-tag-row{{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}}
.card-tag{{font-family:var(--font-mono);font-size:9px;letter-spacing:.08em;color:var(--text-3);background:var(--bg-4);padding:4px 9px;border-radius:99px}}
.comp-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.comp-card{{background:var(--bg-3);border:1px solid var(--line);border-radius:var(--radius);padding:18px;transition:all var(--t)}}
.comp-card:hover{{border-color:var(--line-2);transform:translateY(-1px);box-shadow:0 4px 20px rgba(0,0,0,.16)}}
.comp-name{{font-size:14px;font-weight:600;color:var(--text);margin-bottom:6px}}
.comp-desc{{font-size:12px;color:var(--text-2);line-height:1.55;margin-bottom:12px}}
.threat-chip{{font-family:var(--font-mono);font-size:9px;letter-spacing:.1em;padding:3px 9px;border-radius:99px;font-weight:500}}
.action-item{{display:flex;gap:18px;padding:18px 0;border-bottom:1px solid var(--line);align-items:flex-start}}
.action-num{{font-family:var(--font-display);font-size:36px;color:var(--bg-4);line-height:1;flex-shrink:0;width:40px;text-align:center;font-style:italic}}
.action-content{{flex:1}}
.action-title{{font-size:14px;color:var(--text);margin-bottom:6px;font-weight:500}}
.action-desc{{font-size:13px;color:var(--text-2);line-height:1.6}}
.action-meta{{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;align-items:center}}
.action-chip{{font-family:var(--font-mono);font-size:9px;letter-spacing:.07em;color:var(--text-3);border:1px solid var(--line);padding:4px 9px;border-radius:99px}}
.action-cta{{font-family:var(--font-mono);font-size:10px;letter-spacing:.08em;color:var(--accent);background:transparent;border:1px solid rgba(200,169,126,.3);padding:5px 11px;border-radius:99px;cursor:pointer;transition:all var(--t)}}
.action-cta:hover{{background:rgba(200,169,126,.1);transform:translateY(-1px)}}
.events-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.event-card{{position:relative;background:var(--bg-3);border:1px solid var(--line);border-radius:var(--radius);padding:0;overflow:hidden;cursor:pointer;transition:all var(--t)}}
.event-card:hover{{border-color:var(--line-2);transform:translateY(-2px) scale(1.005);box-shadow:0 8px 28px rgba(0,0,0,.22)}}
.event-accent{{position:absolute;top:0;left:0;right:0;height:2px;z-index:2}}
.event-head{{display:flex;justify-content:space-between;gap:14px;padding:18px 20px 14px;align-items:flex-start}}
.event-meta-row{{display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-wrap:wrap}}
.event-sport-chip{{font-family:var(--font-mono);font-size:9px;letter-spacing:.14em;text-transform:uppercase;padding:3px 9px;border-radius:99px;border:1px solid;font-weight:500}}
.event-date{{font-family:var(--font-mono);font-size:10px;color:var(--text-2);letter-spacing:.08em;font-weight:500}}
.event-countdown{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);letter-spacing:.06em}}
.event-name{{font-size:16px;font-weight:600;color:var(--text);line-height:1.3;margin-bottom:4px}}
.event-venue{{font-size:11px;color:var(--text-3);line-height:1.4}}
.hyd-score{{flex-shrink:0;border:1px solid;border-radius:8px;padding:6px 10px;text-align:center;min-width:60px}}
.hyd-score-label{{font-family:var(--font-mono);font-size:7px;letter-spacing:.18em;color:var(--text-3);font-weight:500}}
.hyd-score-num{{font-family:var(--font-display);font-size:24px;line-height:1.1;font-style:italic}}
.event-hover-angle{{max-height:0;overflow:hidden;transition:max-height var(--t),padding var(--t);padding:0 20px;border-top:1px dashed transparent}}
.event-card:hover .event-hover-angle:not(.is-open){{max-height:120px;padding:12px 20px;border-top-color:var(--line)}}
.event-card.expanded .event-hover-angle{{max-height:0;padding:0 20px;border-top-color:transparent}}
.hover-label{{font-family:var(--font-mono);font-size:8px;letter-spacing:.18em;color:var(--accent);text-transform:uppercase;margin-bottom:4px;font-weight:500}}
.hover-text{{font-size:12px;color:var(--text-2);line-height:1.55}}
.event-body{{display:none;padding:14px 20px 18px;border-top:1px solid var(--line);background:rgba(255,255,255,.015)}}
.event-card.expanded .event-body{{display:block}}
.event-block{{margin-bottom:12px}}
.event-block.accent{{background:rgba(200,169,126,.04);border-left:2px solid var(--accent);padding:10px 12px;border-radius:0 4px 4px 0;margin-top:14px}}
.event-block-label{{font-family:var(--font-mono);font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--text-3);margin-bottom:4px;font-weight:500}}
.event-block-text{{font-size:12px;color:var(--text-2);line-height:1.55}}.event-block-text strong{{color:var(--text);font-weight:500}}
.filter-bar{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:24px;padding-bottom:18px;border-bottom:1px solid var(--line)}}
.filter-chip{{font-family:var(--font-mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-3);background:transparent;border:1px solid var(--line);padding:7px 14px;border-radius:99px;cursor:pointer;transition:all var(--t);font-weight:500}}
.filter-chip:hover{{color:var(--text-2);border-color:var(--line-2)}}
.filter-chip.active{{color:var(--accent);border-color:rgba(200,169,126,.5);background:rgba(200,169,126,.08)}}
.entrants-list{{display:flex;flex-direction:column;gap:0;position:relative}}
.entrant-row{{display:grid;grid-template-columns:40px 1fr;gap:18px;position:relative}}
.entrant-row.hidden{{display:none}}
.entrant-timeline{{position:relative;display:flex;flex-direction:column;align-items:center}}
.entrant-dot{{width:11px;height:11px;border-radius:50%;margin-top:24px;border:2px solid var(--bg);box-shadow:0 0 0 1px var(--line)}}
.entrant-line{{flex:1;width:1px;background:var(--line);margin-top:4px;margin-bottom:0}}
.entrant-row:last-child .entrant-line{{display:none}}
.entrant-card{{background:var(--bg-3);border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;margin-bottom:14px;cursor:pointer;transition:all var(--t)}}
.entrant-card:hover{{border-color:var(--line-2);transform:translateY(-1px);box-shadow:0 4px 20px rgba(0,0,0,.16)}}
.entrant-head{{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:10px}}
.entrant-meta-row{{display:flex;gap:8px;align-items:center;margin-bottom:6px;flex-wrap:wrap}}
.entrant-date{{font-family:var(--font-mono);font-size:10px;color:var(--text-2);letter-spacing:.08em;font-weight:500}}
.entrant-days{{font-family:var(--font-mono);font-size:10px;color:var(--text-3)}}
.threat-pill{{font-family:var(--font-mono);font-size:9px;letter-spacing:.12em;text-transform:uppercase;padding:3px 9px;border-radius:99px;font-weight:500}}
.entrant-brand{{font-size:17px;font-weight:600;color:var(--text);line-height:1.25;margin-bottom:3px}}
.entrant-parent{{font-size:11px;color:var(--text-3);line-height:1.45}}
.entrant-pricing{{flex-shrink:0;text-align:right}}
.entrant-mrp{{font-family:var(--font-mono);font-size:11px;color:var(--accent);font-weight:500}}
.entrant-pser{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);margin-top:2px}}
.entrant-summary{{font-size:13px;color:var(--text-2);line-height:1.6;margin-top:6px}}
.entrant-body{{display:none;margin-top:14px;padding-top:14px;border-top:1px solid var(--line)}}
.entrant-card.expanded .entrant-body{{display:block}}
.entrant-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}}
.entrant-block{{background:var(--bg-2);border:1px solid var(--line);border-radius:8px;padding:10px 12px}}
.entrant-block.accent{{background:rgba(200,169,126,.06);border-color:rgba(200,169,126,.18);grid-column:1/-1}}
.entrant-block-label{{font-family:var(--font-mono);font-size:8px;letter-spacing:.18em;text-transform:uppercase;color:var(--text-3);margin-bottom:5px;font-weight:500}}
.entrant-block-text{{font-size:12px;color:var(--text-2);line-height:1.55}}.entrant-block-text strong{{color:var(--text);font-weight:500}}
/* RADAR */
.radar-section{{background:linear-gradient(180deg,rgba(199,91,91,.04) 0%,transparent 100%);border:1px solid rgba(199,91,91,.16);border-radius:var(--radius);padding:18px 20px;margin-bottom:32px}}
.radar-banner{{display:flex;align-items:center;gap:10px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px dashed rgba(199,91,91,.2)}}
.radar-icon{{font-family:var(--font-mono);font-size:10px;letter-spacing:.16em;color:var(--red);background:rgba(199,91,91,.1);border:1px solid rgba(199,91,91,.3);padding:4px 10px;border-radius:99px;text-transform:uppercase;font-weight:500}}
.radar-tagline{{font-size:12px;color:var(--text-2)}}
.radar-tagline strong{{color:var(--text);font-weight:500}}
.radar-card{{background:var(--bg-3);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin-bottom:10px;transition:all var(--t)}}
.radar-card:hover{{border-color:var(--line-2);transform:translateY(-1px)}}
.radar-card-head{{margin-bottom:8px}}
.radar-meta{{display:flex;gap:8px;align-items:center;margin-bottom:6px;flex-wrap:wrap}}
.radar-unverified{{font-family:var(--font-mono);font-size:9px;letter-spacing:.12em;color:var(--accent-3);background:rgba(212,165,116,.1);border:1px solid rgba(212,165,116,.28);padding:3px 8px;border-radius:99px;text-transform:uppercase;font-weight:500}}
.radar-days{{font-family:var(--font-mono);font-size:10px;color:var(--text-3)}}
.radar-brand{{font-size:15px;font-weight:600;color:var(--text)}}
.radar-summary{{font-size:13px;color:var(--text-2);line-height:1.55;margin-bottom:10px}}
.radar-actions{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding-top:10px;border-top:1px solid var(--line)}}
.radar-source-hint{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);letter-spacing:.04em}}
.radar-source-hint .hint-label{{color:var(--text-2)}}
/* PRICING */
.price-grid{{background:var(--bg-3);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;margin-bottom:18px}}
.price-row{{display:grid;grid-template-columns:130px 1fr 120px 110px 150px;gap:0;align-items:center;border-bottom:1px solid var(--line);transition:background var(--t)}}
.price-row:last-child{{border-bottom:none}}
.price-row:hover{{background:var(--bg-4)}}
.price-row.price-header{{background:var(--bg-2);border-bottom:1px solid var(--line-2)}}
.price-row.price-header .price-cell{{font-family:var(--font-mono);font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--text-3);padding:12px 16px;font-weight:500}}
.price-row.price-osmo{{background:linear-gradient(90deg,rgba(200,169,126,.07) 0%,rgba(200,169,126,.02) 100%);border-left:3px solid var(--accent)}}
.price-row.price-osmo:hover{{background:linear-gradient(90deg,rgba(200,169,126,.12) 0%,rgba(200,169,126,.04) 100%)}}
.price-cell{{padding:16px;font-size:13px;color:var(--text-2);min-width:0}}
.price-brand{{font-family:var(--font-mono);font-size:11px;letter-spacing:.08em;color:var(--text);text-transform:uppercase;font-weight:600;display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.price-osmo .price-brand{{color:var(--accent)}}
.price-brand-tag{{font-family:var(--font-mono);font-size:8px;letter-spacing:.14em;background:var(--accent);color:#0F1115;padding:3px 7px;border-radius:99px;font-weight:600}}
.price-sku-name{{font-size:13px;color:var(--text);line-height:1.4;margin-bottom:4px;font-weight:500}}
.price-pack{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);letter-spacing:.04em}}
.price-mrp-val{{font-family:var(--font-display);font-size:24px;color:var(--text);letter-spacing:-.01em;line-height:1;font-style:italic}}
.price-osmo .price-mrp-val{{color:var(--accent)}}
.price-mrp-sub{{display:flex;gap:6px;align-items:center;margin-top:5px;flex-wrap:wrap}}
.price-mrp-strike{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);text-decoration:line-through}}
.price-off{{font-family:var(--font-mono);font-size:9px;color:var(--accent-2);background:rgba(107,142,123,.12);padding:2px 7px;border-radius:99px;letter-spacing:.04em;font-weight:500;border:1px solid rgba(107,142,123,.25)}}
.price-perserve-val{{font-family:var(--font-display);font-size:22px;color:var(--text);line-height:1;font-style:italic}}
.price-osmo .price-perserve-val{{color:var(--accent-2)}}
.price-perserve-lbl{{font-family:var(--font-mono);font-size:9px;color:var(--text-3);letter-spacing:.1em;margin-top:4px;text-transform:uppercase}}
.price-link{{font-family:var(--font-mono);font-size:10px;color:var(--accent);text-decoration:none;letter-spacing:.04em;border:1px solid rgba(200,169,126,.3);padding:7px 12px;border-radius:99px;display:inline-block;transition:all var(--t);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}}
.price-link:hover{{background:rgba(200,169,126,.1);border-color:rgba(200,169,126,.55);transform:translateY(-1px)}}
.price-takeaway{{font-size:13px;color:var(--text-2);line-height:1.65;padding:16px 18px;background:linear-gradient(90deg,rgba(200,169,126,.06),rgba(200,169,126,.01));border-left:3px solid var(--accent);border-radius:0 var(--radius) var(--radius) 0;margin-top:4px}}
.price-takeaway strong{{color:var(--text);font-weight:500}}
.price-disclaimer{{font-family:var(--font-mono);font-size:9px;color:var(--text-3);letter-spacing:.06em;margin-top:12px;text-align:right}}
.ai-fetch-btn{{font-family:var(--font-mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);background:var(--bg-3);border:1px solid var(--line-2);padding:11px 22px;border-radius:99px;cursor:pointer;transition:all var(--t);display:flex;align-items:center;gap:8px;width:100%;justify-content:center;font-weight:500}}
.ai-fetch-btn:hover{{background:var(--bg-4);border-color:var(--accent);color:var(--accent);transform:translateY(-1px)}}
.ai-output{{margin-top:16px}}
.sk{{background:linear-gradient(90deg,var(--bg-3) 0%,var(--bg-4) 50%,var(--bg-3) 100%);background-size:200% 100%;border-radius:8px;animation:shimmer 1.6s infinite linear}}
@keyframes shimmer{{0%{{background-position:200% 0}}100%{{background-position:-200% 0}}}}
.sk-card{{height:80px;margin-bottom:10px}}
.sidebar{{padding:0;min-width:0}}
.sidebar-block{{padding:28px 24px;border-bottom:1px solid var(--line)}}
.sidebar-title{{font-family:var(--font-mono);font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--text-3);margin-bottom:18px;font-weight:500}}
.heat-row{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}
.heat-label{{font-size:12px;color:var(--text-2);flex:1}}
.heat-bar-wrap{{flex:1;background:var(--bg-3);border-radius:99px;height:5px;overflow:hidden}}
.heat-bar{{height:5px;border-radius:99px;transition:width 1s cubic-bezier(.22,.61,.36,1)}}
.heat-val{{font-family:var(--font-mono);font-size:11px;color:var(--text-3);min-width:28px;text-align:right;font-weight:500}}
.cal-item{{display:flex;align-items:flex-start;gap:12px;margin-bottom:14px}}
.cal-date{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);min-width:36px;padding-top:2px;font-weight:500;letter-spacing:.06em}}
.cal-dot{{width:7px;height:7px;border-radius:50%;margin-top:5px;flex-shrink:0;box-shadow:0 0 0 1px rgba(255,255,255,.05)}}
.cal-text{{font-size:12px;color:var(--text-2);line-height:1.5}}.cal-text strong{{color:var(--text);font-weight:500}}
footer{{max-width:var(--max);margin:0 auto;border-top:1px solid var(--line);padding:24px 48px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}}
.footer-txt{{font-family:var(--font-mono);font-size:10px;color:var(--text-3);letter-spacing:.06em}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.fade-in{{animation:fadeUp .55s ease forwards;opacity:0}}
.delay-1{{animation-delay:.08s}}.delay-2{{animation-delay:.16s}}.delay-3{{animation-delay:.24s}}.delay-4{{animation-delay:.32s}}
@media(max-width:1100px){{
  .events-grid{{grid-template-columns:1fr}}.comp-grid{{grid-template-columns:1fr}}
  .hero{{padding:60px 32px 48px;gap:40px}}
}}
@media(max-width:900px){{
  nav{{padding:14px 20px;flex-wrap:wrap;gap:12px}}.nav-links{{display:none}}
  .hero{{grid-template-columns:1fr;padding:40px 20px;gap:32px}}
  .main{{grid-template-columns:1fr}}
  .content-area{{border-right:none;border-bottom:1px solid var(--line)}}
  .panel{{padding:24px 20px}}.alert-banner{{padding:12px 20px}}
  .entrant-grid{{grid-template-columns:1fr}}.tabs{{top:32px}}
  .price-row{{grid-template-columns:1fr 1fr;gap:6px;padding:14px 6px}}
  .price-row.price-header{{display:none}}
  .price-cell{{padding:6px 14px}}
  .price-cell.price-brand{{grid-column:1 / -1;border-bottom:1px dashed var(--line);padding-bottom:10px;margin-bottom:4px}}
  .price-cell.price-sku{{grid-column:1 / -1}}
  .price-cell.price-link-cell{{grid-column:1 / -1;margin-top:6px}}
  footer{{flex-direction:column;align-items:flex-start;padding:18px 20px}}
}}
</style>
</head>
<body>
<div class="ticker-wrap">
  <div class="ticker-label"><span class="pulse"></span>LIVE</div>
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
    <li><a href="#" onclick="switchTab('india',document.querySelectorAll('.tab-btn')[0]);return false">Intelligence</a></li>
    <li><a href="#" onclick="switchTab('events',document.querySelectorAll('.tab-btn')[1]);return false">Events</a></li>
    <li><a href="#" onclick="switchTab('entrants',document.querySelectorAll('.tab-btn')[2]);return false">Launches</a></li>
    <li><a href="#" onclick="switchTab('competitors',document.querySelectorAll('.tab-btn')[3]);return false">Competitors</a></li>
    <li><a href="#" onclick="switchTab('actions',document.querySelectorAll('.tab-btn')[5]);return false">Actions</a></li>
  </ul>
  <div class="nav-right">
    <span class="live-pill"><span class="live-dot"></span>Live</span>
    <span class="date-pill">{TODAY}</span>
    <button class="refresh-btn" onclick="location.reload()"><span class="spin">↻</span> Refresh</button>
  </div>
</nav>
<div class="alert-banner">
  <span class="alert-tag">⚠ Alert</span>
  <span class="alert-text"><strong>Daily briefing updated:</strong> {TODAY} · {RADAR_COUNT} new signals on Radar · {EVENTS_COUNT} sport events tracked · {ENTRANTS_COUNT} verified launches in database.</span>
</div>
<section class="hero">
  <div class="fade-in">
    <div class="hero-kicker"><span class="kicker-dot"></span> Daily intelligence briefing</div>
    <h1>What's moving the <em>electrolyte</em> category in India today.</h1>
    <p class="hero-desc">Real-time market signals, India incidents, combat &amp; hybrid sport events, new entrant launches, and actionable marketing briefs — built for the Osmo team to move fast.</p>
  </div>
  <div class="hero-stats fade-in delay-2">
    <div class="hero-stat-row">
      <div class="hero-stat-left"><span class="stat-label">India market 2026</span><span class="stat-trend">↑ 13.9% CAGR</span></div>
      <div class="stat-right"><svg class="spark green" viewBox="0 0 80 28"><path class="fill" d="M0,22 L10,20 L20,17 L30,15 L40,10 L50,8 L60,5 L70,4 L80,2 L80,28 L0,28 Z"/><path d="M0,22 L10,20 L20,17 L30,15 L40,10 L50,8 L60,5 L70,4 L80,2"/></svg><span class="stat-value">$81M</span></div>
    </div>
    <div class="hero-stat-row">
      <div class="hero-stat-left"><span class="stat-label">Global category</span><span class="stat-trend">↑ 8.4% CAGR</span></div>
      <div class="stat-right"><svg class="spark" viewBox="0 0 80 28"><path class="fill" d="M0,18 L10,16 L20,14 L30,15 L40,12 L50,10 L60,8 L70,6 L80,5 L80,28 L0,28 Z"/><path d="M0,18 L10,16 L20,14 L30,15 L40,12 L50,10 L60,8 L70,6 L80,5"/></svg><span class="stat-value">$43B</span></div>
    </div>
    <div class="hero-stat-row">
      <div class="hero-stat-left"><span class="stat-label">Combat / hybrid events tracked</span><span class="stat-trend">{EVENTS_COUNT} live</span></div>
      <div class="stat-right"><svg class="spark" viewBox="0 0 80 28"><path class="fill" d="M0,20 L8,18 L16,16 L24,14 L32,12 L40,10 L48,11 L56,8 L64,6 L72,5 L80,4 L80,28 L0,28 Z"/><path d="M0,20 L8,18 L16,16 L24,14 L32,12 L40,10 L48,11 L56,8 L64,6 L72,5 L80,4"/></svg><span class="stat-value sm">{EVENTS_COUNT}</span></div>
    </div>
    <div class="hero-stat-row">
      <div class="hero-stat-left"><span class="stat-label">New launches · 90 days</span><span class="stat-trend dn">{ENTRANTS_COUNT} verified</span></div>
      <div class="stat-right"><svg class="spark red" viewBox="0 0 80 28"><path class="fill" d="M0,24 L10,22 L20,18 L30,15 L40,13 L50,9 L60,7 L70,5 L80,3 L80,28 L0,28 Z"/><path d="M0,24 L10,22 L20,18 L30,15 L40,13 L50,9 L60,7 L70,5 L80,3"/></svg><span class="stat-value sm">{ENTRANTS_COUNT}</span></div>
    </div>
  </div>
</section>
<div class="main">
  <div class="content-area fade-in delay-3">
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('india', this)">India Moments</button>
      <button class="tab-btn" onclick="switchTab('events', this)">Events <span class="badge-num">{EVENTS_COUNT}</span></button>
      <button class="tab-btn" onclick="switchTab('entrants', this)">New Entrants <span class="badge-num">{ENTRANTS_COUNT}</span></button>
      <button class="tab-btn" onclick="switchTab('competitors', this)">Competitors</button>
      <button class="tab-btn" onclick="switchTab('global', this)">Global Trends</button>
      <button class="tab-btn" onclick="switchTab('actions', this)">This Week</button>
    </div>
    <div class="panel active" id="panel-india">
      {INDIA_HTML}
      <div style="margin-top:24px">
        <div class="panel-section-title">Live search · today's fresh India incidents</div>
        <div class="ai-output" id="india-ai-output"></div>
        <button class="ai-fetch-btn" onclick="fetchLive('india')">↻ Search India incidents now</button>
      </div>
    </div>
    <div class="panel" id="panel-events">
      <div class="panel-section">
        <div class="panel-section-title">
          Combat &amp; hybrid sports calendar
          <span class="section-count">{EVENTS_COUNT} events tracked</span>
        </div>
        <div class="filter-bar" id="events-filter">
          <button class="filter-chip active" data-filter="all">All</button>
          <button class="filter-chip" data-filter="combat">Combat</button>
          <button class="filter-chip" data-filter="hybrid">Hybrid</button>
        </div>
        <div class="events-grid" id="events-grid">{EVENTS_HTML}</div>
      </div>
    </div>
    <div class="panel" id="panel-entrants">
      <div class="radar-section">
        <div class="radar-banner">
          <span class="radar-icon">⚡ Radar · flagged this week</span>
          <span class="radar-tagline"><strong>AI-flagged signals from the last 7-14 days.</strong> Unverified — review and promote to the verified list below when confirmed.</span>
        </div>
        {RADAR_HTML}
      </div>
      <div class="panel-section">
        <div class="panel-section-title">
          Verified launches
          <span class="section-count">{ENTRANTS_COUNT} confirmed · last 90 days</span>
        </div>
        <div class="filter-bar" id="entrants-filter">
          <button class="filter-chip active" data-filter="all">All</button>
          <button class="filter-chip" data-filter="week">This Week</button>
          <button class="filter-chip" data-filter="month">This Month</button>
          <button class="filter-chip" data-filter="disruptor">Disruptor</button>
          <button class="filter-chip" data-filter="high-alert">High Alert</button>
          <button class="filter-chip" data-filter="monitor">Monitor</button>
        </div>
        <div class="entrants-list" id="entrants-list">{ENTRANTS_HTML}</div>
      </div>
    </div>
    <div class="panel" id="panel-competitors">
      <div class="panel-section">
        <div class="panel-section-title">India competitor landscape</div>
        <div class="comp-grid">{LANDSCAPE_HTML}</div>
      </div>
      <div class="panel-section">
        <div class="panel-section-title">Competitor pricing — matched SKUs<span class="section-count">verified May 2026 · 6 brands</span></div>
        {PRICING_HTML}
      </div>
      <div class="panel-section">
        <div class="panel-section-title">AI competitor intelligence · new moves this week</div>
        {COMPETITOR_HTML}
        <div style="margin-top:16px">
          <div class="ai-output" id="competitors-ai-output"></div>
          <button class="ai-fetch-btn" onclick="fetchLive('competitors')">↻ Search competitor news now</button>
        </div>
      </div>
    </div>
    <div class="panel" id="panel-global">
      <div class="panel-section">
        <div class="panel-section-title">Global category intelligence</div>
        {GLOBAL_HTML}
      </div>
      <div style="margin-top:24px">
        <div class="panel-section-title">Live search · fresh global trends</div>
        <div class="ai-output" id="global-ai-output"></div>
        <button class="ai-fetch-btn" onclick="fetchLive('global')">↻ Search global trends now</button>
      </div>
    </div>
    <div class="panel" id="panel-actions">
      <div class="panel-section">
        <div class="panel-section-title">This week's prioritised actions · {TODAY}</div>
        {ACTIONS_HTML}
      </div>
      <div class="panel-section">
        <div class="panel-section-title">Generate custom brief</div>
        <div class="ai-output" id="actions-ai-output"></div>
        <button class="ai-fetch-btn" onclick="brief('weekly_brief')">↗ Generate full weekly brief in Claude</button>
      </div>
    </div>
  </div>
  <aside class="sidebar fade-in delay-4">
    <div class="sidebar-block">
      <div class="sidebar-title">Opportunity heat map</div>
      {HEATMAP_HTML}
    </div>
    <div class="sidebar-block">
      <div class="sidebar-title">Upcoming triggers</div>
      {TRIGGERS_HTML}
    </div>
    <div class="sidebar-block">
      <div class="sidebar-title">Quick actions</div>
      <div style="display:flex;flex-direction:column;gap:8px">
        <button class="ai-fetch-btn" style="font-size:10px;padding:10px 14px" onclick="brief('weekly_brief')">Generate full weekly brief →</button>
        <button class="ai-fetch-btn" style="font-size:10px;padding:10px 14px" onclick="brief('events_brief')">90-day events activation plan →</button>
        <button class="ai-fetch-btn" style="font-size:10px;padding:10px 14px" onclick="brief('entrants_brief')">Competitor response plan →</button>
        <button class="ai-fetch-btn" style="font-size:10px;padding:10px 14px" onclick="brief('heatwave_carousel')">Heatwave social copy →</button>
      </div>
    </div>
  </aside>
</div>
<footer>
  <div class="footer-txt">Electrolyte Intelligence · Internal use · Auto-refreshed daily 07:00 IST</div>
  <div class="footer-txt">Generated {TODAY} · {MODEL.upper()}</div>
</footer>
<script>
  const CLAUDE_API = 'https://api.anthropic.com/v1/messages';
  {BRIEF_JS}
  function switchTab(tab, btn) {{
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    if (btn) btn.classList.add('active');
    const panel = document.getElementById('panel-' + tab);
    if (panel) panel.classList.add('active');
  }}
  function toggleCard(head) {{ head.nextElementSibling.classList.toggle('open'); }}
  function toggleEvent(card) {{ card.classList.toggle('expanded'); }}
  function toggleEntrant(card) {{ card.classList.toggle('expanded'); }}
  function brief(type) {{
    const msg = BRIEF_PROMPTS[type] || 'Give me a detailed marketing brief for Osmo electrolytes India.';
    window.open('https://claude.ai/new?q=' + encodeURIComponent(msg), '_blank');
  }}
  document.querySelectorAll('#events-filter .filter-chip').forEach(chip => {{
    chip.addEventListener('click', () => {{
      document.querySelectorAll('#events-filter .filter-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const f = chip.dataset.filter;
      document.querySelectorAll('#events-grid .event-card').forEach(card => {{
        const sportType = card.dataset.sportType;
        let show = true;
        if (f === 'combat') show = (sportType === 'combat');
        else if (f === 'hybrid') show = (sportType === 'hybrid');
        card.style.display = show ? '' : 'none';
      }});
    }});
  }});
  document.querySelectorAll('#entrants-filter .filter-chip').forEach(chip => {{
    chip.addEventListener('click', () => {{
      document.querySelectorAll('#entrants-filter .filter-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const f = chip.dataset.filter;
      document.querySelectorAll('#entrants-list .entrant-row').forEach(row => {{
        const threat = row.dataset.threat;
        const bucket = row.dataset.bucket;
        let show = true;
        if (f === 'week') show = (bucket === 'week');
        else if (f === 'month') show = (bucket === 'week' || bucket === 'month');
        else if (f === 'disruptor') show = (threat === 'disruptor');
        else if (f === 'high-alert') show = (threat === 'high-alert');
        else if (f === 'monitor') show = (threat === 'monitor');
        row.classList.toggle('hidden', !show);
      }});
    }});
  }});
  const SYS = 'You are an electrolyte market intelligence analyst for Osmo India. Return a JSON array of 3 insight objects. Each: title, urgency, what, angle, tag. ONLY valid JSON.';
  async function fetchLive(section) {{
    const el = document.getElementById(section + '-ai-output');
    el.innerHTML = '<div class="sk sk-card"></div><div class="sk sk-card" style="height:70px"></div>';
    const prompts = {{
      india: 'India 2026 heatwave + IPL ongoing. Generate 3 fresh India marketing moments for Osmo right now.',
      global: 'Global electrolyte market $43B, India 13.9% CAGR. Generate 3 global trend insights for Osmo.',
      competitors: 'India 2026 electrolyte launches: hydRo365, Liquid I.V. India, MuscleBlaze, Protyze. Generate 3 competitor insights — what should Osmo do?'
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
      el.innerHTML = '<div style="font-family:var(--font-mono);font-size:10px;color:var(--text-3);padding:10px 0">Live search unavailable — needs API key in browser context.</div>';
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
print(f"   India insights: {len(india_items)} · Global: {len(global_items)} · Competitor AI: {len(competitor_items)}")
print(f"   Actions: {len(actions)} · Heatmap: {len(heatmap)} · Triggers: {len(triggers)}")
print(f"   Radar (new launches): {len(radar_items)}")
print(f"   Curated: {len(EVENTS_DATA)} events, {len(ENTRANTS_DATA)} entrants, {len(PRICING_DATA)} pricing rows")
