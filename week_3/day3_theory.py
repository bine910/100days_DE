# 1. Đọc/ghi file text — with open()
#Đọc ghi file
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()

# "r"   # đọc (mặc định)
# "w"   # ghi — xóa sạch file cũ, tạo mới
# "a"   # append — ghi thêm cuối file
# "x"   # tạo mới — lỗi nếu file đã tồn tại
# with là context manager — tự đóng file khi xong, dù có lỗi hay không

#Ghi file
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("dòng 1\n")
    f.write("dòng 2\n")

# 2. Đọc/ghi CSV

import csv

# Đọc
with open("data.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)    # mỗi row là dict, key = header
    for row in reader:
        print(row["name"], row["score"])

# Ghi
rows = [
    {"name": "Binh", "score": 8.5},
    {"name": "An", "score": 9.2},
]
with open("output.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "score"])
    writer.writeheader()
    writer.writerows(rows)

#3. Đọc/ghi JSON
import json

# Đọc — giống JSON.parse() trong JS
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)          # file → dict/list

# Ghi — giống JSON.stringify()
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    # indent=2: format đẹp
    # ensure_ascii=False: giữ tiếng Việt, không escape thành \uXXXX

# Phân biệt 2 cặp:
json.load(file)     # đọc từ file
json.loads(string)  # parse từ string — giống JSON.parse()

json.dump(data, file)   # ghi vào file
json.dumps(data)        # convert thành string — giống JSON.stringify()

# 4. pathlib — thay thế nối string path

from pathlib import Path

base = Path("data")
file_path = base / "input.csv"      # dùng / thay os.path.join()

file_path.exists()         # file có tồn tại?
file_path.is_file()        # là file hay folder?
file_path.name             # "input.csv"
file_path.stem             # "input"  (tên không có extension)
file_path.suffix           # ".csv"
file_path.parent           # Path("data")

# Tạo folder
Path("output").mkdir(exist_ok=True)    # không lỗi nếu đã tồn tại

# Đọc/ghi nhanh không cần with open
content = file_path.read_text(encoding="utf-8")
file_path.write_text("hello", encoding="utf-8")

# List tất cả file CSV trong folder
for csv_file in Path("data").glob("*.csv"):
    print(csv_file.name)

# 5. Pattern thực tế: đọc → xử lý → ghi

from pathlib import Path
import csv
import json

def csv_to_json(input_path: str, output_path: str) -> None:
    # Đọc CSV
    with open(input_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Ghi JSON
    Path(output_path).parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"Converted {len(rows)} rows → {output_path}")