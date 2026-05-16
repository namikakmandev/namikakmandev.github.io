"""Discount & Margin Calculator (command-line version).

Same logic as js/discount-margin-calculator.js. Universal: works in any
currency. Run:
    python discount_margin_calculator.py
"""

import math


def discount_margin(price, cost, discount_pct, units=0):
    """Mirror of the web tool's compute() + break-even logic."""
    disc = min(100.0, max(0.0, discount_pct))
    net = price * (1 - disc / 100)
    m_before = price - cost
    m_after = net - cost
    m_before_pct = (m_before / price * 100) if price > 0 else 0.0
    m_after_pct = (m_after / net * 100) if net > 0 else 0.0

    # Extra unit volume needed to keep the SAME total profit after the discount.
    extra_pct = None  # None = cannot break even (selling at/below cost)
    if m_after > 0 and m_before > 0:
        extra_pct = (m_before / m_after - 1) * 100

    result = {
        "net_price": net,
        "margin_before": m_before,
        "margin_after": m_after,
        "margin_before_pct": m_before_pct,
        "margin_after_pct": m_after_pct,
        "extra_pct": extra_pct,
    }

    if units > 0:
        result["total_profit_before"] = m_before * units
        result["total_profit_after"] = m_after * units
        result["total_profit_lost"] = (m_before - m_after) * units
        if extra_pct is not None and disc > 0:
            extra_units = math.ceil(units * (extra_pct / 100))
            result["extra_units"] = extra_units
            result["break_even_target"] = units + extra_units

    return result


def _ask(prompt, default, cast=float):
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        value = cast(raw)
        return value if value >= 0 else default
    except ValueError:
        return default


if __name__ == "__main__":
    print("Discount & Margin Calculator\n")
    sym = input("Currency symbol (optional, e.g. $) []: ").strip()
    pad = (sym + " ") if sym else ""

    price = _ask("List / sticker price", 100.0)
    cost = _ask("Unit cost / COGS", 60.0)
    disc = _ask("Discount given (%)", 15.0)
    units = _ask("Units sold (optional, 0 to skip)", 0, int)

    r = discount_margin(price, cost, disc, units)

    print("\n--- Result ---")
    print(f"Net price after discount   {pad}{r['net_price']:,.2f}")
    print(f"Margin before discount     {pad}{r['margin_before']:,.2f} "
          f"({r['margin_before_pct']:.1f}%)")
    print(f"Margin after discount      {pad}{r['margin_after']:,.2f} "
          f"({r['margin_after_pct']:.1f}%)")

    if r["margin_after"] <= 0:
        print("\nAt this discount the price is at or below your cost — "
              "you lose money on every unit, so no extra volume breaks even.")
    elif r["extra_pct"] is None or disc == 0:
        print("\nNo discount applied — your margin is unchanged.")
    else:
        profit_cut = (1 - r["margin_after"] / r["margin_before"]) * 100
        print(f"\nA {disc:.1f}% discount cuts your per-unit profit by "
              f"{profit_cut:.1f}%.")
        print(f"You must sell {r['extra_pct']:.1f}% more units just to make "
              f"the same total profit.")
        if units > 0:
            print(f"\nOn {units:,} units:")
            print(f"  Total profit lost   {pad}{r['total_profit_lost']:,.2f}  "
                  f"({pad}{r['total_profit_before']:,.0f} -> "
                  f"{pad}{r['total_profit_after']:,.0f})")
            print(f"  Extra units to sell  +{r['extra_units']:,} units  "
                  f"(sell ~{r['break_even_target']:,} vs {units:,})")
