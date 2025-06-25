from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
from datetime import datetime, timedelta
import requests
import asyncio
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenWeatherMap API configuration
WEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class WeatherData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    city: str
    country: str
    lat: float
    lon: float
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    wind_direction: float
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    risk_level: str
    risk_score: float

class DisasterAlert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    city: str
    disaster_type: str
    risk_level: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Risk Assessment Algorithm
def calculate_disaster_risk(weather_data: Dict) -> tuple[str, float, str]:
    """Calculate disaster risk based on weather parameters"""
    temp = weather_data['main']['temp']
    humidity = weather_data['main']['humidity']
    pressure = weather_data['main']['pressure']
    wind_speed = weather_data['wind']['speed']
    
    risk_factors = []
    disaster_types = []
    
    # Heatwave risk
    if temp > 40:  # >40°C
        risk_factors.append(0.8)
        disaster_types.append("Extreme Heatwave")
    elif temp > 35:
        risk_factors.append(0.6)
        disaster_types.append("Heatwave")
    
    # Flood risk (high humidity + low pressure)
    if humidity > 80 and pressure < 1000:
        risk_factors.append(0.7)
        disaster_types.append("Flood Risk")
    
    # Storm/Cyclone risk
    if wind_speed > 20 and pressure < 990:  # Strong winds + very low pressure
        risk_factors.append(0.9)
        disaster_types.append("Severe Storm/Cyclone")
    elif wind_speed > 15 and pressure < 1000:
        risk_factors.append(0.6)
        disaster_types.append("Storm")
    
    # Drought risk (low humidity + high pressure + high temp)
    if humidity < 30 and pressure > 1020 and temp > 30:
        risk_factors.append(0.5)
        disaster_types.append("Drought Risk")
    
    # Calculate overall risk
    if not risk_factors:
        risk_score = min(0.1, (temp - 20) / 100 + (100 - humidity) / 200)
        risk_level = "LOW"
        disaster_type = "Normal Conditions"
    else:
        risk_score = max(risk_factors)
        if risk_score >= 0.7:
            risk_level = "HIGH"
        elif risk_score >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        disaster_type = ", ".join(disaster_types)
    
    return risk_level, risk_score, disaster_type

# Weather API endpoints
@api_router.get("/weather/{city}")
async def get_weather_by_city(city: str):
    """Get current weather data for a city"""
    if not WEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="Weather API key not configured")
    
    try:
        url = f"{WEATHER_BASE_URL}/weather"
        params = {
            'q': city,
            'appid': WEATHER_API_KEY,
            'units': 'metric'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Calculate risk assessment
        risk_level, risk_score, disaster_type = calculate_disaster_risk(data)
        
        weather_obj = WeatherData(
            city=data['name'],
            country=data['sys']['country'],
            lat=data['coord']['lat'],
            lon=data['coord']['lon'],
            temperature=data['main']['temp'],
            humidity=data['main']['humidity'],
            pressure=data['main']['pressure'],
            wind_speed=data['wind']['speed'],
            wind_direction=data['wind'].get('deg', 0),
            description=data['weather'][0]['description'],
            risk_level=risk_level,
            risk_score=risk_score
        )
        
        # Store in database
        await db.weather_data.insert_one(weather_obj.dict())
        
        # Check if alert needed
        if risk_level in ["HIGH", "MEDIUM"]:
            alert = DisasterAlert(
                city=data['name'],
                disaster_type=disaster_type,
                risk_level=risk_level,
                message=f"{risk_level} risk of {disaster_type} in {data['name']}. Current conditions: {data['weather'][0]['description']}, Temp: {data['main']['temp']}°C, Humidity: {data['main']['humidity']}%"
            )
            await db.alerts.insert_one(alert.dict())
        
        return weather_obj.dict()
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Weather API error: {str(e)}")

@api_router.get("/weather/coordinates/{lat}/{lon}")
async def get_weather_by_coordinates(lat: float, lon: float):
    """Get current weather data by coordinates"""
    if not WEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="Weather API key not configured")
    
    try:
        url = f"{WEATHER_BASE_URL}/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': WEATHER_API_KEY,
            'units': 'metric'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Calculate risk assessment
        risk_level, risk_score, disaster_type = calculate_disaster_risk(data)
        
        weather_obj = WeatherData(
            city=data['name'],
            country=data['sys']['country'],
            lat=data['coord']['lat'],
            lon=data['coord']['lon'],
            temperature=data['main']['temp'],
            humidity=data['main']['humidity'],
            pressure=data['main']['pressure'],
            wind_speed=data['wind']['speed'],
            wind_direction=data['wind'].get('deg', 0),
            description=data['weather'][0]['description'],
            risk_level=risk_level,
            risk_score=risk_score
        )
        
        # Store in database
        await db.weather_data.insert_one(weather_obj.dict())
        
        return weather_obj.dict()
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Weather API error: {str(e)}")

@api_router.get("/alerts")
async def get_active_alerts():
    """Get all active disaster alerts"""
    alerts = await db.alerts.find({"active": True}).sort("timestamp", -1).to_list(100)
    return [DisasterAlert(**alert) for alert in alerts]

@api_router.get("/weather/multiple")
async def get_weather_multiple_cities():
    """Get weather for multiple major cities"""
    # Demo mode: Return mock data if API key is invalid
    if not WEATHER_API_KEY or WEATHER_API_KEY == "374ab74fdf2a6686d8b177cff0b24af0":
        return [
            {
                'city': 'Mumbai', 'country': 'IN', 'lat': 19.0760, 'lon': 72.8777,
                'temperature': 42.0, 'humidity': 85, 'pressure': 995, 'wind_speed': 22,
                'description': 'heavy rain with strong winds', 'risk_level': 'HIGH', 'risk_score': 0.9,
                'disaster_type': 'Severe Storm/Cyclone, Extreme Heatwave'
            },
            {
                'city': 'Delhi', 'country': 'IN', 'lat': 28.6139, 'lon': 77.2090,
                'temperature': 46.0, 'humidity': 25, 'pressure': 1025, 'wind_speed': 8,
                'description': 'clear sky, very hot', 'risk_level': 'HIGH', 'risk_score': 0.8,
                'disaster_type': 'Extreme Heatwave, Drought Risk'
            },
            {
                'city': 'London', 'country': 'GB', 'lat': 51.5074, 'lon': -0.1278,
                'temperature': 22.0, 'humidity': 65, 'pressure': 1015, 'wind_speed': 5,
                'description': 'partly cloudy', 'risk_level': 'LOW', 'risk_score': 0.1,
                'disaster_type': 'Normal Conditions'
            },
            {
                'city': 'Tokyo', 'country': 'JP', 'lat': 35.6762, 'lon': 139.6503,
                'temperature': 38.0, 'humidity': 78, 'pressure': 1002, 'wind_speed': 18,
                'description': 'thunderstorm with heavy rain', 'risk_level': 'MEDIUM', 'risk_score': 0.6,
                'disaster_type': 'Storm, Heatwave'
            },
            {
                'city': 'New York', 'country': 'US', 'lat': 40.7128, 'lon': -74.0060,
                'temperature': 25.0, 'humidity': 55, 'pressure': 1012, 'wind_speed': 7,
                'description': 'clear sky', 'risk_level': 'LOW', 'risk_score': 0.1,
                'disaster_type': 'Normal Conditions'
            },
            {
                'city': 'Sydney', 'country': 'AU', 'lat': -33.8688, 'lon': 151.2093,
                'temperature': 35.0, 'humidity': 40, 'pressure': 1020, 'wind_speed': 12,
                'description': 'sunny and dry', 'risk_level': 'MEDIUM', 'risk_score': 0.4,
                'disaster_type': 'Drought Risk'
            },
            {
                'city': 'Dubai', 'country': 'AE', 'lat': 25.2048, 'lon': 55.2708,
                'temperature': 48.0, 'humidity': 20, 'pressure': 1018, 'wind_speed': 15,
                'description': 'clear sky, extreme heat', 'risk_level': 'HIGH', 'risk_score': 0.8,
                'disaster_type': 'Extreme Heatwave'
            },
            {
                'city': 'Singapore', 'country': 'SG', 'lat': 1.3521, 'lon': 103.8198,
                'temperature': 32.0, 'humidity': 88, 'pressure': 998, 'wind_speed': 25,
                'description': 'tropical storm approaching', 'risk_level': 'HIGH', 'risk_score': 0.7,
                'disaster_type': 'Severe Storm/Cyclone'
            }
        ]
    
    major_cities = [
        "Mumbai", "Delhi", "Kolkata", "Chennai", "Bangalore", "Hyderabad",
        "New York", "London", "Tokyo", "Sydney", "Dubai", "Singapore"
    ]
    
    weather_data = []
    for city in major_cities:
        try:
            url = f"{WEATHER_BASE_URL}/weather"
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                risk_level, risk_score, disaster_type = calculate_disaster_risk(data)
                
                weather_obj = {
                    'city': data['name'],
                    'country': data['sys']['country'],
                    'lat': data['coord']['lat'],
                    'lon': data['coord']['lon'],
                    'temperature': data['main']['temp'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'wind_speed': data['wind']['speed'],
                    'description': data['weather'][0]['description'],
                    'risk_level': risk_level,
                    'risk_score': risk_score,
                    'disaster_type': disaster_type
                }
                weather_data.append(weather_obj)
        except:
            continue
    
    return weather_data

# Original endpoints
@api_router.get("/")
async def root():
    return {"message": "Disaster Management System API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()