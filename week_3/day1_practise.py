#1. Cho list scores = [85, 92, 78, 95, 88, 76, 91] 
# → dùng comprehension lọc ra điểm >= 90, nhân đôi mỗi điểm 
scores = [85, 92, 78, 95, 88, 76, 91]
# result = [ x*2 for x in scores if x>90]

# 2. Cho dict products = {"laptop": 1000, "mouse": 25, "keyboard": 75, "monitor": 300}
# → lọc ra sản phẩm giá > 50, trả về dict mới

products = {"laptop": 1000, "mouse": 25, "keyboard": 75, "monitor": 300}

# result = {key:value for key,value in products.items() if value >50}
    


# 3. Cho 2 list team_a = ["Binh", "An", "Duc"] và team_b = ["An", "Linh", "Duc"] 
# → dùng set tìm người có mặt ở cả 2 team

a = ["Binh", "An", "Duc"]
b = ["An", "Linh", "Duc"]

set_a = set(a)    
set_b = set(b)
# result = set(a) & set(b)

# 4. Viết function count_words(text: str) -> dict 
# nhận chuỗi, trả về dict đếm số lần xuất hiện mỗi từ (hint: .split() + dict)
def count_words(text: str):
    r={}
    x=text.split()
    for temp in x :
        r[temp] = r.get(temp, 0) + 1
    return r    
# print(count_words(" Hello Binh"))

# Cho list of tuples students = [("Binh", 8.5), ("An", 9.2), ("Duc", 7.8)]
# → dùng destructuring in ra "An: 9.2" cho mỗi student,
# và tìm student có điểm cao nhất (hint: max() với key)
students = [("Binh", 8.5), ("An", 9.2), ("Duc", 7.8)]
r={}
best_name, best_score = max(students, key=lambda x: x[1])
print(f"{best_name}: {best_score}")