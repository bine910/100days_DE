# Bài 1 — Default + keyword args: 
# Viết function create_pipeline_config(name: str, schedule: str = "daily", retry: int = 3, timeout: int = 300) -> dict 
# trả về dict chứa tất cả config. 
# Gọi thử 3 cách: chỉ truyền name, truyền positional, truyền keyword.
def create_pipeline_config(name: str, schedule: str = "daily", retry: int = 3, timeout: int = 300) -> dict:
    return (name,schedule,retry,timeout)
print(create_pipeline_config("Binh"))
print(create_pipeline_config("nam","mon",3,5))
print(create_pipeline_config(name="bac",retry= 4))

#Bài 2 — *args: Viết function merge_datasets(*datasets: list) -> list 
# nhận nhiều list, 
# gộp thành 1 list duy nhất, loại bỏ phần tử trùng, trả về sorted list.
list_a = [9,10,100, 2, 3, 4]
list_b = [3, 4, 5, 6]
list_c = [5, 6, 7, 8]
def merge_datasets(*datasets: list) -> list:
    
    result=[x for dataset in datasets for x in dataset]
    s=set(result)
    return sorted(s)

    
print(merge_datasets(list_a,list_b,list_c))

#Bài 3 — **kwargs + type hints: Viết function build_query(**filters) -> str 
# nhận các keyword argument rồi tạo SQL WHERE clause


def  build_query(**filters) -> str:
    s="WHERE "
    s +=" AND ".join( f"{k} = '{v}'"if isinstance(v, str)else f"{k} = {v}"for k,v in filters.items())
    return s
print(build_query(city="Hanoi", age=22, active=True))

 # 4. Exception handling: Viết function safe_divide(a, b) -> float 
 # chia a cho b. Bắt 3 loại lỗi cụ thể
 # : ZeroDivisionError, TypeError (khi truyền string), và Exception chung.
 #  Mỗi loại in message khác nhau. Dùng else in kết quả khi thành công.
def safe_divide(a, b) -> float :
    try:
        result = a /b
    except ZeroDivisionError :
        print("Error: You cannot divide by zero.")
        result = None
    except TypeError:
        print("Error: You cannot divide by string.")
        result = None
    except Exception as e :
        print(f"Lỗi khác: {e}")
    else :
        print (result)
    finally:
        print("Cleaning up resources...")
print(safe_divide(0,0))

#5 — Custom Exception: Tạo class InvalidDataError(Exception) 
# có attribute row_number và reason. 
# Viết function validate_rows(data: list[dict]) -> None 
# kiểm tra mỗi dict phải có key "name" và "score", score phải >= 0.
#  Raise InvalidDataError khi vi phạm. 

data = [
    {"name": "Binh", "score": 8.5},
    {"name": "An"},                    # thiếu score
    {"name": "Duc", "score": -3},      # score âm
]

class InvalidDataError(Exception):
    def __init__(self, rowNum: int, reason: str):
        super().__init__(f"invalid in '{rowNum}': {reason}")
def validate_rows(data: list[dict]) -> None :
    row =1
    for temp in data:
        if temp.get("name")is None : raise InvalidDataError(row,"ko co name")
        elif temp.get("score" )is None : raise InvalidDataError(row,"ko co score")
        elif temp.get("score")<0: raise InvalidDataError(row,"score âm")
        row += 1

try :
    validate_rows(data)
except InvalidDataError as e:
    print(e)

            