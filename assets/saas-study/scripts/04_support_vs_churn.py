"""
Support tickets vs churn — does support load predict the renewal hump?

Key questions:
1. Do churners have more tickets than non-churners?
2. Renewal-hump test: do tickets in months 9-12 predict churn in months 13-18?
3. Are escalations / low satisfaction sharper predictors than raw volume?
4. Does slow resolution time correlate with churn?
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
tickets = pd.read_csv(DATA / "ravenstack_support_tickets.csv", parse_dates=["submitted_at"])
churn_events = pd.read_csv(DATA / "ravenstack_churn_events.csv", parse_dates=["churn_date"])

# Last real churn date per account
real_churns = churn_events[~churn_events["is_reactivation"].astype(bool)]
last_churn = real_churns.groupby("account_id")["churn_date"].max().rename("last_churn_date")
obs_end = pd.Timestamp("2024-12-31")

acc = accounts.merge(last_churn, on="account_id", how="left")
acc["exit_date"] = pd.to_datetime(np.where(acc["churn_flag"], acc["last_churn_date"].fillna(obs_end), obs_end))
acc["tenure_months"] = ((acc["exit_date"] - acc["signup_date"]).dt.days // 30).astype(int)
acc["observable_months"] = ((obs_end - acc["signup_date"]).dt.days // 30).astype(int)

# Join tickets with signup_date and exit_date
tk = tickets.merge(acc[["account_id", "signup_date", "exit_date", "churn_flag"]], on="account_id", how="left")
tk["months_since_signup"] = ((tk["submitted_at"] - tk["signup_date"]).dt.days // 30).astype(int)

# Only count tickets submitted before exit
tk = tk[tk["submitted_at"] <= tk["exit_date"]].copy()

print(f"Tickets in scope (submitted before exit): {len(tk)}")
print()

# === Q1: Per-account ticket volume — churners vs non-churners ===
per_acc = (tk.groupby("account_id")
             .agg(tickets=("ticket_id", "count"),
                  escalations=("escalation_flag", "sum"),
                  avg_satisfaction=("satisfaction_score", "mean"),
                  avg_resolution_h=("resolution_time_hours", "mean"))
             .reset_index())
per_acc = acc[["account_id", "churn_flag", "tenure_months", "observable_months"]].merge(per_acc, on="account_id", how="left")
per_acc[["tickets", "escalations"]] = per_acc[["tickets", "escalations"]].fillna(0).astype(int)

# Normalize by months observed to make a fair rate
per_acc["tickets_per_month"] = per_acc["tickets"] / per_acc["tenure_months"].replace(0, 1)

print("=" * 60)
print("Q1. Ticket volume — churners vs non-churners")
print("=" * 60)
g = per_acc.groupby("churn_flag").agg(
    n=("account_id", "count"),
    avg_tickets=("tickets", "mean"),
    avg_tickets_per_month=("tickets_per_month", "mean"),
    avg_escalations=("escalations", "mean"),
    avg_satisfaction=("avg_satisfaction", "mean"),
    avg_resolution_h=("avg_resolution_h", "mean"),
).round(2)
g.index = ["Stayed", "Churned"]
print(g.T.to_string())
print()

# === Q1 chart: tickets-per-month, churners vs stayed ===
fig, ax = plt.subplots(figsize=(9, 5))
data = [per_acc.loc[~per_acc["churn_flag"], "tickets_per_month"].dropna(),
        per_acc.loc[per_acc["churn_flag"], "tickets_per_month"].dropna()]
bp = ax.boxplot(data, tick_labels=["Stayed", "Churned"], patch_artist=True,
                widths=0.5, medianprops={"color": FG_LIGHT, "linewidth": 2})
bp["boxes"][0].set_facecolor(BRAND_BLUE); bp["boxes"][0].set_edgecolor(FG_LIGHT)
bp["boxes"][1].set_facecolor(BRAND_ORANGE); bp["boxes"][1].set_edgecolor(FG_LIGHT)
for w in bp["whiskers"] + bp["caps"]:
    w.set_color(FG_LIGHT)
ax.set_ylabel("Support tickets per month of tenure")
ax.set_title("Support load — churners vs stayed", loc="left", pad=15)
ax.grid(True, axis="y", alpha=0.15, color=FG_LIGHT)
plt.tight_layout(); plt.savefig(CHARTS / "11_tickets_per_month_box.png", dpi=140); plt.close()
print("saved -> 11_tickets_per_month_box.png")

# === Q2: Renewal hump test — pre-renewal tickets (months 9-12) vs churn in months 13-18 ===
# Cohort: customers who reached month 12 (could be observed long enough for renewal decision)
eligible = per_acc[per_acc["observable_months"] >= 12].copy()
# Count their tickets in months 9-12
tk_window = tk[(tk["months_since_signup"] >= 9) & (tk["months_since_signup"] <= 12)]
prerenewal = tk_window.groupby("account_id").size().rename("tickets_9_12")
eligible = eligible.merge(prerenewal, on="account_id", how="left")
eligible["tickets_9_12"] = eligible["tickets_9_12"].fillna(0).astype(int)

# Churned in months 13-18
eligible["renewal_churn"] = (
    eligible["churn_flag"] &
    (eligible["tenure_months"] >= 13) &
    (eligible["tenure_months"] <= 18)
)

print("=" * 60)
print("Q2. Renewal hump test — tickets in mo 9-12 vs churn in mo 13-18")
print("=" * 60)
print(f"Customers who reached month 12 of observation: {len(eligible)}")
def bucket(n):
    if n == 0: return "0 tickets"
    if n <= 2: return "1-2"
    if n <= 5: return "3-5"
    return "6+"
eligible["bucket"] = eligible["tickets_9_12"].apply(bucket)
order = ["0 tickets", "1-2", "3-5", "6+"]
test = eligible.groupby("bucket").agg(
    n=("account_id", "count"),
    renewal_churned=("renewal_churn", "sum"),
).reindex(order).fillna(0).astype(int)
test["renewal_churn_rate"] = (test["renewal_churned"] / test["n"]).round(3)
print(test.to_string())
print()

# Chart 2: renewal hump test
fig, ax = plt.subplots(figsize=(9, 5))
colors_b = [BRAND_BLUE, BRAND_BLUE, BRAND_GREEN, BRAND_ORANGE]
bars = ax.bar(test.index, test["renewal_churn_rate"] * 100, color=colors_b, edgecolor=BG_DARK)
overall_rr = eligible["renewal_churn"].mean()
ax.axhline(overall_rr * 100, color=BRAND_ORANGE, linestyle="--", linewidth=1.4,
           label=f"Overall: {overall_rr:.1%}")
for bar, rate, n in zip(bars, test["renewal_churn_rate"], test["n"]):
    ax.text(bar.get_x() + bar.get_width()/2, rate * 100 + 0.5,
            f"{rate:.1%}\n(n={n})", ha="center", va="bottom", color=FG_LIGHT, fontsize=9)
ax.set_ylabel("Churn rate in months 13-18 (%)")
ax.set_xlabel("Support tickets in months 9-12")
ax.set_title("Pre-renewal support load vs renewal-moment churn", loc="left", pad=15)
ax.set_ylim(0, max(test["renewal_churn_rate"] * 100) * 1.35 + 1)
ax.legend(facecolor=BG_DARK, edgecolor=FG_LIGHT, labelcolor=FG_LIGHT)
plt.tight_layout(); plt.savefig(CHARTS / "12_renewal_hump_test.png", dpi=140); plt.close()
print("saved -> 12_renewal_hump_test.png")

# === Q3: Escalations and satisfaction ===
print("=" * 60)
print("Q3. Escalations and satisfaction signal")
print("=" * 60)
per_acc["had_escalation"] = per_acc["escalations"] > 0
esc = per_acc.groupby("had_escalation").agg(
    n=("account_id", "count"),
    churn_rate=("churn_flag", "mean"),
).round(3)
esc.index = ["No escalations", ">=1 escalation"]
print(esc.to_string())
print()

# Satisfaction buckets (3 = bad, 4 = ok, 5 = great)
per_acc["sat_bucket"] = pd.cut(per_acc["avg_satisfaction"], bins=[0, 3.5, 4.5, 5.1],
                                labels=["Low (3-3.5)", "Mid (3.5-4.5)", "High (4.5-5)"])
sat = per_acc.dropna(subset=["sat_bucket"]).groupby("sat_bucket", observed=True).agg(
    n=("account_id", "count"),
    churn_rate=("churn_flag", "mean"),
).round(3)
print(sat.to_string())
print()

# Chart 3: escalation effect
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
ax1, ax2 = axes
overall = per_acc["churn_flag"].mean()

bars1 = ax1.bar(esc.index, esc["churn_rate"] * 100, color=[BRAND_BLUE, BRAND_ORANGE], edgecolor=BG_DARK)
ax1.axhline(overall * 100, color=FG_LIGHT, linestyle="--", linewidth=1, alpha=0.6,
            label=f"Overall: {overall:.1%}")
for bar, rate, n in zip(bars1, esc["churn_rate"], esc["n"]):
    ax1.text(bar.get_x() + bar.get_width()/2, rate * 100 + 0.6,
             f"{rate:.1%}\n(n={n})", ha="center", va="bottom", color=FG_LIGHT, fontsize=10)
ax1.set_ylabel("Churn rate (%)")
ax1.set_title("Churn by escalation history", loc="left", pad=15)
ax1.set_ylim(0, max(esc["churn_rate"] * 100) * 1.3 + 2)
ax1.legend(facecolor=BG_DARK, edgecolor=FG_LIGHT, labelcolor=FG_LIGHT, loc="upper left")

bars2 = ax2.bar(sat.index.astype(str), sat["churn_rate"] * 100, color=[BRAND_ORANGE, BRAND_GREEN, BRAND_BLUE], edgecolor=BG_DARK)
ax2.axhline(overall * 100, color=FG_LIGHT, linestyle="--", linewidth=1, alpha=0.6,
            label=f"Overall: {overall:.1%}")
for bar, rate, n in zip(bars2, sat["churn_rate"], sat["n"]):
    ax2.text(bar.get_x() + bar.get_width()/2, rate * 100 + 0.6,
             f"{rate:.1%}\n(n={n})", ha="center", va="bottom", color=FG_LIGHT, fontsize=10)
ax2.set_title("Churn by average satisfaction score", loc="left", pad=15)
ax2.set_ylim(0, max(sat["churn_rate"] * 100) * 1.3 + 2)
ax2.legend(facecolor=BG_DARK, edgecolor=FG_LIGHT, labelcolor=FG_LIGHT, loc="upper left")
plt.tight_layout(); plt.savefig(CHARTS / "13_escalation_satisfaction.png", dpi=140); plt.close()
print("saved -> 13_escalation_satisfaction.png")

# === Q4: Resolution time ===
print("=" * 60)
print("Q4. Resolution time vs churn")
print("=" * 60)
per_acc["res_bucket"] = pd.cut(per_acc["avg_resolution_h"], bins=[0, 24, 48, 72],
                                labels=["<24h", "24-48h", "48-72h"])
res = per_acc.dropna(subset=["res_bucket"]).groupby("res_bucket", observed=True).agg(
    n=("account_id", "count"),
    churn_rate=("churn_flag", "mean"),
).round(3)
print(res.to_string())
print("\nDone.")
