import os
import json
import logging
import time
import requests
import json
import csv
import psycopg2
from dotenv import load_dotenv

# Gọi API → parse → lưu file. Yêu cầu:

# Load config từ .env (không hardcode)
# Gọi API public, parse JSON response
# Log mỗi bước: bắt đầu, status, số record, lưu file
# Bắt lỗi: timeout, HTTP error, JSON parse error
# Lưu kết quả ra cả CSV và JSON
# Có requirements.txt
load_dotenv()
username=os.environ.get("GITHUB_USERNAME")

# Connection string lấy từ env
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "de_practice")
DB_USER = os.environ.get("DB_USER", "de_user")
DB_PASS = os.environ.get("DB_PASS", "de_pass")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

log= logging.getLogger(__name__)

def fetch(username:str)->dict|None:
    try :
        log.info(f"Fetching https://api.github.com/users/{username}/repos")
        res= requests.get(f"https://api.github.com/users/{username}/repos",timeout=10)
        res.raise_for_status()
        data=res.json()
        log.info(f"Thanh cong:{res.status_code}")
        log.info(f"So record :{len(data)}")
        return data
    except requests.exceptions.RequestException as e:
        log.error(f"That bai:{e}")
        return None
def load_to_db(data, retries=5, delay=3):
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT,
                dbname=DB_NAME, user=DB_USER, password=DB_PASS
            )
            break
        except psycopg2.OperationalError:
            log.warning(f"PostgreSQL chưa sẵn sàng, thử lại ({attempt+1}/{retries})...")
            time.sleep(delay)
    else:
        log.error("Không thể kết nối PostgreSQL")
        return

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS github_repos (
            id INT PRIMARY KEY,
            name TEXT,
            full_name TEXT,
            html_url TEXT,
            description TEXT,
            created_at TEXT
        )
    """)

    for repo in data:
        cur.execute("""
            INSERT INTO github_repos (id, name, full_name, html_url, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            repo["id"], repo["name"], repo["full_name"],
            repo["html_url"], repo.get("description"), repo["created_at"]
        ))

    conn.commit()
    log.info(f"Loaded {len(data)} repos to PostgreSQL")
    cur.close()
    conn.close()
data = fetch(username)
if data:
    load_to_db(data)
