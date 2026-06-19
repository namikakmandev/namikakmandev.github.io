"""
PRICING STRATEGY: cheap-and-upsell vs high-margin.

For each customer, reconstruct the subscription timeline and compute
lifetime revenue. Compare strategies by landing plan, upgrade behaviour,
acquisition channel, and billing frequency.

The bottom-line question: which acquisition + plan strategy actually
generates the most revenue per acquired customer?
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

# Per-account exit date
real_churns = churn_events[~churn_events["is_reactivation"].astype(bool)]
last_churn = real_churns.groupby("account_id")["churn_date"].max().rename("last_churn_date")
acc = accounts.merge(last_churn, on="account_id", how="left")
acc["exit_date"] = pd.to_datetime(np.where(acc["churn_flag"], acc["last_churn_date"].fillna(obs_end), obs_end))

# --- Reconstruct subscription durations ---
# For each subscription, end = end_date if known, else next sub's start_date for same account, else exit_date
subs = subs.sort_values(["account_id", "start_date"]).reset_index(drop=True)
subs = subs.merge(acc[["account_id", "exit_date"]], on="account_id", how="left")
subs["next_start"] = subs.groupby("account_id")["start_date"].shift(-1)
subs["effective_end"] = subs[["end_date", "next_start", "exit_date"]].min(axis=1)
subs["effective_end"] = pd.to_datetime(subs["effective_end"])
# Clip to exit_date
subs["effective_end"] = subs[["effective_end", "exit_date"]].min(axis=1)
subs["duration_days"] = (subs["effective_end"] - subs["start_date"]).dt.days.clip(lower=0)
subs["duration_months"] = subs["duration_days"] / 30
subs["revenue"] = subs["mrr_amount"] * subs["duration_months"]

# --- Per-account roll-up ---
plan_order = ["Basic", "Pro", "Enterprise"]
plan_rank = {p: i for i, p in enumerate(plan_order)}

def first_plan(g):
    return g.sort_values("start_date").iloc[0]["plan_tier"]

def highest_plan(g):
    return max(g["plan_tier"], key=lambda x: plan_rank[x])

per_acc = (subs.groupby("account_id").agg(
    total_revenue=("revenue", "sum"),
    n_subscriptions=("subscription_id", "count"),
    n_upgrades=("upgrade_flag", "sum"),
    n_downgrades=("downgrade_flag", "sum"),
    tenure_months=("duration_months", "sum"),
).reset_index())
per_acc["landing_plan"]  = subs.groupby("account_id").apply(first_plan, include_groups=False).reset_index(drop=True).values
per_acc["highest_plan"]  = subs.groupby("account_id").apply(highest_plan, include_groups=False).reset_index(drop=True).values

per_acc = per_acc.merge(accounts[["account_id", "referral_source", "industry",
                                    "country", "churn_flag", "is_trial"]],
                        on="account_id", how="left")
# Most-used billing frequency per account
per_acc["billing"] = (subs.groupby("account_id")["billing_frequency"]
                     .agg(lambda s: s.mode().iloc[0])
                     .reset_index(drop=True).values)
per_acc["upgraded"] = per_acc["n_upgrades"] > 0

print(f"Accounts: {len(per_acc)} | total revenue computed across {len(subs)} sub-records")
print(f"Median LTV: ${per_acc['total_revenue'].median():,.0f}")
print(f"Mean LTV:   ${per_acc['total_revenue'].mean():,.0f}")
print()

# ============================================================
# Q1. LTV by LANDING plan (where they entered)
# ============================================================
print("=" * 60)
print("Q1. LTV by LANDING plan (the plan they signed up on)")
print("=" * 60)
ltv_by_land = per_acc.groupby("landing_plan").agg(
    n=("account_id", "count"),
    mean_ltv=("total_revenue", "mean"),
    median_ltv=("total_revenue", "median"),
    avg_tenure_mo=("tenure_months", "mean"),
    churn_rate=("churn_flag", "mean"),
    upgrade_share=("upgraded", "mean"),
).reindex(plan_order).round(0)
ltv_by_land["churn_rate"] = ltv_by_land["churn_rate"] / 100  # back to fraction display
# Note: I kept churn_rate as a proper fraction
ltv_by_land = per_acc.groupby("landing_plan").agg(
    n=("account_id", "count"),
    mean_ltv=("total_revenue", "mean"),
    median_ltv=("total_revenue", "median"),
    avg_tenure_mo=("tenure_months", "mean"),
    churn_rate=("churn_flag", "mean"),
    upgrade_share=("upgraded", "mean"),
).reindex(plan_order)
print(ltv_by_land.assign(
    mean_ltv=lambda x: x["mean_ltv"].map("${:,.0f}".format),
    median_ltv=lambda x: x["median_ltv"].map("${:,.0f}".format),
    avg_tenure_mo=lambda x: x["avg_tenure_mo"].round(1),
    churn_rate=lambda x: (x["churn_rate"] * 100).round(1).astype(str) + "%",
    upgrade_share=lambda x: (x["upgrade_share"] * 100).round(1).astype(str) + "%",
).to_string())
print()

# Chart 1: mean LTV by landing plan
fig, ax = plt.subplots(figsize=(9, 5.5))
colors = [BRAND_BLUE, BRAND_GREEN, BRAND_ORANGE]
vals = ltv_by_land["mean_ltv"].values
bars = ax.bar(plan_order, vals, color=colors, edgecolor=BG_DARK)
for bar, v, n in zip(bars, vals, ltv_by_land["n"].values):
    ax.text(bar.get_x() + bar.get_width()/2, v + max(vals)*0.015,
            f"${v:,.0f}\n(n={n})", ha="center", va="bottom", color=FG_LIGHT, fontsize=10)
ax.set_ylabel("Mean lifetime revenue per customer (USD)")
ax.set_title("Mean LTV by landing plan", loc="left", pad=15)
ax.set_ylim(0, max(vals) * 1.18)
plt.tight_layout(); plt.savefig(CHARTS / "14_ltv_by_landing_plan.png", dpi=140); plt.close()
print("saved -> 14_ltv_by_landing_plan.png")

# ============================================================
# Q2. The cheap-and-upsell path: Basic landers split by upgrade behaviour
# ============================================================
print("=" * 60)
print("Q2. CHEAP-AND-UPSELL vs HIGH-MARGIN — strategy comparison")
print("=" * 60)
strategies = {}
basic = per_acc[per_acc["landing_plan"] == "Basic"]
basic_upsold = basic[basic["upgraded"]]
basic_only = basic[~basic["upgraded"]]
ent_landers = per_acc[per_acc["landing_plan"] == "Enterprise"]
pro_landers = per_acc[per_acc["landing_plan"] == "Pro"]

strategies["Basic land, no upgrade"]  = basic_only
strategies["Basic land, upgraded"]    = basic_upsold
strategies["Pro land"]                = pro_landers
strategies["Enterprise land"]         = ent_landers

rows = []
for name, df in strategies.items():
    rows.append({
        "strategy": name,
        "n": len(df),
        "share": len(df) / len(per_acc),
        "mean_ltv": df["total_revenue"].mean(),
        "median_ltv": df["total_revenue"].median(),
        "avg_tenure_mo": df["tenure_months"].mean(),
        "churn_rate": df["churn_flag"].mean(),
    })
strat_df = pd.DataFrame(rows)
print(strat_df.assign(
    share=lambda x: (x["share"] * 100).round(1).astype(str) + "%",
    mean_ltv=lambda x: x["mean_ltv"].map("${:,.0f}".format),
    median_ltv=lambda x: x["median_ltv"].map("${:,.0f}".format),
    avg_tenure_mo=lambda x: x["avg_tenure_mo"].round(1),
    churn_rate=lambda x: (x["churn_rate"] * 100).round(1).astype(str) + "%",
).to_string(index=False))
print()

# Chart 2: strategy comparison
fig, ax = plt.subplots(figsize=(11, 6))
sc = strat_df.copy()
colors2 = [BRAND_BLUE, BRAND_GREEN, "#7FB7FF", BRAND_ORANGE]
bars = ax.bar(sc["strategy"], sc["mean_ltv"], color=colors2, edgecolor=BG_DARK)
for bar, v, n, s in zip(bars, sc["mean_ltv"], sc["n"], sc["share"]):
    ax.text(bar.get_x() + bar.get_width()/2, v + max(sc["mean_ltv"])*0.015,
            f"${v:,.0f}\n(n={n}, {s:.0%} of base)", ha="center", va="bottom",
            color=FG_LIGHT, fontsize=9)
ax.set_ylabel("Mean lifetime revenue per customer (USD)")
ax.set_title("Cheap-and-upsell vs high-margin: which strategy pays?", loc="left", pad=15)
ax.set_ylim(0, max(sc["mean_ltv"]) * 1.22)
plt.xticks(rotation=10, ha="right")
plt.tight_layout(); plt.savefig(CHARTS / "15_strategy_ltv_comparison.png", dpi=140); plt.close()
print("saved -> 15_strategy_ltv_comparison.png")

# ============================================================
# Q3. Channel x landing plan — where do high-LTV customers come from?
# ============================================================
print("=" * 60)
print("Q3. CHANNEL x LANDING PLAN — acquisition source quality")
print("=" * 60)
cl = per_acc.groupby(["referral_source", "landing_plan"]).agg(
    n=("account_id", "count"),
    mean_ltv=("total_revenue", "mean"),
).reset_index()
ch_ltv = per_acc.groupby("referral_source").agg(
    n=("account_id", "count"),
    mean_ltv=("total_revenue", "mean"),
    churn_rate=("churn_flag", "mean"),
).sort_values("mean_ltv", ascending=False)
print("\nLTV by acquisition channel:")
print(ch_ltv.assign(
    mean_ltv=lambda x: x["mean_ltv"].map("${:,.0f}".format),
    churn_rate=lambda x: (x["churn_rate"] * 100).round(1).astype(str) + "%",
).to_string())

# Channel x plan heatmap of LTV
pivot = per_acc.pivot_table(index="referral_source", columns="landing_plan",
                            values="total_revenue", aggfunc="mean").reindex(columns=plan_order)
n_pivot = per_acc.pivot_table(index="referral_source", columns="landing_plan",
                               values="account_id", aggfunc="count").reindex(columns=plan_order)
pivot = pivot.sort_values("Enterprise", ascending=False)
n_pivot = n_pivot.loc[pivot.index]

fig, ax = plt.subplots(figsize=(10, 5.5))
im = ax.imshow(pivot.values, aspect="auto", cmap="viridis")
ax.set_xticks(range(len(plan_order))); ax.set_xticklabels(plan_order)
ax.set_yticks(range(len(pivot.index))); ax.set_yticklabels(pivot.index)
ax.set_xlabel("Landing plan"); ax.set_ylabel("Acquisition channel")
ax.set_title("Mean LTV by channel x landing plan", loc="left", pad=15)
for i in range(pivot.shape[0]):
    for j in range(pivot.shape[1]):
        v = pivot.iat[i, j]
        n = n_pivot.iat[i, j]
        if pd.notna(v):
            ax.text(j, i, f"${v:,.0f}\n(n={int(n)})", ha="center", va="center",
                    fontsize=9, color="black" if v > pivot.values.max() * 0.5 else FG_LIGHT)
cbar = plt.colorbar(im, ax=ax, label="Mean LTV (USD)")
cbar.ax.yaxis.label.set_color(FG_LIGHT); cbar.ax.tick_params(colors=FG_LIGHT)
plt.tight_layout(); plt.savefig(CHARTS / "16_channel_x_plan_ltv.png", dpi=140); plt.close()
print("saved -> 16_channel_x_plan_ltv.png")

# ============================================================
# Q4. Annual vs monthly billing
# ============================================================
print("=" * 60)
print("Q4. ANNUAL vs MONTHLY billing — effect on retention and LTV")
print("=" * 60)
bill = per_acc.groupby("billing").agg(
    n=("account_id", "count"),
    mean_ltv=("total_revenue", "mean"),
    avg_tenure_mo=("tenure_months", "mean"),
    churn_rate=("churn_flag", "mean"),
).round(2)
print(bill.assign(
    mean_ltv=lambda x: x["mean_ltv"].map("${:,.0f}".format),
    avg_tenure_mo=lambda x: x["avg_tenure_mo"].round(1),
    churn_rate=lambda x: (x["churn_rate"] * 100).round(1).astype(str) + "%",
).to_string())
print()

fig, ax = plt.subplots(figsize=(9, 5))
cats = bill.index.tolist()
churn_pct = (bill["churn_rate"] * 100).values
tenure = bill["avg_tenure_mo"].values
x = np.arange(len(cats))
width = 0.4
b1 = ax.bar(x - width/2, churn_pct, width, color=BRAND_ORANGE, edgecolor=BG_DARK, label="Churn rate (%)")
ax2 = ax.twinx()
b2 = ax2.bar(x + width/2, tenure, width, color=BRAND_BLUE, edgecolor=BG_DARK, label="Avg tenure (months)")
ax.set_xticks(x); ax.set_xticklabels([c.capitalize() for c in cats])
ax.set_ylabel("Churn rate (%)", color=BRAND_ORANGE)
ax2.set_ylabel("Avg tenure (months)", color=BRAND_BLUE)
ax2.spines["top"].set_visible(False); ax.spines["top"].set_visible(False)
ax2.tick_params(axis="y", labelcolor=BRAND_BLUE); ax.tick_params(axis="y", labelcolor=BRAND_ORANGE)
for bar, v in zip(b1, churn_pct):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.4, f"{v:.1f}%", ha="center", color=FG_LIGHT, fontsize=9)
for bar, v in zip(b2, tenure):
    ax2.text(bar.get_x() + bar.get_width()/2, v + 0.4, f"{v:.1f}", ha="center", color=FG_LIGHT, fontsize=9)
ax.set_title("Annual vs monthly billing", loc="left", pad=15)
plt.tight_layout(); plt.savefig(CHARTS / "17_billing_freq.png", dpi=140); plt.close()
print("saved -> 17_billing_freq.png")

# ============================================================
# Q5. THE BOTTOM LINE — revenue per 100 customers acquired by strategy
# ============================================================
print("=" * 60)
print("Q5. BOTTOM LINE — total revenue per 100 customers acquired")
print("=" * 60)
sc["rev_per_100"] = sc["mean_ltv"] * 100
sc["share_pct"] = (sc["share"] * 100)
# Weight by share to compute economic contribution to a hypothetical 100-customer cohort
sc["expected_rev_if_100_acquired"] = sc["mean_ltv"] * 100
print(sc[["strategy", "n", "share", "mean_ltv", "rev_per_100"]].assign(
    share=lambda x: (x["share"] * 100).round(1).astype(str) + "%",
    mean_ltv=lambda x: x["mean_ltv"].map("${:,.0f}".format),
    rev_per_100=lambda x: x["rev_per_100"].map("${:,.0f}".format),
).to_string(index=False))
print()

# What share of TOTAL revenue does each strategy contribute?
total_rev = per_acc["total_revenue"].sum()
contributions = []
for name, df in strategies.items():
    s = df["total_revenue"].sum()
    contributions.append({"strategy": name, "n": len(df), "total_rev": s, "share_of_revenue": s/total_rev})
contrib_df = pd.DataFrame(contributions)
print("Share of TOTAL company revenue contributed by each strategy:")
print(contrib_df.assign(
    total_rev=lambda x: x["total_rev"].map("${:,.0f}".format),
    share_of_revenue=lambda x: (x["share_of_revenue"] * 100).round(1).astype(str) + "%",
).to_string(index=False))

# Chart 5: share of customers vs share of revenue
fig, ax = plt.subplots(figsize=(11, 5.5))
x = np.arange(len(contrib_df))
width = 0.4
share_customers = (contrib_df["n"] / contrib_df["n"].sum()) * 100
share_revenue = contrib_df["share_of_revenue"] * 100
b1 = ax.bar(x - width/2, share_customers, width, color=BRAND_BLUE, label="Share of customers", edgecolor=BG_DARK)
b2 = ax.bar(x + width/2, share_revenue, width, color=BRAND_GREEN, label="Share of revenue", edgecolor=BG_DARK)
for bar, v in zip(b1, share_customers):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.5, f"{v:.0f}%", ha="center", color=FG_LIGHT, fontsize=9)
for bar, v in zip(b2, share_revenue):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.5, f"{v:.0f}%", ha="center", color=FG_LIGHT, fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(contrib_df["strategy"], rotation=10, ha="right")
ax.set_ylabel("Share (%)")
ax.set_title("Share of customers vs share of revenue — where the money comes from", loc="left", pad=15)
ax.set_ylim(0, max(max(share_customers), max(share_revenue)) * 1.18)
ax.legend(facecolor=BG_DARK, edgecolor=FG_LIGHT, labelcolor=FG_LIGHT, loc="upper left")
plt.tight_layout(); plt.savefig(CHARTS / "18_customer_vs_revenue_share.png", dpi=140); plt.close()
print("saved -> 18_customer_vs_revenue_share.png")

print("\nDone.")
