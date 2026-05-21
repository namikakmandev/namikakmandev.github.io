"""
Scatter: tenure vs lifetime revenue, per customer.
Color = landing plan. Marker = upgraded vs not upgraded.
Shows the individual distribution behind the bar-chart summaries.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(r"C:\Users\Lenovo\OneDrive\Creative\Churn Study")
DATA = ROOT / "data"
CHARTS = ROOT / "charts"

BRAND_BLUE, BRAND_GREEN, BRAND_ORANGE = "#2F9BFF", "#19C37D", "#FF6500"
BG_DARK, FG_LIGHT = "#0F1419", "#E6EDF3"
plt.rcParams.update({
    "figure.facecolor": BG_DARK, "axes.facecolor": BG_DARK, "savefig.facecolor": BG_DARK,
    "axes.edgecolor": FG_LIGHT, "axes.labelcolor": FG_LIGHT,
    "xtick.color": FG_LIGHT, "ytick.color": FG_LIGHT, "text.color": FG_LIGHT,
    "axes.titlesize": 13, "axes.titleweight": "bold", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
})

accounts = pd.read_csv(DATA / "ravenstack_accounts.csv", parse_dates=["signup_date"])
subs = pd.read_csv(DATA / "ravenstack_subscriptions.csv", parse_dates=["start_date", "end_date"])
churn_events = pd.read_csv(DATA / "ravenstack_churn_events.csv", parse_dates=["churn_date"])
obs_end = pd.Timestamp("2024-12-31")

real_churns = churn_events[~churn_events["is_reactivation"].astype(bool)]
last_churn = real_churns.groupby("account_id")["churn_date"].max().rename("last_churn_date")
acc = accounts.merge(last_churn, on="account_id", how="left")
acc["exit_date"] = pd.to_datetime(np.where(acc["churn_flag"], acc["last_churn_date"].fillna(obs_end), obs_end))

subs = subs.sort_values(["account_id", "start_date"]).reset_index(drop=True)
subs = subs.merge(acc[["account_id", "exit_date"]], on="account_id", how="left")
subs["next_start"] = subs.groupby("account_id")["start_date"].shift(-1)
subs["effective_end"] = subs[["end_date", "next_start", "exit_date"]].min(axis=1)
subs["effective_end"] = subs[["effective_end", "exit_date"]].min(axis=1)
subs["duration_months"] = ((subs["effective_end"] - subs["start_date"]).dt.days / 30).clip(lower=0)
subs["revenue"] = subs["mrr_amount"] * subs["duration_months"]

plan_order = ["Basic", "Pro", "Enterprise"]
plan_rank = {p: i for i, p in enumerate(plan_order)}

def first_plan(g): return g.sort_values("start_date").iloc[0]["plan_tier"]

per_acc = subs.groupby("account_id").agg(
    total_revenue=("revenue", "sum"),
    tenure_months=("duration_months", "sum"),
    n_upgrades=("upgrade_flag", "sum"),
).reset_index()
per_acc["landing_plan"] = subs.groupby("account_id").apply(first_plan, include_groups=False).reset_index(drop=True).values
per_acc["upgraded"] = per_acc["n_upgrades"] > 0

# --- Build the scatter ---
fig, ax = plt.subplots(figsize=(11, 6.5))

plan_colors = {"Basic": BRAND_BLUE, "Pro": BRAND_GREEN, "Enterprise": BRAND_ORANGE}

# 6 groups: each plan x (upgraded/not)
for plan in plan_order:
    for upgraded, marker, alpha, label_suffix in [
        (True,  "o", 0.85, "upgraded"),
        (False, "x", 0.55, "no upgrade"),
    ]:
        sub = per_acc[(per_acc["landing_plan"] == plan) & (per_acc["upgraded"] == upgraded)]
        if len(sub) == 0:
            continue
        ax.scatter(sub["tenure_months"], sub["total_revenue"],
                   s=42, c=plan_colors[plan], marker=marker,
                   alpha=alpha, edgecolors=FG_LIGHT if upgraded else "none", linewidth=0.4,
                   label=f"{plan} — {label_suffix} (n={len(sub)})")

# Median lines for the 3 landing-plan cohorts (visual anchor)
for plan in plan_order:
    g = per_acc[per_acc["landing_plan"] == plan]
    median_rev = g["total_revenue"].median()
    ax.axhline(median_rev, color=plan_colors[plan], linestyle="--", linewidth=0.7, alpha=0.35)

ax.set_xlabel("Customer tenure (months)")
ax.set_ylabel("Lifetime revenue (USD)")
ax.set_title("Every customer: tenure vs lifetime revenue", loc="left", pad=15)
ax.grid(True, alpha=0.12, color=FG_LIGHT)

# Format y-axis as currency
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))

ax.legend(facecolor=BG_DARK, edgecolor=FG_LIGHT, labelcolor=FG_LIGHT,
          loc="upper left", fontsize=8.5, ncol=2, framealpha=0.85)

plt.tight_layout()
out = CHARTS / "19_scatter_tenure_vs_revenue.png"
plt.savefig(out, dpi=140)
plt.close()
print(f"saved -> {out.name}")

# Print quick stats for the markdown narrative
print()
print("Quick stats (median LTV by group):")
g = per_acc.groupby(["landing_plan", "upgraded"]).agg(
    n=("account_id", "count"),
    median_ltv=("total_revenue", "median"),
    mean_ltv=("total_revenue", "mean"),
    median_tenure=("tenure_months", "median"),
).round(1)
print(g.to_string())
