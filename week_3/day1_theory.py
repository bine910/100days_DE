#List

l = [1, 2, 3, 4, 5]
l.append(7)
l.pop()
l[1]
len(l)
#Dict

user = {'name': 'John', 'age': 30, 'city': 'New York'}
user.get("email", None)  # None nếu key không tồn tại (JS trả undefined)
user["email"] = "a@b.c"  # thêm key mới
for key, value in user.items():
    print(key, value)

print(user.get("email", None))

#Tuple= Array nhưng bất biến (immutable)
t = (1, 2, 3, 4, 5)
# t[1]=0  # This would raise an error since tuples are immutable
point = (10, 20)
x, y = point        # destructuring — JS: const [x, y] = point

print(t[1])

#Set
s = {1, 2, 3, 4, 5}
s.add(2)# Thêm phần tử vào set
s.discard(2)  # Xóa phần tử khỏi set
print( 2 in s)  # tra cứu phần tử trong set, trả về True/False
# Set operations (JS không có sẵn)
a = {1, 2, 3}
b = {2, 3, 4}
a & b    # {2, 3}     — intersection
a | b    # {1,2,3,4}  — union
a - b    # {1}        — difference


#List/Dict Comprehension = .map() + .filter() gộp lại

#List Comprehension
nums = [1, 2, 3, 4, 5]
result =[x*10 for x in nums if x%2==0]

#Dict Comprehension
names = ["Binh", "An", "Duc"]
name_lengths = {name: len(name) for name in names}

print(result)  
print(name_lengths)