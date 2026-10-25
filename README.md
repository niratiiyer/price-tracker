# Crypto Market Monitor

Watches cryptocurrency prices around the clock and flags what matters: a price crossing a level I set,
or an unusually large move between two checks. It runs by itself. GitHub Actions checks prices every hour
from CoinGecko's free API, saves every check to [`data/prices.csv`](data/prices.csv) and every alert to
[`data/alerts.csv`](data/alerts.csv), and a Streamlit dashboard shows prices, charts, the biggest moves
and the alert log.

## How it works

```
Every hour (GitHub Actions)
  check_prices.py
    1. reads the watchlist                     watchlist.csv
    2. asks CoinGecko for all prices in one request
    3. skips bad data                          (missing coins, zero prices, impossible jumps)
    4. saves each price + % change             data/prices.csv   (committed back to the repo)
    5. checks three alert rules                → Discord (optional) + data/alerts.csv
         - price fell to/below my "alert below" level
         - price rose to/above my "alert above" level
         - price moved ≥ 3% since the last check (up or down)

Any time
  dashboard.py (Streamlit)  →  current prices vs levels, price-history chart,
                               biggest moves, alert log
```

## Design decisions

- **Alert on the crossing, not the state.** A level alert fires only on the check where the price *crosses*
  the level (it was above last hour and is at or below now). If Bitcoin stays under my level for two days,
  I get one alert, not 48. If it recovers and falls through again, it alerts again.
- **"Unusual move" is measured between checks.** A ≥ 3% move in one hour is rare for large coins, so it's
  worth a look. The threshold is a setting (`MOVE_THRESHOLD_PCT`), not hard-coded.
- **Bad-data filter.** A price of zero, or a ≥ 50% jump between two hourly checks, is far more likely a data
  problem than a real market move, so it's skipped and reported instead of triggering alerts. If the API is
  down, the run fails loudly (and posts a Discord message) instead of saving nothing silently.
- **A CSV in the repo instead of a database.** The data is small, every check is visible in the commit
  history, and there's nothing to host or pay for.
- **Rules are separate from network code** (`tracker/rules.py`), so they're tested without calling CoinGecko.
  One test fakes a full price crash end to end and checks exactly which alerts fire.

## Findings

_Fill this in after a few weeks of data, for example:_
- _How many checks ran, and how many unusual moves were flagged? Which coins moved most?_
- _Did big moves cluster at certain times of day or days of the week?_
- _Were the alert levels set well, or did they fire too often / never? What would I change?_

## Run it yourself

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python check_prices.py        # one price check (prints alerts instead of sending them)
streamlit run dashboard.py    # dashboard at http://localhost:8501
pytest                        # tests
```

## Change the coins or alert levels

Edit [`watchlist.csv`](watchlist.csv): one line per coin with its CoinGecko **API id** (shown on the coin's
page at coingecko.com, e.g. Bitcoin → `bitcoin`, XRP → `ripple`), a symbol, a name, and the price levels to
alert below and above (leave either blank to skip it).

## Project layout

```
check_prices.py        one check: fetch, filter, save, alert
dashboard.py           Streamlit dashboard
watchlist.csv          coins and alert levels
data/prices.csv        every price ever recorded
data/alerts.csv        every alert ever sent
tracker/coingecko.py   calls CoinGecko's API and parses the response
tracker/rules.py       level crossings, unusual moves, bad-data filter
tracker/storage.py     reading and writing the CSV files
tracker/alerts.py      Discord webhook (or print)
tracker/fmt.py         money and percent formatting
tests/                 pytest tests, including a faked end-to-end crash
.github/workflows/     the hourly price check, and tests on every push
```
