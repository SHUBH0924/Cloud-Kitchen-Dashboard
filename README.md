# Rebel Foods – Kitchen PNL Dashboard

This project is based on the Rebel Foods Data Analyst assignment.

The dashboard was built using Streamlit and Plotly to analyze kitchen-level Profit & Loss data, revenue trends, EBITDA performance, and variance categories across stores and months.

---

## What’s Included

### 1. Kitchen Level PNL Dashboard
Filters available:
- Store
- Month
- Revenue category
- EBITDA range
- CM range
- Variance category

The dashboard shows:
- Net Revenue
- GM%
- CM%
- EBITDA
- Store-wise performance
- Monthly trends

---

### 2. Variance Dashboard

This section focuses on food variance/wastage analysis.

Variance buckets used:
- Below 2%
- 2% to 3%
- 3% to 5%
- Above 5%

Two views are included:
1. Average variance % by revenue category
2. Store count breakdown by month and revenue range

---

## Additional Analysis

Some extra analysis was also added to understand:
- Top and bottom performing stores
- Revenue vs EBITDA relationship
- Monthly performance trends
- High variance stores

---

## Tech Stack

- Python
- Streamlit
- Plotly
- Pandas
- NumPy

---

## Files

| File | Description |
|---|---|
| `app.py` | Main Streamlit dashboard |
| `data_prep.py` | Data cleaning and preprocessing |
| `analysis.ipynb` | Exploratory analysis |
| `requirements.txt` | Required packages |

---

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt