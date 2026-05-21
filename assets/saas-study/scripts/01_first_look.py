"""
First look at the RavenStack SaaS churn dataset.
Headline numbers + churn breakdowns by plan, industry, country.
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(r"C:\Users\Lenovo\OneDrive\Creative\Churn Study")
DATA = ROOT / "data"
CHARTS = ROOT / "charts"

BRAND_BLUE   = "#2F9BFF"
BRAND_GREEN  = "#19C37D"
BRAND_ORANGE = "#FF6500"
BG_DARK      = "#0F1419"
FG_LIGHT     = "#E6EDF3"

plt.rcParams.update({
    "figure.facecolor": BG_DARK,
    "axes.facecolor":   BG_DARK,
    "savefig.facecolor": BG_DARK,
    "axes.edgecolor":   FG_LIGHT,
    "axes.labelcolor":  FG_LIGHT,
    "xtick.color":      FG_LIGHT,
    "ytick.color":      FG_LIGHT,
    "text.color":       FG_LIGHT,
    "axes.titlesize":   13,
    "axes.titleweight": "bold",
    "font.size":        10,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
})

accounts = pd.read_csv(DATA / "ravenstack_accounts.csv")
print(f"Loaded {len(accounts)} accounts.\n")

# 1. Headline churn rate
total = len(accounts)
churned = int(accounts["churn_flag"].sum())
churn_rate = churned / total
print("=" * 60)
print("1. HEADLINE NUMBER")
print("=" * 60)
print(f"Total customers : {total}")
print(f"Churned         : {churned}")
print(f"Churn rate      : {churn_rate:.1%}")
print()

def churn_breakdown(df, by):
    g = df.groupby(by).agg(
        customers=("account_id", "count"),
        churned=("churn_flag", "sum"),
    )
    g["churn_rate"] = g["churned"] / g["customers"]
    return g.sort_values("churn_rate", ascending=False)

def bar_chart(series, title, filename, color=BRAND_BLUE, overall=None):
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(series.index[::-1], (series.values[::-1] * 100), color=color)
    ax.set_xlabel("Churn rate (%)")
    ax.set_title(title, loc="left", pad=15)
    for bar, v in zip(bars, series.values[::-1] * 100):
        ax.text(v + 0.4, bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}%", va="center", color=FG_LIGHT, fontsize=9)
    if overall is not None:
        ax.axvline(overall * 100, color=BRAND_ORANGE, linestyle="--", linewidth=1.2,
                   label=f"Overall: {overall:.1%}")
        ax.legend(loc="lower right", facecolor=BG_DARK, edgecolor=FG_LIGHT, labelcolor=FG_LIGHT)
    ax.set_xlim(0, max(series.values * 100) * 1.18)
    plt.tight_layout()
    out = CHARTS / filename
    plt.savefig(out, dpi=140)
    plt.close()
    print(f"  saved -> {out.name}")

# 2. By plan tier
print("=" * 60)
print("2. CHURN BY PLAN TIER")
print("=" * 60)
plan = churn_breakdown(accounts, "plan_tier")
print(plan.to_string(formatters={"churn_rate": "{:.1%}".format}))
print()
bar_chart(plan["churn_rate"], "Churn rate by plan tier", "01_churn_by_plan.png",
          color=BRAND_BLUE, overall=churn_rate)

# 3. By industry
print("=" * 60)
print("3. CHURN BY INDUSTRY")
print("=" * 60)
industry = churn_breakdown(accounts, "industry")
print(industry.to_string(formatters={"churn_rate": "{:.1%}".format}))
print()
bar_chart(industry["churn_rate"], "Churn rate by industry", "02_churn_by_industry.png",
          color=BRAND_GREEN, overall=churn_rate)

# 4. By country
print("=" * 60)
print("4. CHURN BY COUNTRY")
print("=" * 60)
country = churn_breakdown(accounts, "country")
print(country.to_string(formatters={"churn_rate": "{:.1%}".format}))
print()
bar_chart(country["churn_rate"], "Churn rate by country", "03_churn_by_country.png",
          color=BRAND_ORANGE, overall=churn_rate)

# 5. By referral source
print("=" * 60)
print("5. CHURN BY REFERRAL SOURCE")
print("=" * 60)
ref = churn_breakdown(accounts, "referral_source")
print(ref.to_string(formatters={"churn_rate": "{:.1%}".format}))
print()
bar_chart(ref["churn_rate"], "Churn rate by acquisition channel", "04_churn_by_referral.png",
          color=BRAND_BLUE, overall=churn_rate)

print("Done. Charts in:", CHARTS)
