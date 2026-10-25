def money(price: float) -> str:
    """$80,349.00 for big prices, $0.07701 for small ones."""
    if price >= 1:
        return f"${price:,.2f}"
    return f"${price:.5f}".rstrip("0")


def pct(change: float) -> str:
    return f"{change:+.2f}%"
