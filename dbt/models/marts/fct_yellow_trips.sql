select
    raw_trip_id,
    trip_hash,
    cast(pickup_datetime as date) as trip_date,
    pickup_datetime,
    dropoff_datetime,
    passenger_count,
    trip_distance,
    ratecode_id,
    store_and_fwd_flag,
    request_source,
    pickup_location_id,
    dropoff_location_id,
    fare_amount,
    tip_amount,
    tolls_amount,
    congestion_surcharge,
    airport_fee,
    cbd_congestion_fee,
    total_amount,
    payment_type,
    quality_status,
    trip_duration_minutes,
    case
        when fare_amount > 0 then tip_amount / fare_amount
        else null
    end as tip_rate
from {{ ref('stg_yellow_trips') }}
