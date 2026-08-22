# 1.Function cơ bản

def greet(name: str) -> str:
    return f"Hello {name}"

print(greet("Bình"))

# 2. Default parameter + keyword argument

def create_user(name: str, role: str = "viewer") -> dict:
    return {"name": name, "role": role}

print(create_user("Bình",role="admin"))

# 3. *args và **kwargs

def add(*args):# *args = gom positional arguments thành tuple
    return sum(args)

print(add(1,2,3,4,5))

def creat_object(**k):# **kwargs = gom keyword arguments thành dict
    return k

print(creat_object(name="Binh",age=22))
# kwargs = {"name": "Binh", "age": 22}

#4. Type Hints

#basic type
def process(name:str, count :int ,active: bool =True)-> list[str]:
    return [name] * count 
print(process("Binh",9,False))


from typing import Optional

#complex type
def find(use_id:int)-> Optional[dict]:
    return None

print(find(None))

# List, Dict
def summarize(scores: list[int]) -> dict[str, float]:
    return {"avg": sum(scores) / len(scores)}
print(summarize([1,2,3,4,5]))

# 5. Exception Handling
# try:
#     data = json.loads(text)
# except json.JSONDecodeError as e:
#     print(f"JSON lỗi: {e}")
# except Exception as e:
#     print(f"Lỗi khác: {e}")
# else:
#     print("Parse thành công")   # chỉ chạy khi KHÔNG có lỗi — JS không có
# finally:
#     cleanup()

# 6. Custom Exception

class DataValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation failed on '{field}': {message}")

# Sử dụng:
def validate_age(age: int) -> None:
    if age < 0:
        raise DataValidationError("age", "cannot be negative")

try:
    validate_age(-5)
except DataValidationError as e:
    print(e)          # Validation failed on 'age': cannot be negative
    print(e.field)    # age