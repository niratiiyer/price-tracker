import sys
from datetime import datetime, timezone

from tracker.alerts import send_alert
from tracker.coingecko import fetch_prices
from tracker.fmt import money, pct
from tracker.rules import crossed_above, crossed_below, looks_like_glitch, pct_change, unusual_move
from tracker.storage import (
    ALERT_COLUMNS, ALERTS_FILE, PRICE_COLUMNS, PRICES_FILE, append_rows, last_prices, load_watchlist,
)


def main() -> int:
    coins = load_watchlist()
    previous = last_prices()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        quotes, problems = fetch_prices([c.coin_id for c in coins])
    except Exception as exc:
        send_alert(f"Price check failed: couldn't reach CoinGecko ({exc})")
        return 1

    price_rows, alert_rows = [], []

    def alert(coin, kind, price, detail, message):
        alert_rows.append({"checked_at": now, "coin_id": coin.coin_id, "symbol": coin.symbol,
                           "kind": kind, "price": price, "detail": detail})
        send_alert(message)

    for coin in coins:
        if coin.coin_id in problems:
            print(f"Skipped {coin.name}: {problems[coin.coin_id]}")
            continue
        price = quotes[coin.coin_id].price
        before = previous.get(coin.coin_id)
        if looks_like_glitch(price, before):
            print(f"Skipped {coin.name}: {money(price)} looks like bad data (last check {money(before)})")
            continue

        change = pct_change(price, before)
        price_rows.append({
            "checked_at": now,
            "coin_id": coin.coin_id,
            "symbol": coin.symbol,
            "price": price,
            "change_since_last_pct": "" if change is None else round(change, 3),
            "change_24h_pct": round(quotes[coin.coin_id].change_24h_pct, 3),
        })
        since = "first check" if change is None else f"{pct(change)} since last check"
        print(f"{coin.symbol}: {money(price)} ({since})")

        if crossed_below(price, before, coin.alert_below):
            alert(coin, "below", price, f"level {money(coin.alert_below)}",
                  f"{coin.name} ({coin.symbol}) fell to {money(price)}, below your {money(coin.alert_below)} level.")
        if crossed_above(price, before, coin.alert_above):
            alert(coin, "above", price, f"level {money(coin.alert_above)}",
                  f"{coin.name} ({coin.symbol}) rose to {money(price)}, above your {money(coin.alert_above)} level.")
        move = unusual_move(price, before)
        if move is not None:
            alert(coin, "move", price, f"{move:.2f}%",
                  f"Unusual move: {coin.name} ({coin.symbol}) {pct(move)} since the last check "
                  f"({money(before)} → {money(price)}).")

    append_rows(price_rows, PRICES_FILE, PRICE_COLUMNS)
    append_rows(alert_rows, ALERTS_FILE, ALERT_COLUMNS)
    print(f"Saved {len(price_rows)} prices and {len(alert_rows)} alerts at {now}")
    return 0 if price_rows else 1


if __name__ == "__main__":
    sys.exit(main())
