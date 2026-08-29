from src.extract import load_orders, load_order_items, load_products, load_categories
from src.transform import clean_orders, build_sales, revenue_by_category,revenue_by_month
from src.report import save_csv, plot_chart

def main():
    orders=load_orders()
    order_items=load_order_items()
    products=load_products()
    categories=load_categories()
    orders=clean_orders(orders)
    sales= build_sales(orders,order_items,products,categories)
    revenueByCategory= revenue_by_category(sales)
    save_csv(revenueByCategory,'output/output.csv')
    plot_chart(revenue_by_month(sales),'Monthly Revenue Trend', 'output/monthly_revenue_trend.png','line')
    plot_chart(revenue_by_month(sales),'Monthly Revenue Trend', 'output/monthly_revenue_trend.png','bar')


if __name__ == '__main__':
    main()