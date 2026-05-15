"""Product margin waterfall (command-line version).

Same logic as js/gross-to-net.js. Run:
    python gross_to_net.py
"""


def margin_waterfall(gross, rebates, discounts, markups, cogs, opex, other):
    net_price = gross - rebates - discounts + markups
    gross_margin = net_price - cogs
    operating_profit = gross_margin - opex - other

    def pct(v):
        return (v / net_price * 100) if net_price > 0 else 0.0

    markup_on_cogs = ((net_price - cogs) / cogs * 100) if cogs > 0 else 0.0
    return {
        "net_price": net_price,
        "gross_margin": gross_margin,
        "operating_profit": operating_profit,
        "gross_margin_pct": pct(gross_margin),
        "operating_margin_pct": pct(operating_profit),
        "markup_on_cogs": markup_on_cogs,
    }


def _ask(prompt, default):
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        value = float(raw)
        return value if value >= 0 else default
    except ValueError:
        return default


if __name__ == "__main__":
    print("Product Margin Simulator")
    gross = _ask("Gross / List Price", 1000)
    rebates = _ask("Rebates (-)", 50)
    discounts = _ask("Discounts (-)", 100)
    markups = _ask("Markups / Surcharges (+)", 0)
    cogs = _ask("COGS (-)", 450)
    opex = _ask("OpEx (-)", 150)
    other = _ask("Other costs (-)", 30)

    r = margin_waterfall(gross, rebates, discounts, markups, cogs, opex, other)
    print("\n--- Margin Waterfall ---")
    print(f"Gross / List Price   {gross:,.2f}")
    print(f"  Rebates           -{rebates:,.2f}")
    print(f"  Discounts         -{discounts:,.2f}")
    print(f"  Markups           +{markups:,.2f}")
    print(f"= Net Price          {r['net_price']:,.2f}")
    print(f"  COGS              -{cogs:,.2f}")
    print(f"= Gross Margin       {r['gross_margin']:,.2f}  ({r['gross_margin_pct']:.1f}%)")
    print(f"  OpEx              -{opex:,.2f}")
    print(f"  Other             -{other:,.2f}")
    print(f"= Operating Profit   {r['operating_profit']:,.2f}  ({r['operating_margin_pct']:.1f}%)")
    print(f"\nMarkup on COGS: {r['markup_on_cogs']:.1f}%")
