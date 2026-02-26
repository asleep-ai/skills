#!/usr/bin/env python3
"""
Asleep Sleep Insight - Sleep data insights for SleepHub users

Usage:
  python insight.py setup --user-id=X --access-token=Y --refresh-token=Z
  python insight.py                    # Get sleep insights
  python insight.py --check-new        # Only output if new session exists
  python insight.py --days=14          # Custom date range
  python insight.py --history          # View generation history
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Config paths
HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "asleep"
USER_FILE = CONFIG_DIR / "user.json"
HISTORY_FILE = CONFIG_DIR / "insight_history.json"

API_BASE = "https://api.asleep.ai"
KST = timezone(timedelta(hours=9))


def log(msg: str):
    """Log to stderr"""
    print(msg, file=sys.stderr)


def ensure_config_dir():
    """Create config directory if not exists"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_user() -> dict:
    """Load user config"""
    if not USER_FILE.exists():
        return {}
    return json.loads(USER_FILE.read_text())


def save_user(data: dict):
    """Save user config"""
    ensure_config_dir()
    USER_FILE.write_text(json.dumps(data, indent=2))


def load_history() -> dict:
    """Load generation history"""
    if not HISTORY_FILE.exists():
        return {"processed_sessions": [], "history": []}
    return json.loads(HISTORY_FILE.read_text())


def save_history(data: dict):
    """Save generation history"""
    ensure_config_dir()
    HISTORY_FILE.write_text(json.dumps(data, indent=2))


def api_request(method: str, url: str, token: str, data: dict = None) -> dict:
    """Make API request"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise Exception(f"API error {e.code}: {error_body}")


def refresh_token(user: dict) -> dict:
    """Refresh access token"""
    log("🔄 Refreshing token...")
    
    url = f"{API_BASE}/customer/v1/app/refresh"
    data = {"refresh_token": user["refresh_token"]}
    
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode()
    req = Request(url, data=body, headers=headers, method="POST")
    
    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            
        token_data = result.get("result", result)
        user["access_token"] = token_data["access_token"]
        user["refresh_token"] = token_data["refresh_token"]
        
        if "expires_in" in token_data:
            expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
            user["token_expires_at"] = expires_at.isoformat()
        
        save_user(user)
        log("✅ Token refreshed!")
        return user
        
    except HTTPError as e:
        raise Exception(f"Token refresh failed: {e.code}")


def ensure_token(user: dict) -> str:
    """Return valid token (refresh if needed)"""
    if not user.get("access_token"):
        raise Exception("No access_token. Run 'setup' first.")
    
    expires_at = user.get("token_expires_at")
    if expires_at:
        try:
            exp_time = datetime.fromisoformat(expires_at)
            if datetime.now() > exp_time - timedelta(minutes=5):
                user = refresh_token(user)
        except:
            pass
    
    return user["access_token"]


def fetch_sleep_data(user_id: str, token: str, days: int = 7) -> dict:
    """Fetch sleep data from API"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days-1)).strftime("%Y-%m-%d")
    
    url = (
        f"{API_BASE}/data/v1/users/{user_id}/average-stats"
        f"?start_date={start_date}&end_date={end_date}&timezone=Asia/Seoul"
    )
    
    return api_request("GET", url, token)


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime and convert to KST"""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(KST)
    except:
        return None


def parse_time_to_seconds(time_val) -> float:
    """Convert time value to seconds"""
    if time_val is None:
        return None
    if isinstance(time_val, (int, float)):
        return float(time_val)
    return None


def format_timedelta_to_str(seconds: float) -> str:
    """Format seconds to 'X hrs Y mins'"""
    if seconds is None:
        return "N/A"
    minutes = int(seconds // 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours} hrs {minutes} mins"
    return f"{minutes} mins"


def calculate_trend(values: list) -> str:
    """Calculate trend (Asleep internal logic)"""
    valid = [v for v in values if v is not None]
    if len(valid) < 3:
        return "insufficient data"
    
    # datetime type (time trend)
    if all(isinstance(v, datetime) for v in valid):
        def is_first_time_later(time1, time2):
            day_seconds = 24 * 60 * 60
            t1 = time1.timestamp() % day_seconds
            t2 = time2.timestamp() % day_seconds
            diff = (t1 - t2) % day_seconds
            return diff < day_seconds / 2
        
        is_later1 = is_first_time_later(valid[-1], valid[-2])
        is_later2 = is_first_time_later(valid[-2], valid[-3])
        
        if is_later1 and is_later2:
            return "getting later"
        if not is_later1 and not is_later2:
            return "getting earlier"
        return "no trend"
    
    # numeric type
    if valid[-1] > valid[-2] and valid[-2] > valid[-3]:
        return "increasing"
    if valid[-1] < valid[-2] and valid[-2] < valid[-3]:
        return "decreasing"
    return "no trend"


def subtract_if_not_none(a, b):
    """Subtract if both values are not None"""
    if a is not None and b is not None:
        return a - b
    return None


def subtract_relative_time(dt1: datetime, dt2: datetime) -> timedelta:
    """Calculate time difference (closest within 24h cycle)"""
    dt1_time = datetime.combine(datetime.min, dt1.time())
    dt2_time = datetime.combine(datetime.min, dt2.time())
    delta_seconds = (dt1_time - dt2_time).total_seconds()
    delta_seconds_mod = ((delta_seconds + 12 * 3600) % (24 * 3600)) - 12 * 3600
    if delta_seconds_mod == -12 * 3600:
        delta_seconds_mod = 12 * 3600
    return timedelta(seconds=delta_seconds_mod)


def format_delta_time(td: timedelta) -> str:
    """Format timedelta to string (with sign)"""
    total_seconds = td.total_seconds()
    sign = "+" if total_seconds >= 0 else ""
    abs_seconds = abs(total_seconds)
    minutes = int(abs_seconds // 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{sign}{int(total_seconds // 3600)} hrs {minutes} mins"
    return f"{sign}{int(total_seconds // 60)} mins"


def format_delta_percent(delta: float) -> str:
    """Format percent delta to string"""
    sign = "+" if delta >= 0 else ""
    return f"{sign}{int(delta * 100)}%"


def format_delta_number(delta: float) -> str:
    """Format number delta to string"""
    sign = "+" if delta >= 0 else ""
    if isinstance(delta, float):
        return f"{sign}{delta:.1f}"
    return f"{sign}{delta}"


def calculate_delta(current: dict, previous: dict) -> dict:
    """Calculate delta between two sessions"""
    delta = {}
    
    # Time comparison (sleep_time, wake_time)
    curr_sleep = parse_datetime(current.get("sleep_time"))
    prev_sleep = parse_datetime(previous.get("sleep_time"))
    if curr_sleep and prev_sleep:
        time_diff = subtract_relative_time(curr_sleep, prev_sleep)
        delta["sleep_time"] = format_delta_time(time_diff)
    
    curr_wake = parse_datetime(current.get("wake_time"))
    prev_wake = parse_datetime(previous.get("wake_time"))
    if curr_wake and prev_wake:
        time_diff = subtract_relative_time(curr_wake, prev_wake)
        delta["wake_time"] = format_delta_time(time_diff)
    
    # Duration comparison
    for key in ["sleep_latency", "time_in_sleep", "time_in_deep", "time_in_rem", "time_in_snoring"]:
        curr_val = current.get(key)
        prev_val = previous.get(key)
        if curr_val is not None and prev_val is not None:
            diff = curr_val - prev_val
            delta[key] = format_delta_time(timedelta(seconds=diff))
    
    # Ratio comparison
    for key in ["sleep_efficiency", "rem_ratio", "deep_ratio"]:
        curr_val = current.get(key)
        prev_val = previous.get(key)
        if curr_val is not None and prev_val is not None:
            diff = curr_val - prev_val
            delta[key] = format_delta_percent(diff)
    
    # Score comparison
    curr_score = current.get("sleep_index")
    prev_score = previous.get("sleep_index")
    if curr_score is not None and prev_score is not None:
        delta["sleep_score"] = format_delta_number(curr_score - prev_score)
    
    return delta


def convert_sleep_data(data: dict) -> dict:
    """Convert API response to Asleep format"""
    api_result = data.get("result", {})
    sessions = sorted(
        api_result.get("slept_sessions", []),
        key=lambda s: s.get("start_time", "")
    )
    avg_stats = api_result.get("average_stats", {})
    
    result = {
        "wake_dates": [],
        "sleep_onset_time": {"daily": []},
        "wake_up_time": {"daily": []},
        "sleep_onset_latency": {"daily": []},
        "total_sleep_time": {"daily": []},
        "deep_sleep_time": {"daily": []},
        "snoring_time": {"daily": []},
        "sleep_efficiency": {"daily": []},
        "rem_ratio": {"daily": []},
        "sleep_score": {"daily": []},
    }
    
    if not sessions:
        return result
    
    # Filter to last 7 days
    last_wake = parse_datetime(sessions[-1].get("wake_time"))
    if last_wake:
        seven_ago = last_wake.date() - timedelta(days=7)
        filtered_sessions = [
            s for s in sessions 
            if parse_datetime(s.get("wake_time")) and 
               parse_datetime(s.get("wake_time")).date() >= seven_ago
        ]
    else:
        filtered_sessions = sessions
    
    # Define data mapping
    data_mapping = {
        "sleep_onset_time": {
            "getter": lambda s: parse_datetime(s.get("sleep_time")).strftime("%H:%M:%S") if parse_datetime(s.get("sleep_time")) else "N/A",
            "raw_getter": lambda s: parse_datetime(s.get("sleep_time")),
            "avg_getter": lambda a: parse_datetime(a.get("sleep_time")).strftime("%H:%M:%S") if parse_datetime(a.get("sleep_time")) else a.get("sleep_time", "N/A"),
            "type": "time",
        },
        "wake_up_time": {
            "getter": lambda s: parse_datetime(s.get("wake_time")).strftime("%H:%M:%S") if parse_datetime(s.get("wake_time")) else "N/A",
            "raw_getter": lambda s: parse_datetime(s.get("wake_time")),
            "avg_getter": lambda a: parse_datetime(a.get("wake_time")).strftime("%H:%M:%S") if parse_datetime(a.get("wake_time")) else a.get("wake_time", "N/A"),
            "type": "time",
        },
        "sleep_onset_latency": {
            "getter": lambda s: format_timedelta_to_str(s.get("sleep_latency")),
            "raw_getter": lambda s: s.get("sleep_latency"),
            "avg_getter": lambda a: format_timedelta_to_str(a.get("sleep_latency")),
            "type": "duration",
        },
        "total_sleep_time": {
            "getter": lambda s: format_timedelta_to_str(s.get("time_in_sleep")),
            "raw_getter": lambda s: s.get("time_in_sleep"),
            "avg_getter": lambda a: format_timedelta_to_str(a.get("time_in_sleep")),
            "type": "duration",
        },
        "deep_sleep_time": {
            "getter": lambda s: format_timedelta_to_str(s.get("time_in_deep")),
            "raw_getter": lambda s: s.get("time_in_deep"),
            "avg_getter": lambda a: format_timedelta_to_str(a.get("time_in_deep")),
            "type": "duration",
        },
        "snoring_time": {
            "getter": lambda s: format_timedelta_to_str(s.get("time_in_snoring")),
            "raw_getter": lambda s: s.get("time_in_snoring"),
            "avg_getter": lambda a: format_timedelta_to_str(a.get("time_in_snoring")),
            "type": "duration",
        },
        "sleep_efficiency": {
            "getter": lambda s: f"{int(s.get('sleep_efficiency', 0) * 100)}%" if s.get('sleep_efficiency') else "N/A",
            "raw_getter": lambda s: s.get("sleep_efficiency"),
            "avg_getter": lambda a: f"{int(a.get('sleep_efficiency', 0) * 100)}%" if a.get('sleep_efficiency') else "N/A",
            "type": "percentage",
        },
        "rem_ratio": {
            "getter": lambda s: f"{int(s.get('rem_ratio', 0) * 100)}%" if s.get('rem_ratio') else "N/A",
            "raw_getter": lambda s: s.get("rem_ratio"),
            "avg_getter": lambda a: f"{int(a.get('rem_ratio', 0) * 100)}%" if a.get('rem_ratio') else "N/A",
            "type": "percentage",
        },
        "sleep_score": {
            "getter": lambda s: int(s.get("sleep_index")) if s.get("sleep_index") is not None else None,
            "raw_getter": lambda s: s.get("sleep_index"),
            "avg_getter": lambda a: None,  # No month avg for sleep score
            "type": "score",
        },
    }
    
    # Generate daily data
    for session in filtered_sessions:
        wake_dt = parse_datetime(session.get("wake_time"))
        if wake_dt:
            wake_date = wake_dt.strftime("%Y-%m-%d (%a)")
        else:
            wake_date = session.get("wake_time", "")[:10]
        
        result["wake_dates"].append(wake_date)
        
        for key, config in data_mapping.items():
            try:
                result[key]["daily"].append(config["getter"](session))
            except:
                result[key]["daily"].append("N/A")
    
    # Monthly average (if more than 1 session)
    if len(sessions) > 1 and avg_stats:
        for key, config in data_mapping.items():
            if key == "sleep_score":
                continue  # No month avg for sleep score
            try:
                result[key]["month_avg"] = config["avg_getter"](avg_stats)
            except:
                result[key]["month_avg"] = "N/A"
    
    # Trend (if 3+ sessions)
    if len(filtered_sessions) >= 3:
        for key, config in data_mapping.items():
            try:
                raw_values = [config["raw_getter"](s) for s in filtered_sessions]
                result[key]["trend"] = calculate_trend(raw_values)
            except:
                result[key]["trend"] = "error"
    
    return result


def record_generation(history: dict, session_id: str, data: dict):
    """Record generation history"""
    now = datetime.now().isoformat()
    
    if session_id not in history["processed_sessions"]:
        history["processed_sessions"].append(session_id)
    
    history["history"].append({
        "session_id": session_id,
        "generated_at": now,
    })
    
    history["history"] = history["history"][-30:]
    save_history(history)


def cmd_setup(args):
    """Save credentials"""
    user = {
        "user_id": args.user_id,
        "access_token": args.access_token,
        "refresh_token": args.refresh_token,
    }
    save_user(user)
    log(f"✅ Setup complete! Config saved to {USER_FILE}")


def cmd_insight(args):
    """Get sleep insights"""
    user = load_user()
    if not user:
        log("❌ No user config. Run 'setup' first:")
        log("   python insight.py setup --user-id=X --access-token=Y --refresh-token=Z")
        sys.exit(1)
    
    if args.history:
        history = load_history()
        print(json.dumps(history, indent=2))
        return
    
    user_id = user.get("user_id")
    if not user_id:
        log("❌ No user_id in config.")
        sys.exit(1)
    
    log("🔐 Checking token...")
    token = ensure_token(user)
    
    log(f"📊 Fetching {args.days} days of sleep data...")
    raw_data = fetch_sleep_data(user_id, token, args.days)
    
    # Extract session_ids first (for check-new)
    api_result = raw_data.get("result", {})
    sessions = api_result.get("slept_sessions", [])
    session_ids = [s.get("id") for s in sessions if s.get("id")]
    latest_session_id = session_ids[-1] if session_ids else None
    
    sleep_stats = convert_sleep_data(raw_data)
    
    if args.check_new and not args.force:
        history = load_history()
        if latest_session_id and latest_session_id in history["processed_sessions"]:
            log(f"⏭️ Session {latest_session_id} already processed, skipping.")
            return
        if latest_session_id:
            log(f"✨ New session detected: {latest_session_id}")
    
    print(json.dumps(sleep_stats, indent=2, ensure_ascii=False))
    
    if args.check_new or args.force:
        if latest_session_id:
            history = load_history()
            record_generation(history, latest_session_id, sleep_stats)
            log(f"📝 Recorded generation for session {latest_session_id}")


def main():
    parser = argparse.ArgumentParser(description="Asleep Sleep Insight")
    subparsers = parser.add_subparsers(dest="command")
    
    setup_parser = subparsers.add_parser("setup", help="Setup user credentials")
    setup_parser.add_argument("--user-id", required=True, help="User ID")
    setup_parser.add_argument("--access-token", required=True, help="Access token")
    setup_parser.add_argument("--refresh-token", required=True, help="Refresh token")
    
    parser.add_argument("--days", type=int, default=7, help="Days to fetch (default: 7)")
    parser.add_argument("--check-new", action="store_true", help="Only output if new session")
    parser.add_argument("--force", action="store_true", help="Force regeneration")
    parser.add_argument("--history", action="store_true", help="Show generation history")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        cmd_setup(args)
    else:
        cmd_insight(args)


if __name__ == "__main__":
    main()
