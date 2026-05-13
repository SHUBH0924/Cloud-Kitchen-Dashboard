# Cloud Kitchen P&L — Data Analyst Assignment

**Stack:** Python, Streamlit, Plotly, pandas

---

## 1. What's in this folder

| File | Purpose |
|---|---|
| `app.py` | Streamlit dashboard |
| `data_prep.py` | Shared data-loading and bucket logic used by the app and the notebook |
| `analysis.ipynb` | Jupyter notebook walking through the analysis |
| `requirements.txt` | Package versions |
| `Kittchen_PNL_Data.xlsx` | Raw input |

---

## 2. How to run

```bash
# 1. create a virtualenv (I used Virtual Environment)
python3 -m venv .venv && source .venv/bin/activate

# 2. install pinned dependencies
pip install -r requirements.txt

# 3. launch the dashboard
streamlit run app.py
```

Open the printed URL (usually `http://localhost:8501`).

---

## 3. Environment

| Package | Version |
|---|---|
|streamlit | 1.38.0 |
|pandas | 2.2.2 |
|numpy | 1.26.4 |
|plotly | 5.24.1 |
|openpyxl | 3.1.5 |
|Jinja2 | 3.1.2 |
|scipy | 1.11.4 |
|statsmodels | 0.14.2 |
|matplotlib | 3.8.2 |

---

## 4. Dashboards

### Dashboard 1 — Kitchen Level P&L
- KPI tiles: store count, total revenue, GM, EBITDA, variance (with %)
- Snapshot pivot table with one column per metric × month (Net Rev, GM %, CM %, EBITDA, EBITDA %) — with conditional formatting on EBITDA % cells
- Monthly trend chart (Net Revenue / GM / EBITDA bars)
- Filters required by the brief (all in the sidebar):
  - Cohort (fixed): `REVENUE COHORT`, `CM COHORT`, `EBITDA CATEGORY`, `EBITDA COHORT`
  - Range (sliders): `EBITDA`, `CM`, `Net Revenue`, `Gross Margin`
  - Categorical: `STORE`, `ZONE MAPPING`, `CITY`, `MONTH`
- CSV download

### Dashboard 2 — Variance Level P&L
- **Top filter:** Variance category multiselect with the four buckets from the assignment image:
  - `(a) Var < 2%`, `(b) Var 2% to 3%`, `(c) Var 3% to 5%`, `(d) Var > 5%`
- **Sub-dashboard 1** — Average variance % per (revenue bucket × month), with Grand-total row. Conditional formatting (heat) on the values.
- **Sub-dashboard 2** — Distinct store count per (revenue bucket × month), with Grand-total row. Conditional formatting.
- Box-plot of variance % distribution per revenue bucket
- Single-click Excel download with both tables

Revenue buckets:
- `(a) Below INR 15 lacs`
- `(b) INR 15 to 25 lacs`
- `(c) INR 25 to 35 lacs`
- `(d) INR 35 to 45 lacs`
- `(e) Above INR 45 lacs`

Variance buckets:
- `(a) Var < 2%`
- `(b) Var 2% to 3%`
- `(c) Var 3% to 5%`
- `(d) Var > 5%`

### Insights tab
- Top / bottom 10 stores by EBITDA
- Zone × City EBITDA % heatmap
- Variance % vs EBITDA % scatter with OLS trendline and Pearson correlation
- All cross-filterable via the same sidebar

---

## 5. Performance — handling real-time refreshes

Two things keep the app responsive when the underlying file is updated frequently:

1. **mtime-keyed cache.** `@st.cache_data` decorates the loader, and the cache key includes the file's mtime. As soon as the source `.xlsx` is rewritten, the next request automatically re-parses without any manual cache-clear:

   ```python
   @st.cache_data(show_spinner="Wait Your data is loading...")
   def _load(path_str: str, mtime: float) -> pd.DataFrame:
       return load_and_prepare(path_str)

   def get_data():
       mtime = DATA_PATH.stat().st_mtime
       return _load(str(DATA_PATH), mtime)
   ```

2. **Filter-function caching.** `apply_filters` is also `@st.cache_data`-decorated and takes only hashable args (tuples), so identical filter combinations are served from memory.

---

## 6. Derived columns

The raw file contains rupee amounts only. The following are computed in `data_prep.py`:

| Column | Formula |
|---|---|
| `GM %`        | `GROSS MARGIN / NET REVENUE` |
| `CM`          | `GROSS MARGIN − VARIANCE` (variance = food wastage, reduces GM to give CM) |
| `CM %`        | `(CM / NET REVENUE) * 100` |
| `EBITDA %`    | `(KITCHEN EBITDA / NET REVENUE) * 100` |
| `VARIANCE %`  | `(VARIANCE / NET REVENUE) * 100` |
| `MONTH_DT`        | parsed datetime for ordering |
| `REVENUE BUCKET`  | Revenue Buckets are derived above |
| `VARIANCE BUCKET` | Variance Buckets are derived above |


---

## 7. Key findings

1. **Variance (food wastage) is well-controlled.** Blended variance is ~0.58% of net revenue. Almost every store sits in the `Var < 2%` bucket.
2. **Despite the low absolute level, variance % correlates negatively with EBITDA % at the store level** (Pearson ≈ −0.62). Even small wastage differences track real profitability gaps.
3. **EBITDA % is healthy at ~19.5% blended** but **11.5% of store-months are loss-making** (184 distinct stores hit at least one EBITDA-negative month). These are spread across all five cities — opportunity for targeted intervention.
4. **Discount intensity hurts profitability** — `DISCOUNT %` correlates roughly −0.20 with `EBITDA %`, while GM % barely moves with discount. Discount-led top-line growth is margin-dilutive at the EBITDA line.
5. **Zone performance is tight**, with East/South narrowly ahead of West/North on EBITDA %. No zone is structurally broken.

All of the above is interactively explorable in the Insights tab of the dashboard.

---

## 8. Notes on data

- 2,100 rows × 17 columns, 344 stores across 5 cities and 4 zones
- Time range: **Oct 2023 → Mar 2024** (6 months)
- The `(a) Below INR 15 lacs` revenue bucket is empty in this dataset — the minimum NET REVENUE observed is ~₹17 lacs. The bucket is kept for parity with the assignment template.
- Source cohort columns (`REVENUE COHORT`, `CM COHORT`, `EBITDA COHORT`) are preserved as fixed cohort filters in Dashboard 1, exactly as required by the brief.
