"""Scrape the public contribution calendar into data/contributions.json.

Uses the same HTML fragment the GitHub profile page loads, so no token is needed.
Exits non-zero (and writes nothing) if the markup looks broken, so a bad scrape
never overwrites a good graph. Run daily by .github/workflows/update-profile-art.yml.

    python scripts/fetch_contributions.py [username]
"""
import datetime
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER = "usmanmasood229"
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"


def parse(html):
    """Calendar HTML -> [{date, count, level}] sorted by date."""
    soup = BeautifulSoup(html, "html.parser")
    tips = {t.get("for"): t.get_text(" ", strip=True) for t in soup.find_all("tool-tip")}
    days = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        # "1,024 contributions on ..." / "1 contribution on ..." / "No contributions on ..."
        m = re.match(r"([\d,]+) contribution", tips.get(td.get("id"), ""))
        days.append({
            "date": td["data-date"],
            "count": int(m.group(1).replace(",", "")) if m else 0,
            "level": int(td.get("data-level") or 0),
        })
    days.sort(key=lambda d: d["date"])
    if not days:
        raise ValueError("no calendar cells found, GitHub markup may have changed")
    if any(d["level"] for d in days) and not any(d["count"] for d in days):
        raise ValueError("cells are coloured but no counts parsed, tooltip markup may have changed")
    return days


def current_streak(days):
    """Days in a row with contributions, ending today. A blank today doesn't break it (the day isn't over)."""
    i = len(days) - 1
    if i >= 0 and days[i]["count"] == 0:
        i -= 1
    n = 0
    while i >= 0 and days[i]["count"]:
        n += 1
        i -= 1
    return n


def longest_streak(days):
    best = run = 0
    for d in days:
        run = run + 1 if d["count"] else 0
        best = max(best, run)
    return best


def summarise(days, user):
    best = max(days, key=lambda d: d["count"])
    return {
        "username": user,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total": sum(d["count"] for d in days),
        "active_days": sum(1 for d in days if d["count"]),
        "current_streak": current_streak(days),
        "longest_streak": longest_streak(days),
        "best_day": {"date": best["date"], "count": best["count"]},
        "days": days,
    }


if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else USER
    resp = requests.get(f"https://github.com/users/{user}/contributions",
                        headers={"User-Agent": "profile-readme-bot"}, timeout=30)
    resp.raise_for_status()
    data = summarise(parse(resp.text), user)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1))
    print(f"wrote {OUT.name}: {data['total']} contributions, streak {data['current_streak']}, "
          f"longest {data['longest_streak']}")
