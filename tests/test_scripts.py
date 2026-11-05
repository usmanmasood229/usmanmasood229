"""Plain-assert checks for the scrape, streak, grid and render logic.  Run: python tests/test_scripts.py

Needs only beautifulsoup4 (CI runs it). make_ascii.py is left out: it needs numpy/Pillow and its
output is a one-off image checked by eye."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from fetch_contributions import current_streak, longest_streak, parse, summarise  # noqa: E402
from render_heatmap import LEVELS, grid, render  # noqa: E402
import make_info_card  # noqa: E402


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
assert raises(lambda: parse(cal(("2026-01-01", 0, "5 contributions on January 1st."))))  # counts, no colours
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

# summarise: the numbers printed under the graph
s = summarise(days(2, 0, 5, 5))
assert (s["total"], s["current_streak"], s["longest_streak"]) == (12, 2, 2), s
assert s["best_day"] == {"date": "2026-01-03", "count": 5}, s  # first of a tie
assert s["range"] == {"start": "2026-01-01", "end": "2026-01-04"}, s
assert "generated_at" not in s, "a timestamp would make every run commit"

# grid: Sunday on top, weeks as columns, Saturday -> Sunday wraps to the next column
g = grid([{"date": d, "level": 0} for d in ["2026-11-01", "2026-11-02", "2026-11-07", "2026-11-08"]])
assert [(c, r) for c, r, _, _ in g] == [(0, 0), (0, 1), (0, 6), (1, 0)], g  # Nov 1 2026 is a Sunday
g = grid([{"date": d, "level": 0} for d in ["2026-11-04", "2026-11-08"]])  # starts mid-week (Wednesday)
assert [(c, r) for c, r, _, _ in g] == [(0, 3), (1, 0)], g

# render: a level above 4 (GitHub adding a tier) clamps to the top colour instead of crashing
svg = render({"days": [{"date": "2026-11-01", "level": 0}, {"date": "2026-11-02", "level": 5}],
              "best_day": {"date": "2026-11-02", "count": 9}, "range": {"start": "2026-11-01", "end": "2026-11-02"},
              "total": 9, "current_streak": 1, "longest_streak": 1})
assert f'fill="{LEVELS[4]}" style="animation-delay' in svg, "level 5 cell must use the level-4 colour"

# info card: the real LINES fit, too many lines refuses instead of drawing over the status bar
make_info_card.render()
saved = make_info_card.LINES
make_info_card.LINES = [("k", "v")] * 30
try:
    make_info_card.render()
    raise AssertionError("overflowing card rendered without complaint")
except SystemExit as e:
    assert "overflows into the status bar" in str(e.code), e.code
finally:
    make_info_card.LINES = saved

# render: well-formed XML, every box inside the frame, month labels like GitHub's
NS = "{http://www.w3.org/2000/svg}"


def year(start, n, level=1):
    import datetime
    d0 = datetime.date.fromisoformat(start)
    return [{"date": str(d0 + datetime.timedelta(i)), "count": level, "level": level} for i in range(n)]


def texts(root):
    return ["".join(t.itertext()) for t in root.iter(NS + "text")]


root = ET.fromstring(render(summarise(year("2025-11-02", 369))))
w = float(root.get("width"))
assert all(float(r.get("x")) + 12 <= w - 22 for r in root.iter(NS + "rect") if r.get("class") == "c")
assert sum(1 for r in root.iter(NS + "rect") if r.get("class") == "c") == 369
labels = [t for t in texts(root) if t in {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}]
assert labels == ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"], labels
# opening month left unlabelled when the next month starts 1 column later (would overlap)
root = ET.fromstring(render(summarise(year("2025-11-28", 10))))  # Fri Nov 28 -> Mon Dec 1 is column 1
assert [t for t in texts(root) if t in {"Nov", "Dec"}] == ["Dec"], texts(root)
# singular total
one = render(summarise(year("2026-01-01", 1)))
assert "</tspan> contribution in the last year" in one and "1 day</tspan>" in one

# info card: well-formed XML
ET.fromstring(make_info_card.render())

# portrait: only where numpy/Pillow are installed (not in CI), reported as skipped otherwise
try:
    import make_ascii
except ImportError:
    print("skipped portrait check: numpy/Pillow not installed")
else:
    root = ET.fromstring(make_ascii.render(["  .:@@  ", "        ", "@" * 8]))
    rows = [t for t in root.iter(NS + "text") if t.get("class") == "r"]
    assert len(rows) == 2, "blank rows are skipped, the rest are drawn"
    assert root.get("width") == "840" and root.get("height") == "884", "must match info-card.svg"

print("all checks passed")
