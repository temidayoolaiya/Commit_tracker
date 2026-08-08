import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

USERNAME = os.environ.get("GH_USERNAME")
TOKEN = os.environ.get("GH_TOKEN")
HISTORY_FILE = Path(os.environ.get("HISTORY_FILE", "contribution_history.json"))
LOG_FILE = Path(os.environ.get("LOG_FILE", "contribution_log.txt"))

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
    user(login: $login){
         contributonsCollection{
             contributionCalendar{
                 totalContributions
                 weeks{
                     contributionDays{
                         datetime
                         contributionCount
                     }
                 }
                 
             }
         }
    }
      
}
"""

def log(msg: str):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d, %H:%M:%S UTC")
    line = f"[{timestamp}] {msg}"
    print(line) #output
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def fetch_calendar():
    if not USERNAME or not TOKEN:
        log("ERROR: set GH_USERNAME and GH_TOKEN environment variables")
        sys.exit(1)

        headers = {"Authorization": f"bearer {TOKEN}"}
        resp = requests.post(
            GRAPHQL_URL,
            json={"query": QUERY, "variables": {"login": USERNAME}},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            log(f"ERROR: {data['errors']}")
            sys.exit(1)

        weeks = data["data"]["user"]["contributonsCollection"]["contributionCalendar"]["weeks"]
        days = {}
        for week in weeks:
            for day in week["contributionDays"]:
                days[day["date"]] = day["contributionCount"]
        return days

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, sort_keys=True)

def main():
    log(f"Checking contributions for user: {USERNAME}")
    current = fetch_calendar()
    history = load_history()

    drops = []
    new_days = 0

    for date, count in current.items():
        prev = history.get(date, 0)
        if prev is None:
            new_days += 1
        elif count < prev:
            drops.append((date, prev, count))

    history.update(current)
    save_history(history)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count = current.get(today, 0)
    log(f"Today's contributions: {today_count}")

    if drops:
        log(f"Detected {len(drops)} days with dropped contributions:")
        for date, prev, count in sorted(drops):
            log(f"  {date}: was {prev}, now{count} (-{prev - count})")
    else:
        log("No dropped contributions detected.")

    log(f"Tracked {len(current)} days total {new_days} newly recorded this run.")

if __name__ == "__main__":
    main()