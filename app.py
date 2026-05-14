from __future__ import annotations

from pathlib import Path
import io

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_prep import (
    load_and_prepare,
    REVENUE_BUCKETS,
    VARIANCE_BUCKETS,
)

# Page Config
st.set_page_config(
    page_title="Kitchen P&L Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path(__file__).parent / "Kittchen_PNL_Data.xlsx"

# Caching
@st.cache_data(show_spinner="Wait Your data is loading...")
def _load(path_str: str, mtime: float) -> pd.DataFrame:
    return load_and_prepare(path_str)


# The main data loading function.
def get_data() -> pd.DataFrame:
    mtime = DATA_PATH.stat().st_mtime if DATA_PATH.exists() else 0.0
    return _load(str(DATA_PATH), mtime)


@st.cache_data(show_spinner=False)
def apply_filters(
    df: pd.DataFrame,
    stores: tuple,
    zones: tuple,
    months: tuple,
    cities: tuple,
    rev_cohorts: tuple,
    cm_cohorts: tuple,
    ebitda_cats: tuple,
    ebitda_cohorts: tuple,
    ebitda_range: tuple,
    cm_range: tuple,
    rev_range: tuple,
    gm_range: tuple,
) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    if stores:         m &= df["STORE"].isin(stores)
    if zones:          m &= df["ZONE MAPPING"].isin(zones)
    if months:         m &= df["MONTH"].isin(months)
    if cities:         m &= df["CITY"].isin(cities)
    if rev_cohorts:    m &= df["REVENUE COHORT"].isin(rev_cohorts)
    if cm_cohorts:     m &= df["CM COHORT"].isin(cm_cohorts)
    if ebitda_cats:    m &= df["EBITDA CATEGORY"].isin(ebitda_cats)
    if ebitda_cohorts: m &= df["EBITDA COHORT"].isin(ebitda_cohorts)

    lo, hi = ebitda_range; m &= df["KITCHEN EBITDA"].between(lo, hi)
    lo, hi = cm_range;     m &= df["CM"].between(lo, hi)
    lo, hi = rev_range;    m &= df["NET REVENUE"].between(lo, hi)
    lo, hi = gm_range;     m &= df["GROSS MARGIN"].between(lo, hi)

    return df[m].copy()


# Helper functions
def inr(x: float) -> str:
    """Format an integer-rupee value with Indian-style commas."""
    if pd.isna(x):
        return "—"
    sign = "-" if x < 0 else ""
    n = abs(int(round(x)))
    s = str(n)
    if len(s) <= 3:
        return f"{sign}₹{s}"
    last3, rest = s[-3:], s[:-3]
    rest = ",".join([rest[max(i-2, 0):i] for i in range(len(rest), 0, -2)][::-1])
    return f"{sign}₹{rest},{last3}"


def lacs(x: float) -> str:
    if pd.isna(x):
        return "—"
    return f"₹{x/1e5:,.1f} L"


def pct(x: float) -> str:
    return "—" if pd.isna(x) else f"{x*100:,.1f}%"


# Filters
df = get_data()

with st.sidebar:
    st.title("Filters")
    st.caption(f"Data: {DATA_PATH.name}  •  {len(df):,} rows  •  {df['STORE'].nunique()} stores")

    page = st.radio(
        "Dashboard",
        ["Kitchen Level P&L", "Variance Level P&L", "Insights"],
        index=0,
    )
    st.divider()

    # Range filters
    e_min, e_max = int(df["KITCHEN EBITDA"].min()), int(df["KITCHEN EBITDA"].max())
    ebitda_range = st.slider(
        "EBITDA range (₹)",
        min_value=e_min, max_value=e_max,
        value=(e_min, e_max), step=1000,
        help="Absolute kitchen EBITDA in rupees",
    )

    c_min, c_max = int(df["CM"].min()), int(df["CM"].max())
    cm_range = st.slider("CM range (₹)", c_min, c_max, (c_min, c_max), 1000)

    r_min, r_max = int(df["NET REVENUE"].min()), int(df["NET REVENUE"].max())
    rev_range = st.slider("Net Revenue range (₹)", r_min, r_max, (r_min, r_max), 10_000)

    g_min, g_max = int(df["GROSS MARGIN"].min()), int(df["GROSS MARGIN"].max())
    gm_range = st.slider("Gross Margin range (₹)", g_min, g_max, (g_min, g_max), 1000)

    st.divider()
    months_sorted = (
        df.dropna(subset=["MONTH_DT"]).sort_values("MONTH_DT")["MONTH"].drop_duplicates().tolist()
    )
    months_sel = st.multiselect("Month", months_sorted)
    zones_sel = st.multiselect("Zone", sorted(df["ZONE MAPPING"].dropna().unique()))
    cities_sel = st.multiselect("City", sorted(df["CITY"].dropna().unique()))
    stores_sel = st.multiselect("Store", sorted(df["STORE"].dropna().unique()))

    st.divider()
    st.caption("Cohort filters (fixed buckets from source data)")
    rev_cohort_sel    = st.multiselect("Revenue cohort",  sorted(df["REVENUE COHORT"].unique()))
    cm_cohort_sel     = st.multiselect("CM cohort",        sorted(df["CM COHORT"].unique()))
    ebitda_cat_sel    = st.multiselect("EBITDA category", sorted(df["EBITDA CATEGORY"].unique()))
    ebitda_cohort_sel = st.multiselect("EBITDA cohort",   sorted(df["EBITDA COHORT"].unique()))

    if st.button("Reload data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

filtered = apply_filters(
    df,
    tuple(stores_sel), tuple(zones_sel), tuple(months_sel), tuple(cities_sel),
    tuple(rev_cohort_sel), tuple(cm_cohort_sel), tuple(ebitda_cat_sel), tuple(ebitda_cohort_sel),
    tuple(ebitda_range), tuple(cm_range), tuple(rev_range), tuple(gm_range),
)


# Kitchen Level P&L Dashboard
def render_kitchen_pnl(d: pd.DataFrame) -> None:
    st.title("Kitchen Level P&L")
    st.caption(
        "Profit & Loss snapshot per kitchen store. Use the sidebar to filter by "
        "cohorts, zones, months, or to set range filters on EBITDA / CM / Revenue / GM."
    )

    if d.empty:
        st.warning("No rows match the current filters.")
        return

    # KPIs
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Stores", f"{d['STORE'].nunique():,}")
    k2.metric("Net revenue", lacs(d["NET REVENUE"].sum()))
    k3.metric("Gross margin", lacs(d["GROSS MARGIN"].sum()),
              pct(d["GROSS MARGIN"].sum() / d["NET REVENUE"].sum()))
    k4.metric("EBITDA", lacs(d["KITCHEN EBITDA"].sum()),
              pct(d["KITCHEN EBITDA"].sum() / d["NET REVENUE"].sum()))
    k5.metric("Variance (wastage)", lacs(d["VARIANCE"].sum()),
              pct(d["VARIANCE"].sum() / d["NET REVENUE"].sum()))

    st.divider()

    # Table
    st.subheader("Kitchen snapshot")
    pivot_metrics = ["NET REVENUE", "GM %", "CM %", "KITCHEN EBITDA", "EBITDA %"]

    snap = (
        d.pivot_table(
            index="STORE",
            columns="MONTH LABEL",
            values=pivot_metrics,
            aggfunc="sum",
        )
    )

    # Orders the column by their month
    month_order = (
        d.dropna(subset=["MONTH_DT"])
         .sort_values("MONTH_DT")["MONTH LABEL"].drop_duplicates().tolist()
    )
    snap = snap.reindex(columns=pd.MultiIndex.from_product([pivot_metrics, month_order]))
    snap.columns = [f"{m} | {metric}" for metric, m in snap.columns]

    # Recompute % rows: pivot_table summed % which is wrong; fix per metric
    rev_piv = d.pivot_table(index="STORE", columns="MONTH LABEL", values="NET REVENUE", aggfunc="sum")
    gm_piv  = d.pivot_table(index="STORE", columns="MONTH LABEL", values="GROSS MARGIN", aggfunc="sum")
    cm_piv  = d.pivot_table(index="STORE", columns="MONTH LABEL", values="CM",            aggfunc="sum")
    eb_piv  = d.pivot_table(index="STORE", columns="MONTH LABEL", values="KITCHEN EBITDA", aggfunc="sum")
    for m in month_order:
        if m in rev_piv.columns:
            snap[f"{m} | GM %"]     = (gm_piv[m] / rev_piv[m]).reindex(snap.index)
            snap[f"{m} | CM %"]     = (cm_piv[m] / rev_piv[m]).reindex(snap.index)
            snap[f"{m} | EBITDA %"] = (eb_piv[m] / rev_piv[m]).reindex(snap.index)

    # Format display
    fmt = {}
    for c in snap.columns:
        if "%" in c.split(" | ")[1]:
            fmt[c] = "{:.1%}"
        else:
            fmt[c] = "₹{:,.0f}"

    st.dataframe(
        snap.style.format(fmt, na_rep="—").background_gradient(
            cmap="RdYlGn",
            subset=[c for c in snap.columns if "EBITDA %" in c],
            axis=None,
        ),
        use_container_width=True,
        height=500,
    )

    # CSV export
    csv = snap.to_csv().encode("utf-8")
    st.download_button("Download snapshot (CSV)", csv,
                       file_name="kitchen_snapshot.csv", mime="text/csv")

    st.divider()

    # Trends
    st.subheader("Trend — totals by month")
    monthly = (
        d.groupby("MONTH_DT", as_index=False)
         .agg(net_rev=("NET REVENUE", "sum"),
              gm=("GROSS MARGIN", "sum"),
              ebitda=("KITCHEN EBITDA", "sum"),
              variance=("VARIANCE", "sum"))
         .sort_values("MONTH_DT")
    )
    fig = go.Figure()
    fig.add_bar(x=monthly["MONTH_DT"], y=monthly["net_rev"], name="Net revenue", marker_color="#4C78A8")
    fig.add_bar(x=monthly["MONTH_DT"], y=monthly["gm"],      name="Gross margin", marker_color="#54A24B")
    fig.add_bar(x=monthly["MONTH_DT"], y=monthly["ebitda"],  name="EBITDA",       marker_color="#F58518")
    fig.update_layout(
        barmode="group", height=380,
        yaxis_title="₹", xaxis_title=None,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)


# Variance Level P&L Dashboard
def render_variance_pnl(d: pd.DataFrame) -> None:
    st.title("Variance Level P&L")
    st.caption("Food-wastage analysis bucketed by variance % and revenue range. "
               "Top filter below restricts both tables to the chosen variance buckets.")

    if d.empty:
        st.warning("No rows match the current filters.")
        return

    # Variance-bucket multiselect
    variance_labels = [lab for lab, _, _ in VARIANCE_BUCKETS]
    sel_var = st.multiselect(
        "Variance category",
        options=variance_labels,
        default=variance_labels,
        help="Use to restrict both sub-dashboards to the chosen variance buckets",
    )

    d_var = d[d["VARIANCE BUCKET"].isin(sel_var)] if sel_var else d.iloc[0:0]
    if d_var.empty:
        st.warning("No rows match the current variance selection.")
        return

    month_order = (
        d.dropna(subset=["MONTH_DT"])
         .sort_values("MONTH_DT")["MONTH LABEL"].drop_duplicates().tolist()
    )
    rev_order = [lab for lab, _, _ in REVENUE_BUCKETS]

    # Sub-dashboard
    st.subheader("Variance by revenue category — average variance %")
    st.caption("Average variance % across the kitchens in each revenue bucket, by month.")

    avg_pivot = (
        d_var.pivot_table(
            index="REVENUE BUCKET",
            columns="MONTH LABEL",
            values="VARIANCE %",
            aggfunc="mean",
        )
        .reindex(index=rev_order, columns=month_order)
    )
    # Grand total = overall avg variance % for each month
    grand_avg = (
        d_var.pivot_table(
            index=lambda _: "Grand total",
            columns="MONTH LABEL",
            values="VARIANCE %",
            aggfunc="mean",
        )
        .reindex(columns=month_order)
    )
    avg_table = pd.concat([avg_pivot, grand_avg])
    st.dataframe(
        avg_table.style
            .format("{:.1%}", na_rep="—")
            .background_gradient(cmap="OrRd", axis=None),
        use_container_width=True,
        height=260,
    )

    # Sub-dashboard 2
    st.subheader("Store count — by revenue bucket by month")
    st.caption("Number of distinct kitchen stores in each revenue bucket, after applying the variance filter above.")

    count_pivot = (
        d_var.pivot_table(
            index="REVENUE BUCKET",
            columns="MONTH LABEL",
            values="STORE",
            aggfunc=pd.Series.nunique,
            fill_value=0,
        )
        .reindex(index=rev_order, columns=month_order, fill_value=0)
    )
    grand_count = (
        d_var.pivot_table(
            index=lambda _: "Grand total",
            columns="MONTH LABEL",
            values="STORE",
            aggfunc=pd.Series.nunique,
            fill_value=0,
        )
        .reindex(columns=month_order, fill_value=0)
    )
    count_table = pd.concat([count_pivot, grand_count])
    st.dataframe(
        count_table.style
            .format("{:,.0f}")
            .background_gradient(cmap="Blues", axis=None),
        use_container_width=True,
        height=260,
    )

    # Here as an bounus I also added a Variance Distributiion
    st.subheader("Variance distribution")
    fig = px.box(
        d_var, x="REVENUE BUCKET", y="VARIANCE %",
        category_orders={"REVENUE BUCKET": rev_order},
        points=False, color="REVENUE BUCKET",
        title="Distribution of variance % across stores, by revenue bucket",
    )
    fig.update_yaxes(tickformat=".1%")
    fig.update_layout(showlegend=False, height=380, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # Download
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        avg_table.to_excel(writer, sheet_name="avg_variance_pct")
        count_table.to_excel(writer, sheet_name="store_count")
    st.download_button(
        "Download both tables (Excel)",
        out.getvalue(),
        file_name="variance_dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# Insights Dashboard
def render_insights(d: pd.DataFrame) -> None:
    st.title("Insights")

    if d.empty:
        st.warning("No rows match the current filters.")
        return

    # Top / bottom stores by EBITDA
    c1, c2 = st.columns(2)
    by_store = (
        d.groupby("STORE", as_index=False)
         .agg(net_rev=("NET REVENUE", "sum"),
              ebitda=("KITCHEN EBITDA", "sum"),
              variance=("VARIANCE", "sum"))
    )
    by_store["ebitda_%"] = by_store["ebitda"] / by_store["net_rev"]

    with c1:
        st.subheader("Top 10 stores by EBITDA")
        top = by_store.nlargest(10, "ebitda")
        fig = px.bar(top.sort_values("ebitda"), x="ebitda", y="STORE",
                     orientation="h", text_auto=".2s",
                     color="ebitda_%", color_continuous_scale="Greens")
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Bottom 10 stores by EBITDA")
        bot = by_store.nsmallest(10, "ebitda")
        fig = px.bar(bot.sort_values("ebitda"), x="ebitda", y="STORE",
                     orientation="h", text_auto=".2s",
                     color="ebitda_%", color_continuous_scale="Reds_r")
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Zone × city heatmap of EBITDA %
    st.subheader("EBITDA % heatmap — Zone × City")
    heat = (
        d.groupby(["ZONE MAPPING", "CITY"])
         .apply(lambda g: g["KITCHEN EBITDA"].sum() / g["NET REVENUE"].sum())
         .unstack()
    )
    fig = px.imshow(heat, text_auto=".1%", aspect="auto", color_continuous_scale="RdYlGn",
                    labels=dict(color="EBITDA %"))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Variance vs EBITDA scatter plot
    st.subheader("Does food wastage hurt profitability?")
    scatter_df = (
        d.groupby("STORE", as_index=False)
         .apply(lambda g: pd.Series({
             "variance_%": g["VARIANCE"].sum() / g["NET REVENUE"].sum(),
             "ebitda_%":   g["KITCHEN EBITDA"].sum() / g["NET REVENUE"].sum(),
             "net_rev":    g["NET REVENUE"].sum(),
             "zone":       g["ZONE MAPPING"].iloc[0],
         }))
    )
    fig = px.scatter(scatter_df, x="variance_%", y="ebitda_%", size="net_rev",
                     color="zone", hover_name="STORE", trendline="ols",
                     labels={"variance_%": "Variance %", "ebitda_%": "EBITDA %"})
    fig.update_xaxes(tickformat=".1%")
    fig.update_yaxes(tickformat=".1%")
    fig.update_layout(height=440, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    corr = scatter_df["variance_%"].corr(scatter_df["ebitda_%"])
    st.info(f"Correlation (variance % vs EBITDA %): **{corr:+.3f}** "
            f"— {'negative, as expected' if corr < 0 else 'weak/positive'}.")


# Routes
if page == "Kitchen Level P&L":
    render_kitchen_pnl(filtered)
elif page == "Variance Level P&L":
    render_variance_pnl(filtered)
else:
    render_insights(filtered)
