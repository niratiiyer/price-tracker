import os


def move_threshold_pct() -> float:
    return float(os.environ.get("MOVE_THRESHOLD_PCT", "3"))


# anything this big between two hourly checks is almost certainly bad data
GLITCH_MOVE_PCT = 50.0


def pct_change(price: float, previous: float | None) -> float | None:
    if previous is None or previous == 0:
        return None
    return (price - previous) / previous * 100


def looks_like_glitch(price: float, previous: float | None) -> bool:
    if price <= 0:
        return True
    change = pct_change(price, previous)
    return change is not None and abs(change) >= GLITCH_MOVE_PCT


def crossed_below(price: float, previous: float | None, level: float | None) -> bool:
    # only true on the check where it crosses, not every check after
    if level is None or price > level:
        return False
    return previous is None or previous > level


def crossed_above(price: float, previous: float | None, level: float | None) -> bool:
    if level is None or price < level:
        return False
    return previous is None or previous < level


def unusual_move(price: float, previous: float | None, threshold_pct: float | None = None) -> float | None:
    threshold = move_threshold_pct() if threshold_pct is None else threshold_pct
    change = pct_change(price, previous)
    if change is None or abs(change) < threshold:
        return None
    return change
