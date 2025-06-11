"""
Solar Forecast AI - Main Backend Service
======================================

System Design & Architecture:
----------------------------
This application implements an innovative AI-powered solar forecasting system that combines:
1. Natural Language Processing for intent understanding
2. Multiple weather data sources for comprehensive analysis
3. AI-driven response generation for human-like interactions

Key Components:
- Intent Analysis: Uses GPT-4 to understand complex weather queries
- Location Processing: Geocoding with error handling
- Multi-API Integration: Combines data from various weather services
- Response Generation: AI-powered, context-aware responses

Technical Implementation:
------------------------
- FastAPI backend for high-performance async operations
- OpenAI GPT-4 integration for NLP tasks
- Multiple weather API integrations (Open-Meteo, Marine, Air Quality)
- Robust error handling and logging system

Author: [Your Name]
Version: 1.0.0
"""

# ------------------------
# STEP 1: SETUP BACKEND
# ------------------------

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import requests
import json
import os
from dotenv import load_dotenv
import time
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import traceback
import logging

from api_types import (
    APIType, TimeFrame, WeatherIntent, 
    analyze_weather_intent, APIParameters, APIEndpoints
)

# Configure logging for debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Validate environment configuration
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

app = FastAPI()
client = OpenAI(api_key=api_key)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint to verify API status"""
    return {"status": "healthy", "message": "Solar Forecast AI API is running"}

# Function to check content moderation
async def check_moderation(text):
    try:
        response = client.moderations.create(input=text)
        result = response.results[0]
        
        # Convert the moderation result to a dictionary
        categories_dict = {}
        for category in result.categories.__dict__:
            if not category.startswith('_'):  # Skip private attributes
                categories_dict[category] = getattr(result.categories, category)
        
        return {
            "flagged": result.flagged,
            "categories": categories_dict
        }
    except Exception as e:
        print(f"Detailed moderation error: {type(e).__name__}, {str(e)}")
        # Return false instead of raising an error to allow the request to proceed
        return {"flagged": False, "categories": {}}

# Function to get lat/lon from city name using Nominatim
def get_lat_lon(city):
    try:
        # Add delay to respect Nominatim's usage policy
        time.sleep(1)
        
        headers = {
            'User-Agent': 'SolarForecastApp/1.0',
            'Accept': 'application/json'
        }
        
        url = f"https://nominatim.openstreetmap.org/search"
        params = {
            'q': city,
            'format': 'json',
            'limit': 1
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            return None, None
            
        return float(data[0]["lat"]), float(data[0]["lon"])
    except requests.exceptions.RequestException as e:
        print(f"Error in get_lat_lon: {str(e)}")
        return None, None
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error parsing location data: {str(e)}")
        return None, None

# Function to get solar irradiance forecast from Open-Meteo
def get_solar_forecast(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': lat,
            'longitude': lon,
            'hourly': 'shortwave_radiation',
            'forecast_days': 3
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error in get_solar_forecast: {str(e)}")
        return None

class ChatRequest(BaseModel):
    message: str

class Location:
    def __init__(self, city: str, lat: float, lon: float):
        self.city = city
        self.coordinates = {"lat": lat, "lon": lon}

    def to_dict(self):
        return {
            "city": self.city,
            "coordinates": self.coordinates
        }

async def get_location_coordinates(location_query: str) -> Location:
    """
    Geocoding Service Integration
    ----------------------------
    Converts location names to coordinates using OpenStreetMap's Nominatim service.
    
    Features:
    - Robust error handling for location queries
    - Rate limiting compliance
    - Validation of coordinate data
    
    Args:
        location_query (str): User-provided location name
        
    Returns:
        Dict: Location data including coordinates and metadata
    """
    logger.info(f"Fetching coordinates for location: {location_query}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": location_query,
                    "format": "json",
                    "limit": 1
                },
                headers={"User-Agent": "WeatherApp/1.0"}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get location data. Status code: {response.status_code}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to get location data. Status: {response.status_code}"
                )
            
            data = response.json()
            if not data:
                logger.warning(f"Location not found: {location_query}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Location '{location_query}' not found"
                )
            
            location = Location(
                city=data[0]["display_name"].split(",")[0],
                lat=float(data[0]["lat"]),
                lon=float(data[0]["lon"])
            )
            logger.info(f"Location found: {location.city} ({location.coordinates})")
            return location
    except httpx.RequestError as e:
        logger.error(f"Request error while fetching location: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to location service: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_location_coordinates: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing location request: {str(e)}"
        )

async def fetch_weather_data(intent: WeatherIntent, location: Location) -> Dict:
    """
    Multi-Source Weather Data Integration
    -----------------------------------
    Fetches and combines weather data from multiple APIs based on user intent.
    
    Technical Features:
    - Async HTTP requests for improved performance
    - Dynamic API selection based on intent
    - Comprehensive error handling
    - Data validation and normalization
    
    Args:
        intent (WeatherIntent): Analyzed user intent
        location (Location): Processed location data
        
    Returns:
        Dict: Normalized weather data from selected APIs
    """
    logger.info(f"Fetching {intent.api_type.value} data for {location.city}")
    try:
        async with httpx.AsyncClient() as client:
            # Get base parameters
            params = APIParameters.get_base_params(
                location.coordinates["lat"],
                location.coordinates["lon"]
            )
            
            # Add API-specific parameters
            if intent.api_type == APIType.FORECAST:
                forecast_params = APIParameters.get_forecast_params(intent.time_frame)
                params.update(forecast_params)
                logger.debug(f"Forecast parameters: {forecast_params}")
            elif intent.api_type == APIType.ARCHIVE:
                if not (intent.start_date and intent.end_date):
                    intent.end_date = datetime.now().strftime("%Y-%m-%d")
                    intent.start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                params.update(APIParameters.get_archive_params(intent.start_date, intent.end_date))
            elif intent.api_type == APIType.MARINE:
                marine_params = APIParameters.get_marine_params()
                params.update(marine_params)
            elif intent.api_type == APIType.AIR_QUALITY:
                air_quality_params = APIParameters.get_air_quality_params()
                params.update(air_quality_params)
            elif intent.api_type == APIType.SNOW:
                snow_params = APIParameters.get_snow_params()
                params.update(snow_params)
            elif intent.api_type == APIType.CLIMATE:
                climate_params = APIParameters.get_climate_params()
                params.update(climate_params)

            logger.debug(f"API request params: {params}")
            api_url = APIEndpoints.BASE_URLS[intent.api_type]
            logger.info(f"Making request to {api_url} with params: {params}")
            
            # Add common parameters for all requests
            params.update({
                "timezone": "auto",
                "format": "json"
            })
            
            response = await client.get(api_url, params=params)
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    if isinstance(error_json, dict):
                        error_detail = error_json.get('reason', error_json.get('error', response.text))
                except:
                    pass
                
                logger.error(f"API error: {response.status_code} - {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Weather service error: {error_detail}"
                )
            
            data = response.json()
            logger.info(f"Successfully fetched {intent.api_type.value} data")
            
            # Add metadata to response
            data.update({
                "request_type": intent.api_type.value,
                "location": location.city,
                "coordinates": location.coordinates
            })
            
            return data

    except httpx.RequestError as e:
        logger.error(f"Request error while fetching weather data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to weather service: {str(e)}"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in fetch_weather_data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching weather data: {str(e)}"
        )

def get_gpt_function_def(intent: WeatherIntent) -> Dict:
    """Get the appropriate GPT function definition based on intent."""
    base_properties = {
        "summary": {
            "type": "string",
            "description": "Overall analysis and key findings"
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "advice": {"type": "string"}
                }
            }
        }
    }

    if intent.api_type == APIType.FORECAST:
        if intent.time_frame == TimeFrame.HOURLY:
            return {
                "name": "analyze_hourly_forecast",
                "description": "Analyze hourly weather forecast data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        **base_properties,
                        "hourly_forecast": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "hour": {"type": "string"},
                                    "conditions": {"type": "string"},
                                    "solar_potential": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["summary", "hourly_forecast", "recommendations"]
                }
            }
        else:
            return {
                "name": "analyze_daily_forecast",
                "description": "Analyze daily weather forecast data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        **base_properties,
                        "daily_forecast": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string"},
                                    "conditions": {"type": "string"},
                                    "solar_potential": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["summary", "daily_forecast", "recommendations"]
                }
            }
    elif intent.api_type == APIType.MARINE:
        return {
            "name": "analyze_marine_conditions",
            "description": "Analyze marine weather conditions",
            "parameters": {
                "type": "object",
                "properties": {
                    **base_properties,
                    "wave_conditions": {
                        "type": "object",
                        "properties": {
                            "wave_height": {"type": "string"},
                            "wave_direction": {"type": "string"},
                            "sea_temperature": {"type": "string"}
                        }
                    }
                },
                "required": ["summary", "wave_conditions", "recommendations"]
            }
        }
    elif intent.api_type == APIType.AIR_QUALITY:
        return {
            "name": "analyze_air_quality",
            "description": "Analyze air quality data",
            "parameters": {
                "type": "object",
                "properties": {
                    **base_properties,
                    "air_quality_metrics": {
                        "type": "object",
                        "properties": {
                            "aqi_level": {"type": "string"},
                            "pollutants": {"type": "string"},
                            "health_implications": {"type": "string"}
                        }
                    }
                },
                "required": ["summary", "air_quality_metrics", "recommendations"]
            }
        }
    # Add more function definitions for other API types...

def format_response_with_gpt(weather_data: Dict, location: Location, intent: WeatherIntent) -> Dict:
    """Format weather data using GPT based on intent type."""
    logger.info(f"Formatting response with GPT for {intent.api_type.value} data")
    try:
        # Get appropriate function definition
        function_def = get_gpt_function_def(intent)
        if not function_def:
            logger.error(f"No function definition found for intent type: {intent.api_type.value}")
            raise ValueError(f"Unsupported API type: {intent.api_type.value}")
        
        # Create system message based on intent
        system_message = f"You are a weather expert providing analysis of {intent.api_type.value} data. "
        system_message += "Focus on practical insights and clear explanations."

        # Optimize the weather data before sending to GPT
        optimized_data = {}
        if intent.api_type == APIType.MARINE:
            # Only include the first 24 hours of data for hourly forecasts
            if 'hourly' in weather_data:
                optimized_data['hourly'] = {
                    key: value[:24] for key, value in weather_data['hourly'].items()
                }
            # Keep other important metadata
            for key in ['latitude', 'longitude', 'timezone', 'timezone_abbreviation']:
                if key in weather_data:
                    optimized_data[key] = weather_data[key]
        else:
            optimized_data = weather_data

        # Create user message with optimized data
        user_message = f"Analyze this {intent.api_type.value} data for {location.city}:\n"
        user_message += json.dumps(optimized_data, indent=2)

        # Get GPT's analysis using GPT-4 Turbo
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",  # GPT-4 Turbo with 128k context
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            functions=[function_def],
            function_call={"name": function_def["name"]},
            max_tokens=4000  # Maximum allowed completion tokens for this model
        )

        # Parse the function call response
        result = json.loads(response.choices[0].message.function_call.arguments)
        
        # Add common fields
        result.update({
            "raw_data": weather_data,  # Keep the full data in response
            "location": location.to_dict(),
            "query_type": intent.api_type.value,
            "time_frame": intent.time_frame.value
        })
        
        logger.info("Successfully formatted response with GPT")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in GPT response: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to parse GPT response"
        )
    except Exception as e:
        logger.error(f"Error in format_response_with_gpt: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error formatting response: {str(e)}"
        )

@app.post("/chat/")
async def chat_endpoint(request: ChatRequest):
    """Handle chat requests and return weather data."""
    try:
        logger.info(f"Received chat request: {request.message}")

        # Check content moderation
        moderation_result = await check_moderation(request.message)
        if moderation_result["flagged"]:
            logger.warning(f"Content moderation flagged: {moderation_result['categories']}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Content flagged by moderation",
                    "details": f"The following categories were flagged: {', '.join(moderation_result['categories'].keys())}"
                }
            )

        # Analyze user intent
        intent = analyze_weather_intent(request.message)
        logger.info(f"Analyzed intent: {intent.api_type.value}, {intent.time_frame.value}")
        
        # If no location was found in the message
        if not intent.location:
            logger.info("No location found in message")
            return {
                "type": "location_request",
                "message": "I couldn't determine the location. Please specify a city or place for the weather forecast. For example: 'weather forecast for London' or 'air quality in Paris'."
            }

        # Extract location from message
        try:
            location = await get_location_coordinates(intent.location)
            logger.info(f"Location found: {location.city}")
        except HTTPException as e:
            if e.status_code == 404:
                logger.warning(f"Location not found: {intent.location}")
                return {
                    "type": "location_request",
                    "message": f"I couldn't find the location '{intent.location}'. Please check the spelling or try a different city."
                }
            raise e

        # Fetch weather data based on intent
        weather_data = await fetch_weather_data(intent, location)
        
        # Format response with GPT
        formatted_response = format_response_with_gpt(weather_data, location, intent)
        
        logger.info("Successfully processed chat request")
        return formatted_response

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "An error occurred while processing your request",
                "details": str(e)
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)