select
    trip_date,
    extract(hour from pickup_datetime)::int as pickup_hour,
    count(*) as trip_count,
    avg(trip_distance) as average_trip_distance,
    avg(total_amount) as average_total_amount
from {{ ref('fct_yellow_trips') }}
group by trip_date, pickup_hour
