select trip_date, pickup_hour
from {{ ref('hourly_pickup_metrics') }}
group by trip_date, pickup_hour
having count(*) > 1
