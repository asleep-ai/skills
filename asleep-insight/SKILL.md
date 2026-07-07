---
name: asleep-insight
version: 1.3.0
description: AI-powered sleep insights for SleepHub app users
homepage: https://asleep.ai
---

# Asleep Sleep Insight

AI-powered sleep insights for SleepHub app users.

## ⚡ Quick Start: Heartbeat Setup

**This skill requires periodic checking.** After installing, add this to your `HEARTBEAT.md`:

### Add to HEARTBEAT.md

```markdown
### Step 0: Sleep Check (REQUIRED)

Every heartbeat, run:
```bash
python3 ~/.openclaw/workspace/skills/asleep-insight/scripts/insight.py --check-new
```

| Output | Action |
|--------|--------|
| JSON (new session) | Analyze and report with interpretation |
| No output | Silent — don't mention |

**You MUST run this on every heartbeat.** Do not skip heartbeats or limit to
specific times of day -- users have irregular sleep schedules and take naps.

When new session detected:
1. Report sleep score & key metrics
2. Explain WHY it was good/bad
3. Mention weekly trend
4. Give improvement advice if needed
```

### What to Report

| Output exists | No output |
|---------------|-----------|
| Score + metrics | Skip silently |
| Why good/bad (root cause) | Don't mention "no new session" |
| Weekly trend | |
| Advice if needed | |

---

## Installation

### Skill Files

| File | URL |
|------|-----|
| **SKILL.md** | `https://raw.githubusercontent.com/asleep-ai/skills/main/asleep-insight/SKILL.md` |
| **insight.py** | `https://raw.githubusercontent.com/asleep-ai/skills/main/asleep-insight/scripts/insight.py` |

**Install locally:**
```bash
mkdir -p ~/.openclaw/workspace/skills/asleep-insight/scripts
curl -sL https://raw.githubusercontent.com/asleep-ai/skills/main/asleep-insight/SKILL.md \
  -o ~/.openclaw/workspace/skills/asleep-insight/SKILL.md
curl -sL https://raw.githubusercontent.com/asleep-ai/skills/main/asleep-insight/scripts/insight.py \
  -o ~/.openclaw/workspace/skills/asleep-insight/scripts/insight.py
```

### Credentials Setup

Get your credentials from the SleepHub app, then run:

Before setup, inspect the user's original setup request for a breathing
activation marker. Enable breathing metrics only when the request contains a
line whose trimmed contents are exactly `JMY`. Do not use substring matching;
`JMY` embedded inside credentials, tokens, prose, or another word does not
count.

```bash
python scripts/insight.py setup \
  --user-id=YOUR_USER_ID \
  --access-token=YOUR_ACCESS_TOKEN \
  --refresh-token=YOUR_REFRESH_TOKEN
```

Credentials are saved to `~/.config/asleep/user.json`

If the original setup request contains the standalone `JMY` line, persistently
enable breathing metrics during the same setup:

```bash
python scripts/insight.py setup \
  --user-id=YOUR_USER_ID \
  --access-token=YOUR_ACCESS_TOKEN \
  --refresh-token=YOUR_REFRESH_TOKEN \
  --enable-breathing
```

This stores `breathing_enabled: true` in `~/.config/asleep/user.json`.
After that, normal commands such as `python scripts/insight.py` and
`python scripts/insight.py --check-new` include breathing metrics
automatically.

### Breathing Metrics Activation

By default, the skill returns the standard sleep insight metrics only. Breathing
metrics are a persistent setup-time option activated only by the standalone
`JMY` marker in the user's setup request. The marker itself is not stored.


### Token Notes

- **Access tokens expire after 10 hours**
- If you get `403: token invalid`, the script will **auto-refresh** using your refresh token
- Refresh tokens are valid for 14 days — use the skill at least once every 2 weeks to stay logged in
- If both tokens expire, ask your user for new credentials from the app

---

## Usage

```bash
# Get sleep insights (default: 7 days)
python scripts/insight.py

# Check for new sessions only (for heartbeat/cron)
python scripts/insight.py --check-new

# Custom date range
python scripts/insight.py --days=14

# View generation history
python scripts/insight.py --history
```

---

## Output Format

```json
{
  "wake_dates": ["2026-02-25 (Tue)", "2026-02-26 (Wed)"],
  "sleep_onset_time": {
    "daily": ["23:30:00", "22:45:00"],
    "month_avg": "23:08:24",
    "trend": "getting earlier"
  },
  "total_sleep_time": {
    "daily": ["7 hrs 11 mins", "7 hrs 28 mins"],
    "month_avg": "7 hrs 20 mins",
    "trend": "increasing"
  },
  "sleep_score": {
    "daily": [89, 92],
    "trend": "increasing"
  },
  "breathing_index": {
    "daily": [2.4, 3.1],
    "month_avg": 3.2,
    "trend": "increasing"
  },
  "breathing_pattern": {
    "daily": ["STABLE_BREATH", "STABLE_BREATH"]
  }
}
```

## Metrics

| Metric | Description |
|--------|-------------|
| `sleep_onset_time` | Time fell asleep |
| `wake_up_time` | Time woke up |
| `sleep_onset_latency` | Time to fall asleep |
| `total_sleep_time` | Total sleep duration |
| `deep_sleep_time` | Deep sleep duration |
| `snoring_time` | Snoring duration |
| `sleep_efficiency` | Sleep efficiency % |
| `rem_ratio` | REM sleep ratio % |
| `sleep_score` | Overall sleep score (0-100) |

### Optional Breathing Metrics

These fields are included only when setup detected a standalone `JMY` marker
and stored `breathing_enabled: true`.

| Metric | Description |
|--------|-------------|
| `time_in_stable_breath` | Stable breathing duration |
| `time_in_unstable_breath` | Unstable breathing duration |
| `stable_breath_ratio` | Stable breathing ratio % |
| `unstable_breath_ratio` | Unstable breathing ratio % |
| `breathing_index` | Estimated AHI-style breathing index |
| `breathing_pattern` | Breathing stability category |
| `unstable_breath_count` | Count of unstable breathing clusters |

## Trends

- `increasing` / `decreasing` — numeric values
- `getting earlier` / `getting later` — time values
- `no trend` — stable or insufficient data

---

## Agent Guidelines

### Score Interpretation

| Score | Rating | What to Say |
|-------|--------|-------------|
| 90-100 | Excellent | 🔥 Great night! Keep this pattern |
| 80-89 | Good | ✅ Solid sleep, good condition |
| 70-79 | Fair | ⚠️ Okay but room for improvement |
| 60-69 | Poor | 😴 Fatigue risk, try sleeping earlier |
| <60 | Very Poor | 🚨 Serious concern, review habits |

### Root Cause Analysis

Always explain **WHY** the score is good or bad:

| Factor | Good Sign | Caution | Warning Sign |
|--------|-----------|---------|--------------|
| **Bedtime** | Consistent, before 1am | 1-2am | >2am or irregular |
| **Total Sleep** | 6-8 hours | — | <6h or >8h |
| **Sleep Efficiency** | ≥85% | 75-85% | <75% |
| **Sleep Latency** | ≤15 mins | 15-30 mins | >30 mins |
| **Deep Sleep** | ≥15% of TST | — | <15% of TST |
| **REM Ratio** | 20-25% | 15-20% or 25-30% | <15% or >30% |

**Example reasoning:**
- Score 77, total sleep 5h 47m → "Short on sleep (under 6h)"
- Score 88, efficiency 96% → "High efficiency, slept soundly!"
- Latency 3 mins → "Fell asleep almost instantly"

### Weekly Trend Patterns

| Pattern | Detection | Response |
|---------|-----------|----------|
| **Improving** | 3+ days rising | "Getting better! 🔥" |
| **Declining** | 3+ days falling | "Watch out for fatigue ⚠️" |
| **Volatile** | Swings ±15+ | "Irregular sleep pattern" |
| **Stable** | Consistent | "Maintaining steady pattern" |

Always mention where today fits: "Week: 83→77→73→88→**77**"

### Example Outputs

**Good night (Score 88):**
```
🌙 Sleep Score: 88 ✅

Bedtime 00:30, Wake 08:15
Total 7h 30m, Efficiency 96%

Highlights: High efficiency + 1h 20m deep sleep!
Week: 77→73→88 (improving 🔥)

💤 Keep this up!
```

**Concerning night (Score 67):**
```
🌙 Sleep Score: 67 ⚠️

Bedtime 03:15, Wake 09:00
Total 5h 12m, Efficiency 78%

Issues: Late bedtime + short duration
Week: 88→77→67 (declining 📉)

💡 Try sleeping earlier tonight!
```

### Analysis Approach

1. **Key findings first** — Lead with the most important insight
2. **Data-driven** — Always cite specific numbers
3. **Trends over snapshots** — Focus on patterns, not single nights
4. **Actionable advice** — Give 1-2 practical suggestions

### Tone

- Warm and supportive
- Concise (300-500 chars)
- Emojis sparingly 💤

---

## Requirements

- Python 3.8+
- No external dependencies (uses urllib)
