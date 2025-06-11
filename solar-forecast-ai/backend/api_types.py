"""
Solar Forecast AI - API Types and Data Structures
==============================================

System Design:
-------------
This module implements the core data structures and type definitions that power
the Solar Forecast AI system's intelligent weather data processing.

Key Features:
- Flexible API type system for multiple weather data sources
- Smart intent analysis using NLP and pattern matching
- Structured parameter management for API requests
- Location and time frame processing

Technical Implementation:
-----------------------
The module uses:
- Enum classes for type safety
- Regular expressions for pattern matching
- Type hints for better code maintainability
- Structured error handling
"""

from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re

class APIType(Enum):
    """
    Supported API Types for Weather Data
    ----------------------------------
    Defines the different types of weather APIs integrated into the system.
    Each type corresponds to a specific weather data service and capability.
    """
    FORECAST = "forecast"     # Standard weather forecasting
    ARCHIVE = "archive"       # Historical weather data
    MARINE = "marine"        # Marine and ocean conditions
    AIR_QUALITY = "air_quality"  # Air quality metrics
    SNOW = "snow"           # Snow and winter conditions
    CLIMATE = "climate"      # Long-term climate data

class TimeFrame(Enum):
    """
    Time Frame Specifications
    -----------------------
    Defines the temporal scope for weather queries.
    Supports various time ranges for different analysis needs.
    """
    HOURLY = "hourly"         # Hour-by-hour forecast
    DAILY = "daily"           # Day-by-day forecast
    HISTORICAL = "historical"  # Past weather data

class WeatherIntent:
    """
    Weather Query Intent Parser
    -------------------------
    Analyzes and structures user queries into actionable weather data requests.
    
    Features:
    - Intent classification
    - Time frame detection
    - Location extraction
    - Parameter validation
    """
    def __init__(self):
        self.api_type = APIType.FORECAST
        self.time_frame = TimeFrame.DAILY
        self.location = None
        self.start_date = None
        self.end_date = None
        self.specific_params = []

def extract_location(message: str) -> Optional[str]:
    """Extract location from the message using common patterns."""
    message = message.strip()
    
    # Common location prepositions and keywords
    prepositions = r"(?:in|at|for|of|near|around)"
    conditions = r"(?:weather|forecast|condition|temperature|climate|air quality|marine conditions?|wave height|wind)"
    time_markers = r"(?:current|today|tomorrow|now|tonight|this week)"
    question_words = r"(?:what|how|when|where|is|are|will)"
    
    # Patterns ordered by specificity
    patterns = [
        # Pattern for "what are the conditions in location"
        rf"{question_words}\s+(?:is|are)\s+(?:the\s+)?{conditions}\s+{prepositions}\s+([A-Za-z\s,]+?)(?:\s+{time_markers})?[\?]?$",
        
        # Pattern for "location conditions"
        rf"(?:{prepositions}\s+)?([A-Za-z\s,]+?)\s+{conditions}",
        
        # Pattern for "conditions in location"
        rf"{conditions}\s+{prepositions}\s+([A-Za-z\s,]+?)(?:\s+{time_markers})?[\?]?$",
        
        # Pattern for "in location"
        rf"{prepositions}\s+([A-Za-z\s,]+?)(?:\s+{time_markers})?[\?]?$"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Remove any trailing punctuation
            location = re.sub(r'[.,!?]+$', '', location)
            # Remove any weather-related words that might have been captured
            location = re.sub(rf"\b(?:{conditions}|{time_markers}|{question_words})\b", '', location, flags=re.IGNORECASE)
            # Remove any extra whitespace and standardize it
            location = ' '.join(location.split())
            if location and len(location) >= 2:  # Ensure we have a meaningful location
                return location
    
    # If no match found with patterns, try to find the last quoted location
    quoted_match = re.search(r'"([^"]+)"', message)
    if quoted_match:
        location = quoted_match.group(1).strip()
        if location and len(location) >= 2:
            return location
    
    return None

def analyze_weather_intent(message: str) -> WeatherIntent:
    """
    Natural Language Intent Analysis
    ------------------------------
    Processes natural language queries to determine weather data requirements.
    
    Technical Features:
    - Pattern matching for intent detection
    - Location name extraction
    - Time frame analysis
    - Special parameter detection
    
    Args:
        message (str): User's natural language query
        
    Returns:
        WeatherIntent: Structured intent object for API processing
    """
    intent = WeatherIntent()
    message_lower = message.lower()

    # Extract location first
    intent.location = extract_location(message)

    # API Type keywords
    api_keywords = {
        APIType.ARCHIVE: ["historical", "past", "previous", "archive"],
        APIType.MARINE: ["marine", "sea", "ocean", "wave", "shipping"],
        APIType.AIR_QUALITY: ["air quality", "pollution", "aqi", "pm2.5", "pm10"],
        APIType.SNOW: ["snow", "ski", "winter", "freezing"],
        APIType.CLIMATE: ["climate", "long-term", "average", "norm"]
    }

    # Time frame keywords
    hourly_keywords = ["hourly", "hour", "today", "now", "current"]
    historical_keywords = ["historical", "past", "previous", "last month", "last year"]

    # Determine API type
    for api_type, keywords in api_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            intent.api_type = api_type
            break

    # Determine time frame
    if any(keyword in message_lower for keyword in hourly_keywords):
        intent.time_frame = TimeFrame.HOURLY
    elif any(keyword in message_lower for keyword in historical_keywords):
        intent.time_frame = TimeFrame.HISTORICAL
        # Set default historical range (last 30 days)
        intent.end_date = datetime.now().strftime("%Y-%m-%d")
        intent.start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    return intent

class APIParameters:
    @staticmethod
    def get_base_params(lat: float, lon: float) -> Dict:
        return {
            "latitude": lat,
            "longitude": lon,
            "timezone": "auto"
        }

    @staticmethod
    def get_forecast_params(time_frame: TimeFrame) -> Dict:
        params = {
            "hourly": [
                "shortwave_radiation",
                "direct_radiation",
                "diffuse_radiation",
                "temperature_2m",
                "cloudcover",
                "uv_index",
                "windspeed_10m"
            ],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "sunrise",
                "sunset",
                "uv_index_max",
                "shortwave_radiation_sum"
            ]
        }
        
        # Return the parameters as a list instead of a comma-separated string
        if time_frame == TimeFrame.HOURLY:
            return {"hourly": params["hourly"]}
        else:
            return {"daily": params["daily"]}

    @staticmethod
    def get_archive_params(start_date: str, end_date: str) -> Dict:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "hourly": [
                "temperature_2m",
                "shortwave_radiation",
                "direct_radiation",
                "diffuse_radiation"
            ]
        }

    @staticmethod
    def get_marine_params() -> Dict:
        return {
            "hourly": [
                "wave_height",
                "wave_direction",
                "wave_period",
                "wind_wave_height",
                "wind_wave_direction",
                "wind_wave_period",
                "swell_wave_height",
                "swell_wave_direction",
                "swell_wave_period"
            ]
        }

    @staticmethod
    def get_air_quality_params() -> Dict:
        return {
            "hourly": [
                "pm10",
                "pm2_5",
                "carbon_monoxide",
                "nitrogen_dioxide",
                "sulphur_dioxide",
                "ozone",
                "aerosol_optical_depth",
                "dust",
                "uv_index",
                "european_aqi"
            ]
        }

    @staticmethod
    def get_snow_params() -> Dict:
        return {
            "hourly": [
                "snowfall",
                "snow_depth",
                "snow_height",
                "freezing_level_height",
                "snow_melt"
            ],
            "daily": [
                "snowfall_sum",
                "snow_depth_max"
            ]
        }

    @staticmethod
    def get_climate_params(start_year: str = "1990", end_year: str = "2020") -> Dict:
        return {
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "models": ["ERA5", "CMIP6"],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "shortwave_radiation_sum"
            ]
        }

class APIEndpoints:
    BASE_URLS = {
        APIType.FORECAST: "https://api.open-meteo.com/v1/forecast",
        APIType.ARCHIVE: "https://archive-api.open-meteo.com/v1/archive",
        APIType.MARINE: "https://marine-api.open-meteo.com/v1/marine",
        APIType.AIR_QUALITY: "https://air-quality-api.open-meteo.com/v1/air-quality",
        APIType.SNOW: "https://snow-api.open-meteo.com/v1/snow",
        APIType.CLIMATE: "https://climate-api.open-meteo.com/v1/climate"
    } 