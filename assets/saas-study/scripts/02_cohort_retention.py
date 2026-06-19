"""
Cohort retention analysis for RavenStack SaaS.

Question: do customers churn early (onboarding problem) or late (value erosion)?
Method:
  - Cohort each customer by their signup month.
  - For churned customers, exit_date = latest churn event date (or observation end if none).
  - For active customers, exit_date = observation end.
  - Survival at month N = share of cohort whose tenure >= N months.
  - Only show months where all members of the cohort had a fair chance to be observed.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

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

# Observation cutoff = latest date we see anywhere
obs_end = max(accounts["signup_date"].max(), churn_events["churn_date"].max())
print(f"Observation cutoff: {obs_end.date()}")

# For each churned account, find the latest churn event (excluding reactivations)
real_churns = churn_events[~churn_events["is_reactivation"].astype(bool)]
last_churn = real_churns.groupby("account_id")["churn_date"].max().rename("last_churn_date")

df = accounts.merge(last_churn, on="account_id", how="left")

# exit_date: for churned customers, last_churn_date if available, else obs_end
# for active, obs_end
df["exit_date"] = np.where(
    df["churn_flag"],
    df["last_churn_date"].fillna(obs_end),
    obs_end,
)
df["exit_date"] = pd.to_datetime(df["exit_date"])

# Tenure in whole months (floor)
df["tenure_days"] = (df["exit_date"] - df["signup_date"]).dt.days
df["tenure_months"] = (df["tenure_days"] // 30).astype(int)

# Observable months (how many months has this customer had a chance to exist?)
df["observable_days"] = (obs_end - df["signup_date"]).dt.days
df["observable_months"] = (df["observable_days"] // 30).astype(int)

# Cohort = signup year-month
df["cohort"] = df["signup_date"].dt.to_period("M").astype(str)

print(f"Total customers: {len(df)}  |  Churned: {df['churn_flag'].sum()}")
print(f"Tenure (months) — min/median/max: {df['tenure_months'].min()} / {df['tenure_months'].median():.0f} / {df['tenure_months'].max()}")
print()

# --- Build cohort survival table ---
# For each cohort, for each month_since_signup M:
#   - only include if cohort has observable_months >= M
#   - survival = share of members with tenure_months >= M

max_m = int(df["observable_months"].max())
cohorts = sorted(df["cohort"].unique())

survival = pd.DataFrame(index=cohorts, columns=range(max_m + 1), dtype=float)
for c in cohorts:
    sub = df[df["cohort"] == c]
    # use MIN observable so every cell is a fair comparison (no censoring bias)
    cohort_observable = int(sub["observable_months"].min())
    n = len(sub)
    for m in range(cohort_observable + 1):
        alive = (sub["tenure_months"] >= m).sum()
        survival.loc[c, m] = alive / n
    # cells beyond cohort_observable stay NaN

# --- Group cohorts into quarters for a readable line chart ---
df["cohort_q"] = df["signup_date"].dt.to_period("Q").astype(str)
quarters = sorted(df["cohort_q"].unique())
survival_q = pd.DataFrame(index=quarters, columns=range(max_m + 1), dtype=float)
for q in quarters:
    sub = df[df["cohort_q"] == q]
    q_observable = int(sub["observable_months"].min())
    n = len(sub)
    for m in range(q_observable + 1):
        survival_q.loc[q, m] = (sub["tenure_months"] >= m).sum() / n

print("Quarterly cohort survival (%):")
print((survival_q * 100).round(1).to_string(na_rep="-"))
print()

# --- Chart 1: survival curves by quarterly cohort ---
fig, ax = plt.subplots(figsize=(10, 6))
cmap = LinearSegmentedColormap.from_list("brand", [BRAND_BLUE, BRAND_GREEN, BRAND_ORANGE])
colors = [cmap(i / max(1, len(quarters) - 1)) for i in range(len(quarters))]
for q, color in zip(quarters, colors):
    series = survival_q.loc[q].dropna()
    ax.plot(series.index, series.values * 100, marker="o", markersize=4,
            linewidth=2, color=color, label=q)
ax.set_xlabel("Months since signup")
ax.set_ylabel("Share of cohort still active (%)")
ax.set_title("Cohort retention by signup quarter", loc="left", pad=15)
ax.set_ylim(0, 105)
ax.grid(True, alpha=0.15, color=FG_LIGHT)
ax.legend(title="Signup quarter", facecolor=BG_DARK, edgecolor=FG_LIGHT,
          labelcolor=FG_LIGHT, title_fontsize=9, fontsize=9)
plt.tight_layout()
plt.savefig(CHARTS / "05_cohort_curves.png", dpi=140)
plt.close()
print("saved -> 05_cohort_curves.png")

# --- Chart 2: pooled survival curve with 95% confidence band ---
# Pool ALL customers, weight by exposure
pooled = []
for m in range(max_m + 1):
    eligible = df[df["observable_months"] >= m]
    if len(eligible) < 10:  # too thin to be meaningful
        break
    alive_share = (eligible["tenure_months"] >= m).mean()
    n = len(eligible)
    se = np.sqrt(alive_share * (1 - alive_share) / n)
    pooled.append({"m": m, "survival": alive_share, "n": n, "se": se})
pooled = pd.DataFrame(pooled)

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(pooled["m"], pooled["survival"] * 100, color=BRAND_BLUE, linewidth=2.5, marker="o")
ax.fill_between(pooled["m"],
                (pooled["survival"] - 1.96 * pooled["se"]) * 100,
                (pooled["survival"] + 1.96 * pooled["se"]) * 100,
                color=BRAND_BLUE, alpha=0.15, label="95% confidence band")
ax.set_xlabel("Months since signup")
ax.set_ylabel("Share of customers still active (%)")
ax.set_title("Pooled retention curve (all cohorts combined)", loc="left", pad=15)
ax.set_ylim(0, 105)
ax.grid(True, alpha=0.15, color=FG_LIGHT)
ax.legend(facecolor=BG_DARK, edgecolor=FG_LIGHT, labelcolor=FG_LIGHT)
plt.tight_layout()
plt.savefig(CHARTS / "06_pooled_retention.png", dpi=140)
plt.close()
print("saved -> 06_pooled_retention.png")

print("\nPooled survival (%):")
print(pooled.assign(survival_pct=lambda x: (x["survival"]*100).round(1))[["m", "survival_pct", "n"]].to_string(index=False))

# --- Chart 3: cohort heatmap (monthly cohorts × months since signup) ---
fig, ax = plt.subplots(figsize=(13, 8))
heatmap_data = (survival * 100).astype(float)
im = ax.imshow(heatmap_data.values, aspect="auto", cmap="viridis", vmin=0, vmax=100)
ax.set_yticks(range(len(cohorts)))
ax.set_yticklabels(cohorts, fontsize=8)
ax.set_xticks(range(0, max_m + 1, 2))
ax.set_xticklabels(range(0, max_m + 1, 2))
ax.set_xlabel("Months since signup")
ax.set_ylabel("Signup month (cohort)")
ax.set_title("Cohort retention heatmap (% still active)", loc="left", pad=15)
# annotate cells
for i, c in enumerate(cohorts):
    for m in range(max_m + 1):
        v = heatmap_data.iat[i, m]
        if pd.notna(v):
            ax.text(m, i, f"{v:.0f}", ha="center", va="center", fontsize=6,
                    color=FG_LIGHT if v < 60 else "#000000")
cbar = plt.colorbar(im, ax=ax, label="% still active")
cbar.ax.yaxis.label.set_color(FG_LIGHT)
cbar.ax.tick_params(colors=FG_LIGHT)
plt.tight_layout()
plt.savefig(CHARTS / "07_cohort_heatmap.png", dpi=140)
plt.close()
print("saved -> 07_cohort_heatmap.png")

# --- Headline insight: drop in the first 3 months vs rest ---
first_3 = pooled.set_index("m")
m0 = first_3.loc[0, "survival"]
if 3 in first_3.index:
    m3 = first_3.loc[3, "survival"]
    print(f"\nRetention M0->M3: {m0:.1%} -> {m3:.1%}  (drop of {(m0-m3):.1%} in first 3 months)")
if 6 in first_3.index:
    m6 = first_3.loc[6, "survival"]
    print(f"Retention M0->M6: {m0:.1%} -> {m6:.1%}  (drop of {(m0-m6):.1%} in first 6 months)")
if 12 in first_3.index:
    m12 = first_3.loc[12, "survival"]
    print(f"Retention M0->M12: {m0:.1%} -> {m12:.1%}")

print("\nDone.")
