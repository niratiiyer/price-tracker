import csv
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_FILE = ROOT / "watchlist.csv"
PRICES_FILE = ROOT / "data" / "prices.csv"
ALERTS_FILE = ROOT / "data" / "alerts.csv"
PRICE_COLUMNS = ["checked_at", "coin_id", "symbol", "price", "change_since_last_pct", "change_24h_pct"]
ALERT_COLUMNS = ["checked_at", "coin_id", "symbol", "kind", "price", "detail"]


@dataclass
class Coin:
    coin_id: str
    symbol: str
    name: str
    alert_below: float | None
    alert_above: float | None


def _optional_float(value: str | None) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def load_watchlist(path: Path = WATCHLIST_FILE) -> list[Coin]:
    with open(path, newline="") as f:
        return [
            Coin(
                coin_id=row["coin_id"].strip(),
                symbol=row["symbol"].strip(),
                name=row["name"].strip(),
                alert_below=_optional_float(row.get("alert_below")),
                alert_above=_optional_float(row.get("alert_above")),
            )
            for row in csv.DictReader(f)
            if (row.get("coin_id") or "").strip()
        ]


def last_prices(path: Path = PRICES_FILE) -> dict[str, float]:
    latest: dict[str, float] = {}
    if not path.exists():
        return latest
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            latest[row["coin_id"]] = float(row["price"])
    return latest


def append_rows(rows: list[dict], path: Path, columns: list[str]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)
