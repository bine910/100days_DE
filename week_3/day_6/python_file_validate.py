import os
import json
import logging
import requests
import csv
import json
from pathlib import Path
from dotenv import load_dotenv


# Đọc file → kiểm tra data → log kết quả. Yêu cầu:

# Đọc CSV hoặc JSON input (dùng file output từ script 1)
# Validate: thiếu field, giá trị rỗng, kiểu dữ liệu sai, duplicate
# Custom exception cho validation error
# Log tổng kết: bao nhiêu row OK, bao nhiêu row lỗi, lỗi ở dòng nào
# Không crash khi gặp lỗi — gom hết rồi report
REQUIRED_FIELDS = ["name", "language", "stargazers_count","forks_count"]
FIELD_TYPES ={
    "name": str,
    "stargazers_count": int,
    "forks_count": int
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s - %(lineno)s - %(funcName)s"
)

log = logging.getLogger(__name__)
errors=[]
checkDup= set()

class CheckFieldError(Exception):
    def __init__(self, row_number: int, field: str, error_type: str, message: str):
        self.row_number = row_number
        self.field = field
        self.error_type = error_type  # "missing", "empty", "type", "duplicate"
        super().__init__(f"Row {row_number} - [{error_type}] {field}: {message}")

with open("week_3/data/output.csv","r",encoding="utf-8") as f:
    read = list(csv.DictReader(f))
    for i,row in enumerate(read,start=1):
        missing = [field for field in REQUIRED_FIELDS if field not in row]
        name = row.get("name", "")
        if name in checkDup:
            errors.append(CheckFieldError(i, "name", "duplicate", f"'{name}' da ton tai"))
        else:
            checkDup.add(name)
        if missing:
            for field in missing:
                errors.append(CheckFieldError(i,field,"thieu field","missing"))
        if(row.get("name")=="") :errors.append(CheckFieldError(i,"name","thieu value","missing"))
        if(row.get("stargazers_count")=="") :errors.append(CheckFieldError(i,"stargazers_count","thieu value","missing"))
        if(row.get("forks_count")=="") :errors.append(CheckFieldError(i,"forks_count","thieu value","missing"))
        for field in ["stargazers_count", "forks_count"]:
            try:
                int(row.get(field ,""))
            except ValueError as e:
                errors.append(f"failed:{e}")
log.info(f"Total rows: {len(read)}")
log.info(f"Valid: {(len(read) - len(errors))}")
log.info(f"Invalid: {len(errors)}")

for e in errors:
    log.error(str(e))

    

            

