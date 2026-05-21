"""
Statistical evidence for the pricing study.

1. Correlation matrix of numeric features
2. Linear regression on lifetime revenue (LTV) — what drives revenue, in $
3. Logistic regression on churn — what drives the binary churn outcome, as odds ratios
4. Forest plot of the key coefficients
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm

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

# ============================================================
# 1. Load and build per-account dataset
# ============================================================
accounts = pd.read_csv(DATA / "ravenstack_accounts.csv", parse_dates=["signup_date"])
subs = pd.read_csv(DATA / "ravenstack_subscriptions.csv", parse_dates=["start_date", "end_date"])
tickets = pd.read_csv(DATA / "ravenstack_support_tickets.csv", parse_dates=["submitted_at"])
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

def first_plan(g): return g.sort_values("start_date").iloc[0]["plan_tier"]

per_acc = subs.groupby("account_id").agg(
    total_revenue=("revenue", "sum"),
    n_subscriptions=("subscription_id", "count"),
    n_upgrades=("upgrade_flag", "sum"),
    n_downgrades=("downgrade_flag", "sum"),
    tenure_months=("duration_months", "sum"),
).reset_index()
per_acc["landing_plan"] = subs.groupby("account_id").apply(first_plan, include_groups=False).reset_index(drop=True).values
per_acc = per_acc.merge(accounts[["account_id", "referral_source", "industry", "country", "churn_flag", "seats"]], on="account_id", how="left")
per_acc["billing"] = (subs.groupby("account_id")["billing_frequency"]
                     .agg(lambda s: s.mode().iloc[0]).reset_index(drop=True).values)
per_acc["n_tickets"] = per_acc["account_id"].map(tickets.groupby("account_id").size()).fillna(0).astype(int)
per_acc["upgraded"] = (per_acc["n_upgrades"] > 0).astype(int)
per_acc["is_event"] = (per_acc["referral_source"] == "event").astype(int)
per_acc["is_partner"] = (per_acc["referral_source"] == "partner").astype(int)
per_acc["is_organic"] = (per_acc["referral_source"] == "organic").astype(int)
per_acc["is_devtools"] = (per_acc["industry"] == "DevTools").astype(int)
per_acc["is_annual"] = (per_acc["billing"] == "annual").astype(int)
per_acc["is_enterprise_land"] = (per_acc["landing_plan"] == "Enterprise").astype(int)
per_acc["is_pro_land"] = (per_acc["landing_plan"] == "Pro").astype(int)
per_acc["churn"] = per_acc["churn_flag"].astype(int)

print(f"Accounts: {len(per_acc)}  | Churned: {per_acc['churn'].sum()}  | Upgraded: {per_acc['upgraded'].sum()}")
print()

# ============================================================
# 2. Correlation matrix
# ============================================================
print("=" * 60)
print("CORRELATION MATRIX")
print("=" * 60)
numeric_cols = ["total_revenue", "tenure_months", "n_upgrades", "n_subscriptions", "n_tickets", "seats", "churn"]
corr = per_acc[numeric_cols].corr().round(2)
print(corr.to_string())
print()

# Heatmap of correlations
fig, ax = plt.subplots(figsize=(8, 6.5))
im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
labels = ["LTV", "Tenure", "Upgrades", "Subs", "Tickets", "Seats", "Churn"]
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=20, ha="right")
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
ax.set_title("Correlation matrix — per-customer numeric features", loc="left", pad=15)
for i in range(len(labels)):
    for j in range(len(labels)):
        v = corr.values[i, j]
        ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                color="black" if abs(v) < 0.5 else "white", fontsize=9.5, fontweight="bold")
cbar = plt.colorbar(im, ax=ax, label="Pearson correlation")
cbar.ax.yaxis.label.set_color(FG_LIGHT); cbar.ax.tick_params(colors=FG_LIGHT)
plt.tight_layout()
plt.savefig(CHARTS / "20_correlation_matrix.png", dpi=140)
plt.close()
print("saved -> 20_correlation_matrix.png")

# ============================================================
# 3. Linear regression on LTV
# ============================================================
print()
print("=" * 60)
print("LINEAR REGRESSION on LTV (in $)")
print("=" * 60)
# Reference categories: Basic landing, monthly billing, event channel
# Coefficients tell us $-impact relative to that baseline
features_ltv = ["tenure_months", "n_upgrades",
                "is_partner", "is_organic",  # channel relative to event baseline
                "is_pro_land", "is_enterprise_land",  # plan relative to Basic
                "is_annual", "is_devtools", "seats"]
X = sm.add_constant(per_acc[features_ltv].astype(float))
y = per_acc["total_revenue"].astype(float)
ols = sm.OLS(y, X).fit()
print(ols.summary().tables[1])
print(f"R-squared: {ols.rsquared:.3f}  |  Adj R-squared: {ols.rsquared_adj:.3f}  |  N: {int(ols.nobs)}")
print()

# ============================================================
# 4. Logistic regression on churn
# ============================================================
print("=" * 60)
print("LOGISTIC REGRESSION on CHURN (odds ratios)")
print("=" * 60)
features_churn = ["tenure_months",
                  "is_partner", "is_organic",
                  "is_pro_land", "is_enterprise_land",
                  "is_annual", "is_devtools", "seats", "n_tickets"]
X2 = sm.add_constant(per_acc[features_churn].astype(float))
y2 = per_acc["churn"].astype(int)
logit = sm.Logit(y2, X2).fit(disp=False)
print(logit.summary().tables[1])

# Convert to odds ratios
odds = pd.DataFrame({
    "coef": logit.params,
    "odds_ratio": np.exp(logit.params),
    "p_value": logit.pvalues,
    "CI_low": np.exp(logit.conf_int()[0]),
    "CI_high": np.exp(logit.conf_int()[1]),
}).round(3)
print()
print("Odds ratios (>1 = more churn, <1 = less churn):")
print(odds.to_string())
print()

# ============================================================
# 5. Coefficient forest plot — LTV regression (most interpretable)
# ============================================================
plot_vars = {
    "n_upgrades":         "Per upgrade event",
    "is_partner":         "Partner channel (vs event)",
    "is_organic":         "Organic channel (vs event)",
    "is_pro_land":        "Pro landing (vs Basic)",
    "is_enterprise_land": "Enterprise landing (vs Basic)",
    "is_annual":          "Annual billing (vs monthly)",
    "is_devtools":        "DevTools industry",
    "seats":              "Per seat",
}
plot_df = pd.DataFrame({
    "label": [plot_vars[v] for v in plot_vars],
    "coef":  [ols.params[v] for v in plot_vars],
    "ci_lo": [ols.conf_int().loc[v, 0] for v in plot_vars],
    "ci_hi": [ols.conf_int().loc[v, 1] for v in plot_vars],
    "p":     [ols.pvalues[v] for v in plot_vars],
}).sort_values("coef")

fig, ax = plt.subplots(figsize=(11, 6.5))
y_pos = np.arange(len(plot_df))
colors = [BRAND_GREEN if c > 0 else BRAND_ORANGE for c in plot_df["coef"]]
ax.errorbar(plot_df["coef"], y_pos,
            xerr=[plot_df["coef"] - plot_df["ci_lo"], plot_df["ci_hi"] - plot_df["coef"]],
            fmt="none", ecolor=FG_LIGHT, capsize=4, linewidth=1.2, alpha=0.6)
ax.scatter(plot_df["coef"], y_pos, s=80, c=colors, edgecolors=FG_LIGHT, linewidth=0.6, zorder=3)
ax.axvline(0, color=FG_LIGHT, linestyle="--", linewidth=1, alpha=0.5)
ax.set_yticks(y_pos)
ax.set_yticklabels(plot_df["label"])
ax.set_xlabel("Estimated effect on lifetime revenue (USD)")
ax.set_title("What drives lifetime revenue — regression coefficients with 95% CI", loc="left", pad=15)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:+.0f}k" if abs(x) >= 1000 else f"${x:+.0f}"))
ax.grid(True, axis="x", alpha=0.12, color=FG_LIGHT)
# annotate p-values
for i, row in plot_df.reset_index(drop=True).iterrows():
    p_label = "***" if row["p"] < 0.001 else ("**" if row["p"] < 0.01 else ("*" if row["p"] < 0.05 else "n.s."))
    ax.text(row["ci_hi"] + max(plot_df["ci_hi"]) * 0.02, i,
            p_label, va="center", color=FG_LIGHT, fontsize=9)
plt.tight_layout()
plt.savefig(CHARTS / "21_ltv_regression_forest.png", dpi=140)
plt.close()
print("saved -> 21_ltv_regression_forest.png")

print()
print("Done.")
