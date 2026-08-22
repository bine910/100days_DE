# Bài 1: Cài requests và python-dotenv:

# bash
# pip install requests python-dotenv

# Bài 2: Tạo file .env trong week_3/ chứa:

# GITHUB_USERNAME=octocat

# Tạo .env.example copy giống nhưng value là placeholder.

# Bài 3: Viết file week_3/day5_practice.py:

# Load .env lấy GITHUB_USERNAME
# Gọi API https://api.github.com/users/{username}
# Log mỗi bước: bắt đầu, response status, số repos, lưu file
# Bắt lỗi timeout, HTTP error
# Lưu kết quả ra data/github_user.json
# Không hardcode username trong code

import os
import json
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
gitEnpoint= os.environ.get("GITHUB_USERNAME")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - tên file: %(filename)s -  %(message)s - số dòng: %(lineno)d - tên function: %(funcName)s  "
)

log= logging.getLogger(__name__)

def fetch(username:str) -> dict |None :
    try:
        log.info(f"Fetching https://api.github.com/users/{username}")
        res= requests.get(f"https://api.github.com/users/{username}",timeout=10)
        res.raise_for_status()
        data = res.json()
        log.info(f"User has {data['public_repos']} public repos")
        log.info(f"Sucess: {res.status_code}")
        return res.json()
    except requests.exceptions.RequestException as e:
        log.error(f"Failed: {e}")
        return None


data= fetch(gitEnpoint)
if data:
    with open ("week_3/data/github_user.json","w")as f:
        json.dump(data,f,indent=2)
    log.info("Saved to data/github_user.json")
    
# Bài 4: Chạy script, mở file pipeline.log kiểm tra log có timestamp + level đúng không. Thử đổi username trong .env thành user không tồn tại, xem log error ra sao.