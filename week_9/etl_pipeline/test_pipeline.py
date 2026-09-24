from logger import log
import psycopg2
from psycopg2.extras import execute_values


def test_pipeline():
    conn = None
    try:
        # Attempt to connect to the PostgreSQL database
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="de_week9",
            user="postgres",
            password="postgres"
        )
        log.info("Database connection successful")
        cursor = conn.cursor()
        # Test 1
        cursor.execute("SELECT COUNT(*) FROM gold_price_daily WHERE date BETWEEN %s AND %s", ('2024-01-01', '2024-01-31'))
        count = cursor.fetchone()[0]
        assert count == 22, f"Expected 22 rows, got {count}"
        log.info(f"Test 1 passed: {count} rows")
        # Test 2
        cursor.execute("SELECT COUNT(*) FROM gold_price_daily WHERE high < low")
        bad_rows = cursor.fetchone()[0]
        assert bad_rows == 0, f"Found {bad_rows} rows where high < low"
        log.info(f"Test 2 passed: no rows where high < low")    
        # Test 3
        cursor.execute("SELECT COUNT(*) FROM gold_price_daily")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT date) FROM gold_price_daily")
        distinct = cursor.fetchone()[0]
        assert total == distinct, f"Duplicates found: {total} rows but {distinct} distinct dates"
        log.info(f"Test 3 passed: {total} total = {distinct} distinct dates")
    except Exception as e:
        log.error("Database connection failed: %s", e)
        assert False, "Database connection failed"
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_pipeline()