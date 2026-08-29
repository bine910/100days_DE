import pandas as pd

def load_orders() -> pd.DataFrame:
    return pd.read_csv('data/raw/olist_orders_dataset.csv')
def load_order_items() -> pd.DataFrame:
    return pd.read_csv('data/raw/olist_order_items_dataset.csv')
def load_products() -> pd.DataFrame:
    return pd.read_csv('data/raw/olist_products_dataset.csv')
def load_categories() -> pd.DataFrame:
    return pd.read_csv('data/raw/product_category_name_translation.csv')