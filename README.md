# Electrolyte Intelligence — Daily Briefing Site

A self-updating market intelligence website for the Osmo team.
Refreshes automatically every morning at 07:00 IST with fresh AI-generated insights.

---

## What's in this repo

| File | What it does |
|------|-------------|
| `index.html` | The live website (auto-generated, don't edit manually) |
| `generate.py` | Calls Claude API and regenerates `index.html` with fresh content |
| `requirements.txt` | Python dependency (just `anthropic`) |
| `netlify.toml` | Netlify deploy config (no setup needed) |
| `.github/workflows/daily-refresh.yml` | GitHub Action — runs `generate.py` every morning at 07:00 IST |

---

## One-time setup (takes ~15 minutes total)

### Step 1 — Push to GitHub (5 min)

1. Go to **github.com** → click **New repository**
2. Name it: `electrolyte-intelligence`
3. Set to **Private** (recommended for internal tool)
4. Click **Create repository**
5. On your computer, open Terminal in this folder and run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/electrolyte-intelligence.git
   git push -u origin main
   ```
   Replace `YOUR_USERNAME` with your GitHub username.

### Step 2 — Add your Anthropic API key to GitHub (2 min)

1. Go to your repo on GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: your Anthropic API key (starts with `sk-ant-...`)
5. Click **Add secret**

Get your API key at: https://console.anthropic.com/settings/keys

### Step 3 — Connect Netlify (5 min)

1. Go to **netlify.com** → Sign up free (use GitHub login)
2. Click **Add new site** → **Import an existing project**
3. Choose **GitHub** → select `electrolyte-intelligence` repo
4. Build settings: leave everything blank (the `netlify.toml` handles it)
5. Click **Deploy site**

You'll get a URL like `https://electrolyte-intelligence.netlify.app` in ~30 seconds.

**Optional — custom domain:** In Netlify → Site settings → Domain management → Add custom domain.

### Step 4 — Enable auto-deploy on push (automatic)

Netlify auto-detects GitHub pushes. Every time the GitHub Action commits a new `index.html`,
Netlify redeploys in ~20 seconds. Nothing to configure.

---

## How it works after setup

```
Every day at 07:00 IST
        ↓
GitHub Action runs generate.py
        ↓
generate.py calls Claude API → fetches fresh India moments,
global trends, competitor intelligence, weekly actions
        ↓
Writes new index.html with today's content baked in
        ↓
GitHub Action commits + pushes index.html
        ↓
Netlify detects push → redeploys in ~20 seconds
        ↓
Your team opens the URL → sees today's briefing
```

---

## Manual refresh

To regenerate the page manually at any time:

**Option A — GitHub UI (easiest):**
1. Go to your repo → **Actions** tab
2. Click **Daily Intelligence Refresh**
3. Click **Run workflow** → **Run workflow**

**Option B — local:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python generate.py
```
Then commit and push the updated `index.html`.

---

## Changing the refresh time

Edit `.github/workflows/daily-refresh.yml`:
```yaml
- cron: '30 1 * * *'   # 01:30 UTC = 07:00 IST
```
Use https://crontab.guru to find your preferred UTC time.

---

## Changing the AI model

Edit the top of `generate.py`:
```python
MODEL = "claude-opus-4-5"   # change to any Claude model
```
Available models: `claude-opus-4-5`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`

---

## Estimated monthly cost

The script makes ~6 Claude API calls per run, each ~500–800 tokens.
At daily frequency: roughly **$1–3/month** depending on model choice.
- Haiku: ~$0.10/month
- Sonnet: ~$0.80/month
- Opus: ~$2.50/month

---

## Share the link

Once Netlify is connected, share the URL with your team.
Bookmark it. Add it to your Notion workspace. Pin it in Slack.
The page is always up-to-date — just open and read.
