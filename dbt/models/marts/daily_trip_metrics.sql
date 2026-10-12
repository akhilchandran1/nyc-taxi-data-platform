select
    trip_date,
    count(*) as trip_count,
    sum(total_amount) as gross_revenue,
    avg(total_amount) as average_total_amount,
    avg(fare_amount) as average_fare_amount,
    avg(tip_amount) as average_tip_amount,
    avg(trip_distance) as average_trip_distance,
    avg(trip_duration_minutes) as average_trip_duration_minutes,
    sum(case when quality_status = 'flagged' then 1 else 0 end) as flagged_trip_count
from {{ ref('fct_yellow_trips') }}
group by trip_date
