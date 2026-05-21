"""
At which life-cycle STAGE do customers churn?
- For the 110 churned accounts, compute tenure_months_at_churn (signup -> last real churn event).
- Histogram of tenure at churn.
- Lifecycle stage bar chart: 0-3 / 3-6 / 6-12 / 12-18 / 18-24 months.
- Bonus: stage x reason_code, stage x industry.
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
churn_events = pd.read_csv(DATA / "ravenstack_churn_events.csv", parse_dates=["churn_date"])

# Real exit only (not reactivations)
real_churns = churn_events[~churn_events["is_reactivation"].astype(bool)]
last_churn = real_churns.groupby("account_id").agg(
    last_churn_date=("churn_date", "max"),
).reset_index()

# Latest reason for each churned account (most recent reason)
last_reason = (real_churns.sort_values("churn_date")
               .groupby("account_id").tail(1)[["account_id", "reason_code"]]
               .rename(columns={"reason_code": "last_reason"}))

churned = (accounts[accounts["churn_flag"]]
           .merge(last_churn, on="account_id", how="left")
           .merge(last_reason, on="account_id", how="left"))

# Some churn_flag=True accounts have no real churn event recorded — drop with note
no_event = churned["last_churn_date"].isna().sum()
churned = churned.dropna(subset=["last_churn_date"]).copy()
churned["tenure_days"] = (churned["last_churn_date"] - churned["signup_date"]).dt.days
churned["tenure_months"] = (churned["tenure_days"] // 30).astype(int)

print(f"Churned accounts total       : {accounts['churn_flag'].sum()}")
print(f"  with a real churn event    : {len(churned)}")
print(f"  without (dropped)          : {no_event}")
print()
print(f"Tenure at churn (months)     : min {churned['tenure_months'].min()}, median {churned['tenure_months'].median():.0f}, max {churned['tenure_months'].max()}")
print()

# --- Chart 1: histogram of tenure at churn ---
fig, ax = plt.subplots(figsize=(10, 5.5))
bins = np.arange(0, churned["tenure_months"].max() + 2) - 0.5
counts, edges, patches = ax.hist(churned["tenure_months"], bins=bins, color=BRAND_BLUE, edgecolor=BG_DARK)
ax.set_xlabel("Tenure at churn (months since signup)")
ax.set_ylabel("Number of churned customers")
ax.set_title("When do customers actually leave?", loc="left", pad=15)
median_t = churned["tenure_months"].median()
ax.axvline(median_t, color=BRAND_ORANGE, linestyle="--", linewidth=1.4, label=f"Median: month {median_t:.0f}")
ax.legend(facecolor=BG_DARK, edgecolor=FG_LIGHT, labelcolor=FG_LIGHT)
ax.set_xticks(range(0, int(churned["tenure_months"].max()) + 2, 2))
plt.tight_layout()
plt.savefig(CHARTS / "08_tenure_at_churn_hist.png", dpi=140)
plt.close()
print("saved -> 08_tenure_at_churn_hist.png")

# --- Chart 2: lifecycle stage bar ---
def stage(m):
    if m < 3:   return "Onboarding (0-3 mo)"
    if m < 6:   return "Activation (3-6 mo)"
    if m < 12:  return "Year 1 (6-12 mo)"
    if m < 18:  return "Renewal moment (12-18 mo)"
    return "Year 2+ (18+ mo)"

churned["stage"] = churned["tenure_months"].apply(stage)
stage_order = ["Onboarding (0-3 mo)", "Activation (3-6 mo)", "Year 1 (6-12 mo)",
               "Renewal moment (12-18 mo)", "Year 2+ (18+ mo)"]
stage_counts = churned["stage"].value_counts().reindex(stage_order).fillna(0).astype(int)
stage_pct = (stage_counts / stage_counts.sum() * 100).round(1)

print()
print("CHURN BY LIFECYCLE STAGE")
print("-" * 50)
for s in stage_order:
    print(f"  {s:<30}  {stage_counts[s]:>3}   ({stage_pct[s]:>4.1f}%)")
print()

fig, ax = plt.subplots(figsize=(11, 5.5))
colors = [BRAND_BLUE, BRAND_BLUE, BRAND_GREEN, BRAND_ORANGE, BRAND_ORANGE]
bars = ax.bar(stage_counts.index, stage_counts.values, color=colors, edgecolor=BG_DARK)
for bar, c, p in zip(bars, stage_counts.values, stage_pct.values):
    ax.text(bar.get_x() + bar.get_width()/2, c + 0.5, f"{c}\n({p:.0f}%)",
            ha="center", va="bottom", color=FG_LIGHT, fontsize=9)
ax.set_ylabel("Number of churned customers")
ax.set_title("At which lifecycle stage do customers leave?", loc="left", pad=15)
ax.set_ylim(0, max(stage_counts.values) * 1.22)
plt.xticks(rotation=0, ha="center")
plt.tight_layout()
plt.savefig(CHARTS / "09_lifecycle_stage_bar.png", dpi=140)
plt.close()
print("saved -> 09_lifecycle_stage_bar.png")

# --- Chart 3: stage x reason ---
print()
print("CHURN STAGE x REASON")
print("-" * 50)
stage_reason = pd.crosstab(churned["stage"], churned["last_reason"])
stage_reason = stage_reason.reindex(stage_order).fillna(0).astype(int)
print(stage_reason.to_string())

fig, ax = plt.subplots(figsize=(11, 6))
reason_colors = [BRAND_BLUE, BRAND_GREEN, BRAND_ORANGE, "#7FB7FF", "#A8E6CF", "#FFB280"]
stage_reason.plot(kind="bar", stacked=True, color=reason_colors[:stage_reason.shape[1]],
                  ax=ax, edgecolor=BG_DARK)
ax.set_ylabel("Number of churned customers")
ax.set_xlabel("")
ax.set_title("Stage of churn, split by stated reason", loc="left", pad=15)
ax.legend(title="Reason code", facecolor=BG_DARK, edgecolor=FG_LIGHT, labelcolor=FG_LIGHT,
          title_fontsize=9, fontsize=9, loc="upper left")
plt.xticks(rotation=15, ha="right")
plt.tight_layout()
plt.savefig(CHARTS / "10_stage_x_reason.png", dpi=140)
plt.close()
print("saved -> 10_stage_x_reason.png")

print("\nDone.")
