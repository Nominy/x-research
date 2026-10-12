import hashlib
import html
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
GRAPHS = ROOT / "graphs"


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    panel = json.loads((DATA / "panel.json").read_text(encoding="utf-8"))
    start, end = timestamp(panel["start"]), timestamp(panel["end_exclusive"])
    hour = timedelta(hours=1)
    days = (end - start).days
    dates = [start + timedelta(days=i, hours=12) for i in range(days)]
    selection = panel["eligibility"]
    window = panel["comparison"]
    before_start = timestamp(selection["start"])
    before_end = timestamp(selection["end_exclusive"])
    after_start = timestamp(window["start"])
    after_end = timestamp(window["end_exclusive"])
    rows = []
    for account in panel["accounts"]:
        raw = (DATA / account["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == account["sha256"]
        response = json.loads(raw)
        assert not response.get("errors") and not response["meta"].get("next_token")
        counts = {}
        for bucket in response["data"]:
            t, n = timestamp(bucket["start"]), bucket["tweet_count"]
            assert start <= t < end and (t - start) % hour == timedelta(0)
            assert timestamp(bucket["end"]) == t + hour and t not in counts
            assert isinstance(n, int) and not isinstance(n, bool) and n >= 0
            counts[t] = n
        assert len(counts) == days * 24
        assert sum(counts.values()) == response["meta"]["total_tweet_count"]
        before = [(t, n) for t, n in counts.items() if before_start <= t < before_end]
        assert sum(n for _, n in before) >= selection["minimum_posts"]
        assert len({t.date() for t, n in before if n}) >= selection["minimum_utc_dates"]
        daily = [sum(counts[start + timedelta(days=i, hours=h)] for h in range(24)) for i in range(days)]
        last = max(i for i, n in enumerate(daily) if n)
        rule = panel["zero_examples"]
        zero_example = (
            daily[last] >= rule["minimum_last_day_posts"]
            and sum(n > 0 for n in daily[max(0, last - 6):last + 1]) >= rule["minimum_active_dates_in_last_seven_days"]
            and days - last - 1 >= rule["minimum_following_zero_days"]
        )
        observed = sum(n for t, n in counts.items() if after_start <= t < after_end)
        references = [sum(n for t, n in counts.items() if after_start - timedelta(weeks=w) <= t < after_end - timedelta(weeks=w)) for w in window["reference_weeks"]]
        rows.append({"username": account["username"], "daily": daily, "observed": observed, "references": references, "zero_example": zero_example})
    assert len(rows) == len({r["username"].lower() for r in rows}) == 47
    total = [sum(r["daily"][i] for r in rows) for i in range(days)]
    zero_rows = [r for r in rows if r["zero_example"]]
    observed = sum(r["observed"] for r in rows)
    references = [sum(r["references"][i] for r in rows) for i in range(len(window["reference_weeks"]))]
    mean = sum(references) / len(references)
    summary = {"accounts": len(rows), "observed": observed, "reference_totals": references, "reference_mean": mean,
               "change": observed / mean - 1, "no_posts_after": sum(r["observed"] == 0 for r in rows),
               "zero_examples": len(zero_rows), "daily": [{"date": d.date().isoformat(), "posts": n} for d, n in zip(dates, total)]}
    (DATA / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    GRAPHS.mkdir(exist_ok=True)

    def draw(ax, values, title, small=False):
        ax.plot(dates, values, color="black", linewidth=0.9)
        for event in panel["events"]:
            if "end" in event:
                ax.axvspan(timestamp(event["start"]), timestamp(event["end"]), color="0.9", zorder=0)
            else:
                ax.axvline(timestamp(event["start"]), color="0.6", linestyle="--", linewidth=0.7)
        ax.set_xlim(start, end)
        ax.set_ylim(bottom=0)
        ax.set_title(title, fontsize=9 if small else 11)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=3 if small else 5, integer=True))
        ax.set_xticks([dates[0], dates[14], dates[-1]] if small else dates[::4] + [dates[-1]])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d", tz=timezone.utc))
        ax.tick_params(labelsize=7 if small else 9)
        ax.set_ylabel("posts", fontsize=7 if small else 9)

    for name, values, title in [
        ("daily", total, "all 47 accounts"),
        ("zero", [sum(r["daily"][i] for r in zero_rows) for i in range(days)], f"accounts ending at zero ({len(zero_rows)})"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 3))
        draw(ax, values, title)
        fig.tight_layout()
        fig.savefig(GRAPHS / f"{name}.png", dpi=140)
        plt.close(fig)
    fig, axes = plt.subplots(math.ceil(len(rows) / 3), 3, figsize=(12, 27))
    for ax, row in zip(axes.flat, rows):
        draw(ax, row["daily"], "@" + row["username"].lower(), small=True)
    for ax in list(axes.flat)[len(rows):]:
        ax.set_visible(False)
    fig.tight_layout(pad=1.2)
    fig.savefig(GRAPHS / "accounts.png", dpi=150)
    plt.close(fig)

    links = "\n".join(f'<li><a href="data/{html.escape(a["file"])}">@{html.escape(a["username"].lower())}</a></li>' for a in panel["accounts"])
    page = f'''<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>x research</title>
<style>img {{ max-width: 100%; height: auto; }}</style>
<h1>x research</h1>
<p>47 accounts, september 14–october 11, 2026. posts include reposts. all times utc.</p>
<p><a href="https://github.com/nominy/x-research">readme</a> · <a href="data/panel.json">panel</a> · <a href="data/summary.json">summary</a></p>
<p>dashed lines: october 7 at 22:31 and october 11 at 01:00. grey band: october 9, exact time unknown.</p>
<h2>daily posts</h2>
<a href="graphs/daily.png"><img src="graphs/daily.png" width="1000" alt="daily posts from all 47 accounts"></a>
<h2>per account</h2>
<p>each y-axis starts at zero; scales differ.</p>
<a href="graphs/accounts.png"><img src="graphs/accounts.png" width="1200" alt="daily posts for each of the 47 accounts"></a>
<h2>ending at zero</h2>
<p>{len(zero_rows)} accounts selected by their zero tail. this is not a separate causal test; the rule is in panel.json.</p>
<a href="graphs/zero.png"><img src="graphs/zero.png" width="1000" alt="posts from the selected accounts ending at zero"></a>
<h2>raw counts</h2>
<ul>
{links}
</ul>
</html>
'''
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    print(f"{len(rows)} accounts; {observed} posts vs {mean:.1f}; {len(zero_rows)} zero-tail examples")


if __name__ == "__main__":
    main()
