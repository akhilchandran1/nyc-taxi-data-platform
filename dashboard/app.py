"""Streamlit analytics dashboard for loaded NYC taxi data."""

from __future__ import annotations

import logging
import os

import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://taxi:taxi@localhost:5432/nyc_taxi")
logger = logging.getLogger(__name__)


@st.cache_data(ttl=300)
def load_daily_metrics():
    import pandas as pd

    engine = create_engine(DATABASE_URL)
    query = text(
        """
        select trip_date, trip_count, gross_revenue, average_total_amount,
               average_trip_distance, flagged_trip_count
        from analytics_marts.daily_trip_metrics
        order by trip_date
        """
    )
    try:
        return pd.read_sql(query, engine)
    finally:
        engine.dispose()


@st.cache_data(ttl=300)
def load_hourly_metrics():
    import pandas as pd

    engine = create_engine(DATABASE_URL)
    try:
        return pd.read_sql(
            text(
                """
                select trip_date, pickup_hour, trip_count, average_trip_distance,
                       average_total_amount
                from analytics_marts.hourly_pickup_metrics
                order by trip_date, pickup_hour
                """
            ),
            engine,
        )
    finally:
        engine.dispose()


st.set_page_config(page_title="NYC Taxi Analytics", layout="wide")
st.title("NYC Taxi Analytics")

try:
    daily = load_daily_metrics()
    hourly = load_hourly_metrics()
except Exception:
    logger.exception("Could not load analytics data")
    st.error("Analytics tables are unavailable. Load the data and run dbt first.")
    st.stop()

if daily.empty:
    st.info("No modeled trip data is available yet.")
    st.stop()

min_date, max_date = daily["trip_date"].min(), daily["trip_date"].max()
selected_range = st.date_input(
    "Trip date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
if isinstance(selected_range, tuple) and len(selected_range) == 2:
    start_date, end_date = selected_range
    daily = daily[(daily["trip_date"] >= start_date) & (daily["trip_date"] <= end_date)]
    hourly = hourly[
        (hourly["trip_date"] >= start_date) & (hourly["trip_date"] <= end_date)
    ]

if daily.empty:
    st.info("No trips in the selected date range.")
    st.stop()

# Weight averages by trip count when collapsing daily hourly records.
if not hourly.empty:
    hourly = hourly.assign(
        weighted_distance=hourly["average_trip_distance"] * hourly["trip_count"],
        weighted_total=hourly["average_total_amount"] * hourly["trip_count"],
    )
    hourly = hourly.groupby("pickup_hour", as_index=False).agg(
        trip_count=("trip_count", "sum"),
        weighted_distance=("weighted_distance", "sum"),
        weighted_total=("weighted_total", "sum"),
    )
    hourly["average_trip_distance"] = hourly["weighted_distance"] / hourly["trip_count"]
    hourly["average_total_amount"] = hourly["weighted_total"] / hourly["trip_count"]

total_trips = int(daily["trip_count"].sum())
gross_revenue = float(daily["gross_revenue"].sum())
avg_distance = (
    float((daily["average_trip_distance"] * daily["trip_count"]).sum() / total_trips)
    if total_trips else 0.0
)
flagged_count = int(daily["flagged_trip_count"].sum())

metric_cols = st.columns(4)
metric_cols[0].metric("Trips", f"{total_trips:,}")
metric_cols[1].metric("Gross revenue", f"${gross_revenue:,.2f}")
metric_cols[2].metric("Avg distance", f"{avg_distance:.2f} mi")
metric_cols[3].metric("Flagged trips", f"{flagged_count:,}")

left, right = st.columns(2)
with left:
    st.plotly_chart(
        px.line(daily, x="trip_date", y="trip_count", title="Trip trend by date"),
        width="stretch",
    )
    st.plotly_chart(
        px.bar(hourly, x="pickup_hour", y="trip_count", title="Pickup demand by hour"),
        width="stretch",
    )
with right:
    st.plotly_chart(
        px.line(daily, x="trip_date", y="gross_revenue", title="Gross revenue by date"),
        width="stretch",
    )
    st.plotly_chart(
        px.scatter(
            hourly,
            x="average_trip_distance",
            y="average_total_amount",
            size="trip_count",
            title="Distance vs fare by hour",
        ),
        width="stretch",
    )
