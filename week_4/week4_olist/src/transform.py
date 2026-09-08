import pandas as pd


def clean_orders(df:pd.DataFrame) -> pd.DataFrame:
    """Convert datetime columns and remove duplicates."""
    datetime_cols = [
    'order_purchase_timestamp',
    'order_approved_at', 
    'order_delivered_carrier_date',
    'order_delivered_customer_date',
    'order_estimated_delivery_date'
]
    df = df.copy()
    for x in datetime_cols:
        df[x]=pd.to_datetime(df[x])
    df = df.drop_duplicates()
    
    return df

def build_sales(orders: pd.DataFrame, order_items: pd.DataFrame, 
                products: pd.DataFrame, categories: pd.DataFrame) -> pd.DataFrame:
    """Merge 4 dataset"""
    sales = (
        orders
        .merge(order_items, on='order_id')
        .merge(products, on='product_id')
        .merge(categories, on='product_category_name', how='left')
    )
    sales['year_month'] = sales['order_purchase_timestamp'].dt.to_period('M')
    return sales
def revenue_by_category(sales: pd.DataFrame) -> pd.DataFrame:
    """Find the revenue by category."""
    return sales.groupby(['product_category_name_english'])['price'].agg(['sum','mean','count']).sort_values('sum',ascending=False)
def revenue_by_month(sales: pd.DataFrame) -> pd.Series:
    """Find the revenue by month."""
    return sales.groupby('year_month')['price'].sum()