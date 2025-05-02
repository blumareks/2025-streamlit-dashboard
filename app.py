#20250502 Marek Sadowski for Think 2025

import streamlit as st
import pandas as pd
import time
import requests
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging

from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Retrieve the database configuration from the environment
URI = os.getenv("URL")

# Alert Service API configuration
ALERT_API_URL = os.getenv("ALERT_API_URL")
X-API-KEY = os.getenv("x-api-key")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = URI #"postgresql://username:password@localhost:5432/your_database"

# Initialize database connection
@st.cache_resource
def init_db():
    return create_engine(DATABASE_URL)

def send_low_battery_alert(lat, lon, direction, battery_level):
    """Send alert to external service when battery is low"""
    try:
        payload = {
            "latitude": lat,
            "longitude": lon,
            "direction": direction,
            "battery_percentage": battery_level,
            "timestamp": datetime.now().isoformat()
        }

        headers = {
          'x-api-key': X-API-KEY,
          'Content-Type': 'application/json'
  }
       
        response = requests.post(ALERT_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Successfully sent low battery alert for battery level: {battery_level}%")
        return True
   
    except requests.RequestException as e:
        logger.error(f"Failed to send low battery alert: {e}")
        return False


def get_latest_data(engine):
    """Fetch the latest data from the database"""
    query = """
    SELECT *
    FROM vehicle_data
    ORDER BY timestamp DESC
    LIMIT 1
    """
    return pd.read_sql(query, engine)


def get_historical_data(engine, hours=1):
    """Fetch historical data for the last specified hours"""
    query = f"""
    SELECT *
    FROM vehicle_data
    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
    ORDER BY timestamp ASC
    """
    return pd.read_sql(query, engine)


def create_dashboard():
    st.set_page_config(
        page_title="EV Vehicle Monitor",
        page_icon="🚗",
        layout="wide"
    )
   
    st.title("🚗 EV Vehicle Monitor")
   
    # Initialize database connection
    engine = init_db()
   
    # Create placeholder for the last alert time
    if 'last_alert_time' not in st.session_state:
        st.session_state.last_alert_time = datetime.min
   
    # Create three columns for the main metrics
    col1, col2, col3 = st.columns(3)
   
    while True:
        try:
            print("Getting latest data")
            # Get latest data
            latest_data = get_latest_data(engine)
            print(latest_data)
            if not latest_data.empty:
                # Display main metrics
                with col1:
                    st.metric(
                        "Battery Level",
                        f"{latest_data['battery_level'].iloc[0]}%",
                        delta=None
                    )
               
                with col2:
                    st.metric(
                        "Speed",
                        f"{latest_data['speed'].iloc[0]} m/s",
                        delta=None
                    )
               
                with col3:
                    st.metric(
                        "Temperature",
                        f"{latest_data['battery_temperature'].iloc[0]}°C",
                        delta=None
                    )
               
                # Create two columns for graphs
                col_left, col_right = st.columns(2)
               
                print("Getting historical data")
                # Get historical data for graphs
                historical_data = get_historical_data(engine)
                print(historical_data)
                with col_left:
                    # Battery level over time
                    fig_battery = px.line(
                        historical_data,
                        x='timestamp',
                        y='battery_level',
                        title='Battery Level Over Time'
                    )
                    st.plotly_chart(fig_battery, use_container_width=True)
                   
                    # Battery details
                    st.subheader("Battery Details")
                    battery_details = pd.DataFrame({
                        'Metric': ['SOC', 'Voltage', 'Current', 'SOH'],
                        'Value': [
                            f"{latest_data['battery_soc'].iloc[0]}%",
                            f"{latest_data['battery_voltage'].iloc[0]}V",
                            f"{latest_data['battery_current'].iloc[0]}A",
                            f"{latest_data['battery_soh'].iloc[0]}%"
                        ]
                    })
                    st.table(battery_details)
               
                with col_right:
                    print("Getting map")
                    # Map with current location
                    fig_map = px.scatter_mapbox(
                        latest_data,
                        lat='latitude',
                        lon='longitude',
                        zoom=13,
                        title='Vehicle Location'
                    )
                    fig_map.update_layout(
                        mapbox_style="open-street-map",
                        margin={"r":0,"t":30,"l":0,"b":0}
                    )
                    st.plotly_chart(fig_map, use_container_width=True)
                   
                    # Location details
                    print("Getting location details")
                    st.subheader("Location Details")
                    location_details = pd.DataFrame({
                        'Metric': ['Latitude', 'Longitude', 'Altitude', 'Direction'],
                        'Value': [
                            f"{latest_data['latitude'].iloc[0]:.6f}",
                            f"{latest_data['longitude'].iloc[0]:.6f}",
                            f"{latest_data['altitude'].iloc[0]} m",
                            f"{latest_data['direction'].iloc[0]}°"
                        ]
                    })
                    st.table(location_details)
               
                # Check battery level and send alert if necessary
                battery_level = latest_data['battery_level'].iloc[0]
                current_time = datetime.now()
               
                if (battery_level < 20 and
                    current_time - st.session_state.last_alert_time > timedelta(minutes=5)):
                    alert_sent = send_low_battery_alert(
                        latest_data['latitude'].iloc[0],
                        latest_data['longitude'].iloc[0],
                        latest_data['direction'].iloc[0],
                        battery_level
                    )
                   
                    if alert_sent:
                        st.session_state.last_alert_time = current_time
                        st.warning(f"⚠️ Low battery alert sent! Battery level: {battery_level}%")
               
                # Display last update time
                st.text(f"Last updated: {latest_data['timestamp'].iloc[0]}")
           
            else:
                st.error("No data available from the database")
           
            # Sleep for 15 seconds
            time.sleep(15)
            st.rerun()
            #st.experimental_rerun()
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            st.error(f"Error updating dashboard: {str(e)}")
            time.sleep(15)
            st.rerun()


if __name__ == "__main__":
    create_dashboard()
    
