# Asleep Skills

AI agent skills for Asleep sleep data.

## Available Skills

### [asleep-insight](./asleep-insight)

AI-powered sleep insights for SleepHub app users.

- Get personalized sleep analysis
- Track trends (sleep time, efficiency, score)
- Heartbeat integration for daily insights

**Quick start:**
```bash
python asleep-insight/scripts/insight.py setup \
  --user-id=YOUR_USER_ID \
  --access-token=YOUR_ACCESS_TOKEN \
  --refresh-token=YOUR_REFRESH_TOKEN

python asleep-insight/scripts/insight.py
```

See [asleep-insight/SKILL.md](./asleep-insight/SKILL.md) for full documentation.

---

## Requirements

- Python 3.8+
- No external dependencies

## License

MIT
