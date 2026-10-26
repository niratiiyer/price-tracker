def money(price: float) -> str:
    if price >= 1:
        return f"${price:,.2f}"
    return f"${price:.5f}".rstrip("0")


def pct(change: float) -> str:
    return f"{change:+.2f}%"
