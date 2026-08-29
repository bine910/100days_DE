from src.extract import load_orders, load_order_items, load_products, load_categories
from src.transform import clean_orders, build_sales, revenue_by_category,revenue_by_month
from src.report import save_csv, plot_chart
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def main():
    try:

        orders = load_orders()
        order_items = load_order_items()
        products = load_products()
        categories = load_categories()
        logger.info(f"Loaded: orders={len(orders)}, items={len(order_items)}, products={len(products)}, categories={len(categories)}")

        orders = clean_orders(orders)
        logger.info("Orders cleaned")

        sales = build_sales(orders, order_items, products, categories)
        logger.info(f"Sales built: {len(sales)} rows")

        cat_rev = revenue_by_category(sales)
        monthly_rev = revenue_by_month(sales)

        save_csv(cat_rev, 'output/category_summary.csv')
        plot_chart(cat_rev['sum'].head(10), 'Top 10 Categories', 'output/revenue_by_category.png', 'bar')
        plot_chart(monthly_rev, 'Monthly Revenue', 'output/monthly_revenue_trend.png', 'line')
        logger.info("All outputs saved")
    except Exception as e :
        logger.error(f"Lỗi : {e}")
    
    

if __name__ == '__main__':
    main()