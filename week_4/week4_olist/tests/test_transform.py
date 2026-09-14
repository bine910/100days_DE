import pandas as pd
from src.transform import clean_orders,revenue_by_category

def test_clean_orders_converts_datetime():
    # 1. Tạo input giả
    df = pd.DataFrame({
        'order_id': ['001'],
        'customer_id': ['c1'],
        'order_status': ['delivered'],
        'order_purchase_timestamp': ['2017-10-02 10:56:33'],
        'order_approved_at': ['2017-10-02 11:00:00'],
        'order_delivered_carrier_date': ['2017-10-03 08:00:00'],
        'order_delivered_customer_date': ['2017-10-10 21:25:13'],
        'order_estimated_delivery_date': ['2017-10-18 00:00:00']
    })
    
    # 2. Gọi function
    result = clean_orders(df)
    
    # 3. Assert — cột đã chuyển sang datetime chưa?
    assert pd.api.types.is_datetime64_any_dtype(result['order_purchase_timestamp'])

def test_revenue_by_category():
    df = pd.DataFrame({
    'product_category_name_english': ['cái 1', 'cái 1', 'cái 2', 'cái 2', 'cái 2'],
    'price': [10, 20, 5, 5, 5]
})
    result = revenue_by_category(df)
    assert result.index[0]=='cái 1'
    assert len(result) == 2
    assert result['sum'].iloc[0] > result['sum'].iloc[1]