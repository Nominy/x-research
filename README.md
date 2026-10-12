# x research

a small check of 47 accounts around the october 2026 yandex outages.

the accounts came from [antibot4navalny's list](https://github.com/antibot4navalny/accounts_labelled/blob/285cb844017ee6d3132c89e5c7b63eb16413ee27/labels_manual.json): the 64 september additions and a fixed sample of 250 older entries. kept the 47 with at least 5 posts on 2 dates in the week before the first outage. accounts that went quiet afterward stayed in.

pulled hourly x api counts for september 14–october 11, including reposts. all times are utc. compared october 7 at 23:00 through october 12 at 00:00 with the same hours in the previous three weeks: 511 posts vs 818.3 on average, down 37.6%.

these are researcher-flagged accounts, not verified bots. this doesn't establish what caused the drop.

[graphs](index.html) · [data and selection rule](data/panel.json)

to rebuild the graphs:

```sh
python -m pip install matplotlib
python plot.py
```
