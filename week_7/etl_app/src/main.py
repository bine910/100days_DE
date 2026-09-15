import os
import json
import logging
import requests
import json
import csv
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

data = fetch(username)
if data:
    os.makedirs("data", exist_ok=True)
    with open("data/output.json", "w") as f:
        json.dump(data,f,indent=2)
    log.info("Saved to output.json")
    with open ("data/output.csv","w",newline="",encoding="utf-8")as f:
        w=csv.DictWriter(f,fieldnames=data[0].keys())
        w.writeheader()
        w.writerows(data)
