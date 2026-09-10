BEGIN;
INSERT INTO dim_date (date_key,
    full_date,
    day_of_week,
    day_name,
    day_of_month,
    month,
    month_name,
    quarter,
    year,
    is_weekend,
    is_holiday
    )
select 
    to_char(d, 'YYYYMMDD')::integer,
    d::date,
    extract(isodow from d)::smallint,
    to_char(d, 'FMDay')::varchar(10),
    extract(day from d)::smallint,
    extract(month from d)::smallint,
    to_char(d, 'FMMonth')::varchar(20),
    extract(quarter from d)::smallint,
    extract(year from d)::smallint,
    EXTRACT(ISODOW FROM d) IN (6, 7),
    FALSE

FROM generate_series(
    '2020-01-01'::date,
    '2030-12-31'::date,
    interval '1 day'
) AS d
 ON CONFLICT (date_key) DO NOTHING;
COMMIT;