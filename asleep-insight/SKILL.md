---
name: asleep-insight
version: 1.1.0
description: AI-powered sleep insights for SleepHub app users
homepage: https://asleep.ai
---

# Asleep Sleep Insight

AI-powered sleep insights for SleepHub app users.

## Skill Files

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

## Setup

Get your credentials from the SleepHub app, then run:

```bash
python scripts/insight.py setup \
  --user-id=YOUR_USER_ID \
  --access-token=YOUR_ACCESS_TOKEN \
  --refresh-token=YOUR_REFRESH_TOKEN
```

Credentials are saved to `~/.config/asleep/user.json`

## ⚠️ Token Notes

- **Access tokens expire after 10 hours**
- If you get `403: token invalid`, the script will **auto-refresh** using your refresh token
- Refresh tokens are valid for 14 days — use the skill at least once every 2 weeks to stay logged in
- If both tokens expire, ask your user for new credentials from the app

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

## Heartbeat Integration

Add to **every heartbeat** (not just morning):

```bash
python scripts/insight.py --check-new
```

**Behavior:**
- New session detected → Outputs JSON → Generate insight and send
- No new session → Silent exit (no output, no action needed)

The script automatically tracks which sessions have been processed — no duplicates, no spam.

**Why every heartbeat?** Users wake up at different times, take naps, or have irregular schedules. Checking frequently ensures timely insights without knowing their sleep pattern.

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

## Trends

- `increasing` / `decreasing` — numeric values
- `getting earlier` / `getting later` — time values
- `no trend` — stable or insufficient data

---

## Agent Guidelines

### Analysis Approach

1. **Key findings first** — Lead with the most important insight
2. **Data-driven** — Always cite specific numbers
3. **Trends over snapshots** — Focus on patterns, not single nights
4. **Actionable advice** — Give 1-2 practical suggestions

### Reference Ranges

| Metric | Healthy Range |
|--------|---------------|
| Sleep Efficiency | ≥ 85% |
| Deep Sleep Ratio | 15-25% |
| REM Ratio | 20-25% |
| Sleep Latency | 10-20 mins |

### Tone

- Warm and supportive
- Concise (300-500 chars)
- Emojis sparingly 💤

---

## Requirements

- Python 3.8+
- No external dependencies (uses urllib)
