"""Fetch current prices from CoinGecko's free public API (no key needed)."""
import json
import urllib.request
from dataclasses import dataclass

API_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids={ids}&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true"
)


@dataclass
class Quote:
    coin_id: str
    price: float          # US dollars
    change_24h_pct: float  # CoinGecko's own 24-hour change, in percent
    updated_at: int        # when CoinGecko last updated this price (Unix seconds)


def parse_response(data: dict, coin_ids: list[str]) -> tuple[dict[str, Quote], dict[str, str]]:
    """Turn CoinGecko's JSON into quotes, plus a reason for every coin we couldn't price."""
    quotes, problems = {}, {}
    for coin_id in coin_ids:
        entry = data.get(coin_id)
        if not entry:
            problems[coin_id] = "CoinGecko didn't return this coin (check the coin_id)"
            continue
        price = entry.get("usd")
        if price is None:
            problems[coin_id] = "no USD price in the response"
            continue
        quotes[coin_id] = Quote(
            coin_id=coin_id,
            price=float(price),
            change_24h_pct=float(entry.get("usd_24h_change") or 0.0),
            updated_at=int(entry.get("last_updated_at") or 0),
        )
    return quotes, problems


def fetch_prices(coin_ids: list[str], timeout: int = 20) -> tuple[dict[str, Quote], dict[str, str]]:
    url = API_URL.format(ids=",".join(coin_ids))
    request = urllib.request.Request(url, headers={"User-Agent": "crypto-market-monitor (student project)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return parse_response(json.load(response), coin_ids)
