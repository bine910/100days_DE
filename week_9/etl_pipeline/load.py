import pandas as pd
import psycopg2
import logging
from tenacity import retry, stop_after_attempt, wait_fixed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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

        # 2. UPSERT
        sql = """
            INSERT INTO gold_price_daily
                (date, open, high, low, close, volume)
            VALUES
                (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date)
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume;
        """

        # 3. Load từng row
        for _, row in df.iterrows():
            cursor.execute(
                sql,
                (
                    row["Date"],
                    row["Open"],
                    row["High"],
                    row["Low"],
                    row["Close"],
                    row["Volume"],
                )
            )

        # 4. Commit
        conn.commit()

        logging.info("Loaded %d rows successfully", len(df))

    except Exception as e:
        if conn:
            conn.rollback()

        logging.error("Load failed: %s", e)
        raise

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()