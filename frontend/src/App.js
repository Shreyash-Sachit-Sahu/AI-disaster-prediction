import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Weather Icons Component
const WeatherIcon = ({ description, riskLevel }) => {
  const getIcon = () => {
    if (description.includes('rain') || description.includes('drizzle')) return '🌧️';
    if (description.includes('cloud')) return '☁️';
    if (description.includes('clear')) return '☀️';
    if (description.includes('storm')) return '⛈️';
    if (description.includes('snow')) return '❄️';
    return '🌤️';
  };

  const getRiskColor = () => {
    switch (riskLevel) {
      case 'HIGH': return 'text-red-500';
      case 'MEDIUM': return 'text-yellow-500';
      case 'LOW': return 'text-green-500';
      default: return 'text-gray-500';
    }
  };

  return (
    <div className="flex items-center space-x-2">
      <span className="text-3xl">{getIcon()}</span>
      <span className={`font-bold ${getRiskColor()}`}>{riskLevel}</span>
    </div>
  );
};

// Weather Card Component
const WeatherCard = ({ weather }) => {
  const getRiskBorderColor = () => {
    switch (weather.risk_level) {
      case 'HIGH': return 'border-red-500 bg-red-50';
      case 'MEDIUM': return 'border-yellow-500 bg-yellow-50';
      case 'LOW': return 'border-green-500 bg-green-50';
      default: return 'border-gray-300 bg-white';
    }
  };

  return (
    <div className={`border-2 rounded-lg p-4 ${getRiskBorderColor()} shadow-lg hover:shadow-xl transition-shadow`}>
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="text-lg font-bold text-gray-800">{weather.city}</h3>
          <p className="text-sm text-gray-600">{weather.country}</p>
        </div>
        <WeatherIcon description={weather.description} riskLevel={weather.risk_level} />
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="font-semibold">Temperature:</span>
          <span className="ml-1">{weather.temperature}°C</span>
        </div>
        <div>
          <span className="font-semibold">Humidity:</span>
          <span className="ml-1">{weather.humidity}%</span>
        </div>
        <div>
          <span className="font-semibold">Pressure:</span>
          <span className="ml-1">{weather.pressure} hPa</span>
        </div>
        <div>
          <span className="font-semibold">Wind:</span>
          <span className="ml-1">{weather.wind_speed} m/s</span>
        </div>
      </div>
      
      <div className="mt-3 pt-3 border-t border-gray-200">
        <p className="text-sm text-gray-700 capitalize">{weather.description}</p>
        {weather.disaster_type && weather.disaster_type !== 'Normal Conditions' && (
          <p className="text-sm font-semibold text-red-600 mt-1">
            ⚠️ {weather.disaster_type}
          </p>
        )}
      </div>
    </div>
  );
};

// Alert Component
const AlertBanner = ({ alerts }) => {
  if (!alerts || alerts.length === 0) return null;

  const highRiskAlerts = alerts.filter(alert => alert.risk_level === 'HIGH');
  
  if (highRiskAlerts.length === 0) return null;

  return (
    <div className="bg-red-600 text-white p-4 mb-6 rounded-lg shadow-lg">
      <div className="flex items-center space-x-2 mb-2">
        <span className="text-2xl">🚨</span>
        <h2 className="text-xl font-bold">HIGH RISK ALERTS</h2>
      </div>
      {highRiskAlerts.slice(0, 3).map((alert, index) => (
        <div key={index} className="mb-2 last:mb-0">
          <p className="font-semibold">{alert.city}: {alert.disaster_type}</p>
          <p className="text-sm opacity-90">{alert.message}</p>
        </div>
      ))}
    </div>
  );
};

// Search Component
const CitySearch = ({ onSearch, loading }) => {
  const [city, setCity] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (city.trim()) {
      onSearch(city.trim());
      setCity('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mb-6">
      <div className="flex space-x-2">
        <input
          type="text"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="Enter city name (e.g., Mumbai, London, Tokyo)"
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
    </form>
  );
};

// Main App Component
function App() {
  const [weatherData, setWeatherData] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load multiple cities data on component mount
  const loadMultipleCities = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${API}/weather/multiple`);
      setWeatherData(response.data);
    } catch (e) {
      console.error('Error loading weather data:', e);
      setError('Failed to load weather data. Please check if the OpenWeatherMap API key is configured.');
    } finally {
      setLoading(false);
    }
  };

  // Load alerts
  const loadAlerts = async () => {
    try {
      const response = await axios.get(`${API}/alerts`);
      setAlerts(response.data);
    } catch (e) {
      console.error('Error loading alerts:', e);
    }
  };

  // Search for specific city
  const searchCity = async (cityName) => {
    try {
      setSearchLoading(true);
      setError(null);
      const response = await axios.get(`${API}/weather/${encodeURIComponent(cityName)}`);
      
      // Add the new city data to the existing data, or replace if it already exists
      setWeatherData(prevData => {
        const filtered = prevData.filter(item => item.city.toLowerCase() !== response.data.city.toLowerCase());
        return [response.data, ...filtered];
      });
      
      // Refresh alerts
      loadAlerts();
    } catch (e) {
      console.error('Error searching city:', e);
      if (e.response?.status === 404 || e.response?.data?.detail?.includes('city not found')) {
        setError(`City "${cityName}" not found. Please check the spelling and try again.`);
      } else {
        setError('Failed to fetch weather data for the city. Please try again.');
      }
    } finally {
      setSearchLoading(false);
    }
  };

  useEffect(() => {
    loadMultipleCities();
    loadAlerts();
    
    // Auto-refresh every 5 minutes
    const interval = setInterval(() => {
      loadMultipleCities();
      loadAlerts();
    }, 300000);
    
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-xl text-gray-600">Loading disaster management system...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            🌍 AI Disaster Management System
          </h1>
          <p className="text-lg text-gray-600">
            Real-time weather monitoring with AI-powered risk assessment
          </p>
          <div className="mt-2 text-sm text-gray-500">
            Last updated: {new Date().toLocaleString()}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            <p>{error}</p>
          </div>
        )}

        {/* Alerts */}
        <AlertBanner alerts={alerts} />

        {/* Search */}
        <CitySearch onSearch={searchCity} loading={searchLoading} />

        {/* Risk Level Legend */}
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <h3 className="text-lg font-semibold mb-3">Risk Level Guide:</h3>
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span className="text-sm">LOW - Normal conditions</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-yellow-500 rounded"></div>
              <span className="text-sm">MEDIUM - Monitor conditions</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span className="text-sm">HIGH - Take precautions</span>
            </div>
          </div>
        </div>

        {/* Weather Cards Grid */}
        {weatherData.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {weatherData.map((weather, index) => (
              <WeatherCard key={`${weather.city}-${index}`} weather={weather} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-xl text-gray-600 mb-4">No weather data available</p>
            <p className="text-gray-500">Try searching for a specific city above</p>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-12 text-gray-500 text-sm">
          <p>Powered by OpenWeatherMap API • Built with AI for disaster preparedness</p>
        </div>
      </div>
    </div>
  );
}

export default App;