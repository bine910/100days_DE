/*
- inner join : chọn tát cả các bản ghi từ cả hai bảng thỏa mãn điều kiện join

- full  join : chọn tất cả các bản ghi từ cả hai bảng, nếu không có bản ghi nào thỏa mãn điều kiện
     join thì sẽ trả về giá trị null

- left join : chọn tất cả các bản ghi từ bảng bên trái và các bản ghi từ bảng bên phải thỏa mãn 
    điều kiện join, nếu không có bản ghi nào thỏa mãn điều kiện join thì sẽ trả về giá trị null

- right join : chọn tất cả các bản ghi từ bảng bên phải và các bản ghi từ bảng trái thỏa mãn 
    điều kiện join, nếu không có bản ghi nào thì trả về giá trị null

- cross join : chọn tất cả các bản ghi từ cả hai bảng, kết quả trả về là tích Descartes của hai bảng
- sự khác nhau giữa inner join và left join 
    là inner join chỉ trả về các bản ghi thỏa mãn điều kiện join 
    còn left join trả về tất cả các bản ghi từ bảng bên trái 
    và các bản ghi từ bảng bên phải thỏa mãn điều kiện join,
     nếu không có bản ghi nào thỏa mãn điều kiện join thì sẽ trả về giá trị null    
- sự khác nhau giữa where và having là
     where lọc dữ liệu trước khi nhóm 
     còn having lọc dữ liệu sau khi nhóm
*/
-- Tên khách hàng
-- Tên phim đã thuê
-- Ngày thuê
select c.first_name,c.last_name,r.rental_date,f.title 
from customer c
join rental r
on c.customer_id=r.customer_id
join inventory i
on r.inventory_id=i.inventory_id
join film f
on i.film_id= f.film_id