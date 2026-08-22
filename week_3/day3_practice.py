import json
import csv
from pathlib import Path


#Bài 1: Tạo file data/students.csv có 5 dòng (name, score, city). 
# Viết script đọc CSV, lọc student có score > 8.0, ghi ra data/top_students.json.
with open ("week_3/data/student.csv","w",encoding="utf-8") as f:
    f.write("name,score,city\n")
    f.write("Binh,8.5,Hanoi\n")
    f.write("An,9.2,HCMC\n")
    f.write("Duc,7.8,Danang\n")
    f.write("Linh,6.5,Hanoi\n")
    f.write("Tuan,8.9,Hue\n")

res=[]
with open ("week_3/data/student.csv","r",encoding="utf-8") as f:
    reader=csv.DictReader(f)
    for r in reader:
        if(float(r["score"])>8.0): res.append(r)
    print(res)
with open ("week_3/data/top_student.json","w",encoding="utf-8") as f:
    json.dump(res,f,indent=2,ensure_ascii=False)

#Bài 2: Viết function json_to_csv(json_path: str, csv_path: str) 
# — ngược lại bài 1: đọc JSON array, ghi ra CSV.
def json_to_csv(json_path: str, csv_path: str)-> None:
    with open(json_path,"r",encoding="utf-8") as f:
        data=json.load(f)
        print(data)
    with open(csv_path,"w",newline="",encoding="utf-8") as f:
        writer =csv.DictWriter(f,fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

json_to_csv("week_3/data/top_student.json","week_3/data/new.csv")

#Bài 3: Dùng pathlib list tất cả file trong folder data/, 
# in ra tên + extension + size (dùng .stat().st_size).
base= Path("week_3/data")
for x in base.glob("*.csv"):
    print(x.name)
    print(x.suffix) 
    print(x.stem)
    print(x.stat().st_size)
#Bài 4: Viết function merge_csv_files(folder: str, output: str) — đọc tất cả file .csv trong folder,
#  gộp thành 1 file CSV duy nhất (hint: Path(folder).glob("*.csv")).

def merge_csv_files(folder: str, output: str) -> None:
    temp =[]
    for x in Path(folder).glob("*.csv"):
        with open(x, "r", encoding="utf-8") as f:
            temp.append(list(csv.DictReader(f)))
    with open (output,"w",newline="",encoding="utf-8") as f:
        w= csv.DictWriter(f,fieldnames=temp[0][0].keys())
        w.writeheader()
        for x in temp:
            w.writerows(x)

merge_csv_files("week_3/data","week_3/sum.csv")