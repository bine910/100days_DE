# Week 1 - JOIN

- Inner join: chọn tất cả các bản ghi từ cả hai bảng thỏa mãn điều kiện join.
- Full join: chọn tất cả các bản ghi từ cả hai bảng, nếu không có bản ghi nào thỏa mãn điều kiện join thì sẽ trả về giá trị `null`.
- Left join: chọn tất cả các bản ghi từ bảng bên trái và các bản ghi từ bảng bên phải thỏa mãn điều kiện join, nếu không có bản ghi nào thỏa mãn điều kiện join thì sẽ trả về giá trị `null`.
- Right join: chọn tất cả các bản ghi từ bảng bên phải và các bản ghi từ bảng bên trái thỏa mãn điều kiện join, nếu không có bản ghi nào thì trả về giá trị `null`.
- Cross join: chọn tất cả các bản ghi từ cả hai bảng, kết quả trả về là tích Descartes của hai bảng.

## So sánh các loại join

- Khác nhau giữa inner join và left join:
	- Inner join chỉ trả về các bản ghi thỏa mãn điều kiện join.
	- Left join trả về tất cả các bản ghi từ bảng bên trái và các bản ghi từ bảng bên phải thỏa mãn điều kiện join, nếu không có bản ghi nào thỏa mãn điều kiện join thì sẽ trả về giá trị `null`.

## Where và Having

- Where lọc dữ liệu trước khi nhóm.
- Having lọc dữ liệu sau khi nhóm.
