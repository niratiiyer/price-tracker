# price-tracker

Hourly crypto price checks with alerts.

A GitHub Action pulls prices from CoinGecko every hour, appends them to `data/prices.csv`, and logs an
alert to `data/alerts.csv` when:

- a price drops below or rises above a level set in `watchlist.csv`
- a price moves 3% or more since the previous check

Alerts show up on the dashboard. They can also be posted to Discord (see below).

`dashboard.py` is a Streamlit app that shows current prices, a chart per coin, the largest moves, and past alerts.

## Notes

- Level alerts only fire on the check where the price crosses the level. A coin sitting below its level
  doesn't alert every hour.
- A zero price, or a 50%+ jump between two hourly checks, is treated as bad data and skipped.
- If two runs overlap, the second push gets rejected. It then redoes the check on top of the first run's data
  so the "change since last check" is still right.
- History is stored as CSV in the repo rather than a database. It's small, and every check is a commit.
- The 3% threshold is the same for every coin, which is too tight for some (DOGE) and loose for others (BTC).
  Scaling it by each coin's recent volatility would be the next thing to change.

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python check_prices.py      # one check; alerts print instead of posting
streamlit run dashboard.py
pytest
```

Set `DISCORD_WEBHOOK_URL` to post alerts to Discord, and `MOVE_THRESHOLD_PCT` to change the 3%. In Actions these are a
repo secret and a repo variable.

## Watchlist

```
coin_id,symbol,name,alert_below,alert_above
bitcoin,BTC,Bitcoin,75000,90000
```

`coin_id` is the id on the coin's CoinGecko page. Either level can be left blank.
