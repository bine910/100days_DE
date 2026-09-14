# Week 4 — Olist E-Commerce Data Analysis

Mini ETL project phân tích doanh thu từ dataset Brazilian E-Commerce (Olist).

Pipeline: Extract (CSV) → Transform (clean, merge, aggregate) → Load (report CSV + charts)

## Dataset

Brazilian E-Commerce Public Dataset by Olist (~100K orders, 9 CSV files)

Source: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

## Setup

```bash
git clone <repo-url>
cd week_4/week4_olist

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Download Data

```bash
pip install kaggle
kaggle datasets download olistbr/brazilian-ecommerce --unzip -p data/raw/
```

## Run

```bash
python main.py
```

Output trong folder `output/`:
- `category_summary.csv` — revenue theo category
- `revenue_by_category.png` — bar chart top 10 categories
- `monthly_revenue_trend.png` — line chart trend theo tháng

## Test

```bash
python -m pytest tests/ -v
```

## Project Structure

```
week4_olist/
├── src/
│   ├── extract.py       # Load raw CSV
│   ├── transform.py     # Clean, merge, aggregate
│   └── report.py        # Save CSV + charts
├── tests/
│   └── test_transform.py
├── data/raw/            # CSV files (not in git)
├── output/              # Reports + charts
├── main.py              # Entry point
└── requirements.txt
```