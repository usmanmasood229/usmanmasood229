"""Plain-assert checks for the scrape + streak + grid logic.  Run: python tests/test_scripts.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from fetch_contributions import current_streak, longest_streak, parse  # noqa: E402
from render_heatmap import grid  # noqa: E402


def cal(*cells):
    """cells: (date, level, tooltip text or None for a missing tooltip)"""
    tds = "".join(f'<td class="ContributionCalendar-day" data-date="{d}" data-level="{lv}" id="c{i}"></td>'
                  for i, (d, lv, _) in enumerate(cells))
    tips = "".join(f'<tool-tip for="c{i}">{t}</tool-tip>' for i, (_, _, t) in enumerate(cells) if t is not None)
    return f"<table><tr>{tds}</tr></table>{tips}"


def days(*counts):
    return [{"date": f"2026-01-{i + 1:02d}", "count": c, "level": int(c > 0)} for i, c in enumerate(counts)]


def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


# parse: counts with commas, singular, none, missing tooltip, out-of-order cells
got = parse(cal(("2026-01-03", 4, "1,024 contributions on January 3rd."),
                ("2026-01-01", 1, "1 contribution on January 1st."),
                ("2026-01-02", 0, "No contributions on January 2nd."),
                ("2026-01-04", 0, None)))
assert [d["date"] for d in got] == ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"], got
assert [d["count"] for d in got] == [1, 0, 1024, 0], got
assert [d["level"] for d in got] == [1, 0, 4, 0], got

# parse refuses broken markup instead of writing a blank graph
assert raises(lambda: parse("<html></html>"))
assert raises(lambda: parse(cal(("2026-01-01", 3, None), ("2026-01-02", 2, None))))
# ...but an honest all-zero year is fine
assert [d["count"] for d in parse(cal(("2026-01-01", 0, "No contributions on January 1st.")))] == [0]

# streaks
assert current_streak([]) == 0 and longest_streak([]) == 0
assert current_streak(days(0, 0, 0)) == 0 and longest_streak(days(0, 0, 0)) == 0
assert current_streak(days(3, 1, 0)) == 2, "a blank today must not break the streak"
assert current_streak(days(3, 0, 0)) == 0, "a blank yesterday does"
assert current_streak(days(1, 0, 1)) == 1
assert current_streak(days(1, 1, 1)) == 3
assert current_streak(days(0)) == 0 and current_streak(days(5)) == 1
assert longest_streak(days(1, 1, 0, 1, 1, 1, 0, 1)) == 3

# grid: Sunday on top, weeks as columns, Saturday -> Sunday wraps to the next column
g = grid([{"date": d, "level": 0} for d in ["2026-11-01", "2026-11-02", "2026-11-07", "2026-11-08"]])
assert [(c, r) for c, r, _, _ in g] == [(0, 0), (0, 1), (0, 6), (1, 0)], g  # Nov 1 2026 is a Sunday
g = grid([{"date": d, "level": 0} for d in ["2026-11-04", "2026-11-08"]])  # starts mid-week (Wednesday)
assert [(c, r) for c, r, _, _ in g] == [(0, 3), (1, 0)], g

print("all checks passed")
