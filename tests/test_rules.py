import csv

import check_prices
from tracker.coingecko import Quote, parse_response
from tracker.fmt import money
from tracker.rules import crossed_above, crossed_below, looks_like_glitch, pct_change, unusual_move
from tracker.storage import append_rows, last_prices, load_watchlist



def test_alert_when_price_first_falls_below_level():
    assert crossed_below(74_900, previous=76_000, level=75_000)
    assert crossed_below(75_000, previous=76_000, level=75_000)


def test_no_repeat_alert_while_price_stays_below():
    assert not crossed_below(74_000, previous=74_900, level=75_000)


def test_alerts_again_after_recovering_and_falling_again():
    assert not crossed_below(76_000, previous=74_000, level=75_000)
    assert crossed_below(74_500, previous=76_000, level=75_000)


def test_above_level_works_the_same_way():
    assert crossed_above(90_100, previous=89_000, level=90_000)
    assert not crossed_above(91_000, previous=90_100, level=90_000)
    assert not crossed_above(89_000, previous=88_000, level=90_000)


def test_blank_level_means_no_alert():
    assert not crossed_below(1, previous=100, level=None)
    assert not crossed_above(1000, previous=1, level=None)



def test_unusual_move_flags_big_moves_both_ways():
    assert round(unusual_move(103.5, 100, threshold_pct=3), 2) == 3.5
    assert round(unusual_move(96.0, 100, threshold_pct=3), 2) == -4.0


def test_small_moves_and_first_check_are_not_flagged():
    assert unusual_move(102.9, 100, threshold_pct=3) is None
    assert unusual_move(100, None, threshold_pct=3) is None


def test_threshold_comes_from_environment(monkeypatch):
    monkeypatch.setenv("MOVE_THRESHOLD_PCT", "1")
    assert unusual_move(101.5, 100) is not None



def test_glitches_are_caught():
    assert looks_like_glitch(0, previous=80_000)
    assert looks_like_glitch(800, previous=80_000)
    assert looks_like_glitch(200_000, previous=80_000)


def test_real_moves_are_not_glitches():
    assert not looks_like_glitch(72_000, previous=80_000)
    assert not looks_like_glitch(80_000, previous=None)


def test_pct_change():
    assert pct_change(110, 100) == 10
    assert pct_change(5, None) is None



def test_parse_response_reports_missing_coins():
    data = {"bitcoin": {"usd": 80349, "usd_24h_change": 1.5, "last_updated_at": 1792964593}}
    quotes, problems = parse_response(data, ["bitcoin", "notarealcoin"])
    assert quotes["bitcoin"] == Quote("bitcoin", 80349.0, 1.5, 1792964593)
    assert "didn't return" in problems["notarealcoin"]


def test_money_formatting():
    assert money(80349) == "$80,349.00"
    assert money(1.3) == "$1.30"
    assert money(0.07701) == "$0.07701"
    assert money(0.0682) == "$0.0682"



def test_watchlist_with_blank_levels(tmp_path):
    path = tmp_path / "watchlist.csv"
    path.write_text("coin_id,symbol,name,alert_below,alert_above\nbitcoin,BTC,Bitcoin,75000,\n\n")
    [coin] = load_watchlist(path)
    assert (coin.coin_id, coin.alert_below, coin.alert_above) == ("bitcoin", 75000.0, None)


def test_history_round_trip(tmp_path):
    path = tmp_path / "prices.csv"
    cols = ["checked_at", "coin_id", "price"]
    append_rows([{"checked_at": "t1", "coin_id": "bitcoin", "price": 80000}], path, cols)
    append_rows([{"checked_at": "t2", "coin_id": "bitcoin", "price": 77000}], path, cols)
    assert last_prices(path) == {"bitcoin": 77000.0}
    assert len(list(csv.DictReader(open(path)))) == 2



def test_full_run_records_prices_and_alerts(tmp_path, monkeypatch, capsys):
    watchlist = tmp_path / "watchlist.csv"
    watchlist.write_text("coin_id,symbol,name,alert_below,alert_above\nbitcoin,BTC,Bitcoin,75000,90000\n")
    prices, alerts = tmp_path / "prices.csv", tmp_path / "alerts.csv"
    monkeypatch.setattr(check_prices, "load_watchlist", lambda: load_watchlist(watchlist))
    monkeypatch.setattr(check_prices, "last_prices", lambda: last_prices(prices))
    monkeypatch.setattr(check_prices, "PRICES_FILE", prices)
    monkeypatch.setattr(check_prices, "ALERTS_FILE", alerts)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    def fake_market(price):
        monkeypatch.setattr(check_prices, "fetch_prices",
                            lambda ids: ({"bitcoin": Quote("bitcoin", price, 0.0, 0)}, {}))

    fake_market(80_000)
    assert check_prices.main() == 0
    fake_market(74_000)
    assert check_prices.main() == 0  # -7.5%: crosses the level and is a big move
    fake_market(73_500)
    assert check_prices.main() == 0  # still below, small move, so nothing new

    kinds = [row["kind"] for row in csv.DictReader(open(alerts))]
    assert kinds == ["below", "move"]
    assert len(list(csv.DictReader(open(prices)))) == 3
    assert "Unusual move: Bitcoin (BTC) -7.50%" in capsys.readouterr().out


def test_full_run_survives_coingecko_being_down(monkeypatch, capsys):
    def boom(ids):
        raise OSError("connection refused")
    monkeypatch.setattr(check_prices, "fetch_prices", boom)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert check_prices.main() == 1
    assert "couldn't reach CoinGecko" in capsys.readouterr().out
