#1. requests — gọi API bằng Python
import requests

# res=requests.get("https://api.github.com/users/octocat")
# res.status_code        # 200
# res.json()             # parse JSON → dict (giống res.json() trong JS)
# res.text               # raw string
# res.headers             # response headers

res1= requests.post(
    "https://httpbin.org/post",
    json={"name":"Binh","age":22},
    headers={"Authorozation":"Bearer xxx"},
    timeout=10
)
try:
    response = requests.get("https://api.example.com/data", timeout=5)
    response.raise_for_status()   # raise nếu status 4xx/5xx
    data = response.json()
except requests.exceptions.Timeout:
    print("Request timeout")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")

# 2. logging — thay print() bằng logger
# Setup 1 lần
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Sử dụng
logger.debug("Chi tiết debug")      # không hiện nếu level=INFO
logger.info("Pipeline started")      # thông tin bình thường
logger.warning("Missing 3 rows")     # cảnh báo
logger.error("API returned 500")     # lỗi
logger.critical("Database down")     # lỗi nghiêm trọng
# 3. Python-dotenv - load .env file
import os
from dotenv import load_dotenv

load_dotenv()    # đọc file .env → đưa vào os.environ

api_key = os.environ.get("API_KEY")
base_url = os.environ.get("BASE_URL")

# 4 Kết hợp tất cả — pattern thực tế
import os
import json
import logging
import requests
from dotenv import load_dotenv

# Config
load_dotenv()
API_KEY = os.environ.get("API_KEY")

# Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def fetch_data(url: str) -> dict | None:
    try:
        logger.info(f"Fetching {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        logger.info(f"Success: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed: {e}")
        return None

data = fetch_data("https://api.github.com/users/octocat")
if data:
    with open("output.json", "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Saved to output.json")