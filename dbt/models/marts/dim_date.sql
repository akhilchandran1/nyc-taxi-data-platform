with dates as (
    select distinct cast(pickup_datetime as date) as trip_date
    from {{ ref('stg_yellow_trips') }}
)

select
    trip_date,
    extract(year from trip_date)::int as year,
    extract(month from trip_date)::int as month,
    extract(day from trip_date)::int as day,
    extract(dow from trip_date)::int as day_of_week,
    to_char(trip_date, 'Day') as day_name,
    case when extract(dow from trip_date) in (0, 6) then true else false end as is_weekend
from dates
