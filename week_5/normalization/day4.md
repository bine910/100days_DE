student_id
student_name
student_email
course_id
course_name
department_id
department_name
instructor_id
instructor_name
semester
grade


Step: [0NF → 1NF ]

Problem: [student_id một mình? Không — 1 sinh viên đăng ký nhiều môn → nhiều rows cùng student_id.
course_id một mình? Không — 1 môn có nhiều sinh viên.
(student_id, course_id) cùng nhau? Gần đúng nhưng 1 sinh viên có thể học lại cùng môn ở semester khác.
(student_id, course_id, semester) → đây mới là composite key — xác định duy nhất 1 row.
]

Decision: []

Result: [
student_id → student_name, student_email
course_id → course_name, department_id
department_id → department_name
instructor_id → instructor_name
(student_id, course_id, semester) → grade, instructor_id
]

Step: 1NF → 2NF

Problem: 
PK = (student_id, course_id, semester)
Nhưng: student_id → student_name, student_email
→ student_name chỉ phụ thuộc 1 PHẦN composite key
→ Partial dependency

PK = (student_id, course_id, semester)
Nhưng: course_id → course_name, department_id
→ student_name chỉ phụ thuộc 1 PHẦN composite key
→ Partial dependency


Decision:
Tách student_name, student_email ra bảng riêng theo student_id
Tách course_name, department_id ra bảng riêng theo course_id

Result:
students(student_id, student_name, student_email)
    PK: student_id
    FD: student_id → student_name, student_email
courses(course_id, course_name, department_id)
    PK: course_id
    FD: course_id → course_name, department_id
enrollments(student_id, course_id, semester, grade, instructor_id)
    PK: (student_id, course_id, semester)
    FK: student_id → students
    FK: course_id → courses

Step: 2NF → 3NF

Problem:
- Bảng courses: course_id → department_id → department_name (transitive dependency)
- Bảng enrollments: instructor_id → instructor_name (thiếu bảng chứa)

Decision:
- Tách department ra bảng riêng
- Tách instructor ra bảng riêng

Result:
departments(department_id,department_name)
    PK: department_id

instructors(instructor_id,instructor_name)
    PK: instructor_id

courses(course_id,course_name,department_id)  ← 
    PK: course_id
    FK: department_id

enrollments(student_id, course_id, semester, grade, instructor_id) 
    PK: student_id, course_id,semester
    FK: instructor_id

Final schema (tất cả bảng sau 3NF):
1. students(...)
2. courses(...)
3. departments(...)
4. instructors(...)
5. enrollments(...)

