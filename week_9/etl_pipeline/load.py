import pandas as pd
import psycopg2
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from psycopg2.extras import execute_values
from logger import log

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def load(df: pd.DataFrame) -> None:
    conn = None
    cursor = None
    
    try:
            # 1. Connect PostgreSQL
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="de_week9",
                user="postgres",
                password="postgres"
            )
    
            cursor = conn.cursor()
    
            sql = """
                INSERT INTO gold_price_daily (date, open, high, low, close, volume)
                VALUES %s
                ON CONFLICT (date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
            """

            data = [tuple(row) for row in df.values]
            execute_values(cursor, sql, data)
    
            # 4. Commit
            conn.commit()
    
            log.info("Loaded %d rows successfully", len(df))
    
    except Exception as e:
            if conn:
                conn.rollback()
    
            log.error("Load failed: %s", e)
            raise
    
    finally:
            if cursor:
                cursor.close()
    
            if conn:
                conn.close()