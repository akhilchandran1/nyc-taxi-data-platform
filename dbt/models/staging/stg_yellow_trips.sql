with source as (
    select * from {{ source('raw', 'raw_yellow_trips') }}
),

renamed as (
    select
        id as raw_trip_id,
        dataset_name,
        trip_hash,
        vendor_id,
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
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        congestion_surcharge,
        airport_fee,
        cbd_congestion_fee,
        total_amount,
        payment_type,
        quality_status,
        quality_issues,
        loaded_at,
        extract(epoch from (dropoff_datetime - pickup_datetime)) / 60.0 as trip_duration_minutes
    from source
)

select * from renamed
