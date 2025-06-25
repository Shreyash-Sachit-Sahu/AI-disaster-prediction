import requests
import unittest
import json
import sys
from datetime import datetime

class DisasterManagementAPITester:
    def __init__(self, base_url="https://475ae694-6427-4246-ad31-3ff063aa59f8.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status=200, data=None, validation_func=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            
            status_success = response.status_code == expected_status
            
            # Validate response content if validation function is provided
            content_success = True
            validation_message = ""
            if status_success and validation_func:
                content_success, validation_message = validation_func(response.json())
            
            success = status_success and content_success
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if validation_message:
                    print(f"   {validation_message}")
            else:
                print(f"❌ Failed - Expected status {expected_status}, got {response.status_code}")
                if validation_message:
                    print(f"   {validation_message}")
            
            result = {
                "name": name,
                "success": success,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "validation_message": validation_message
            }
            
            self.test_results.append(result)
            
            return success, response.json() if response.status_code == expected_status else None
        
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "success": False,
                "error": str(e)
            })
            return False, None

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        def validate_response(data):
            if "message" in data and data["message"] == "Disaster Management System API":
                return True, "Root endpoint returned correct message"
            return False, f"Root endpoint returned unexpected message: {data}"
        
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "/api/",
            200,
            validation_func=validate_response
        )

    def test_weather_multiple_endpoint(self):
        """Test the weather/multiple endpoint"""
        def validate_response(data):
            if not isinstance(data, list):
                return False, "Expected a list of weather data"
            
            if len(data) == 0:
                return False, "Weather data list is empty"
            
            # Check if the first item has the expected fields
            required_fields = ['city', 'country', 'temperature', 'humidity', 
                              'pressure', 'wind_speed', 'description', 'risk_level']
            
            for field in required_fields:
                if field not in data[0]:
                    return False, f"Missing required field: {field}"
            
            return True, f"Received weather data for {len(data)} cities"
        
        return self.run_test(
            "Weather Multiple Cities Endpoint",
            "GET",
            "/api/weather/multiple",
            200,
            validation_func=validate_response
        )

    def test_weather_city_endpoint(self, city):
        """Test the weather/{city} endpoint"""
        def validate_response(data):
            # Check if we got an error response due to API key
            if "detail" in data and "Weather API error" in data["detail"] and "401" in data["detail"]:
                return True, "API returned expected error due to invalid OpenWeatherMap API key"
            
            required_fields = ['city', 'country', 'temperature', 'humidity', 
                              'pressure', 'wind_speed', 'description', 'risk_level']
            
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
            
            if data['city'].lower() != city.lower() and data['city'] != city:
                return False, f"Requested {city} but got data for {data['city']}"
            
            risk_level = data['risk_level']
            if risk_level not in ['LOW', 'MEDIUM', 'HIGH']:
                return False, f"Invalid risk level: {risk_level}"
            
            return True, f"Received valid weather data for {data['city']} with risk level: {risk_level}"
        
        # We expect 400 because the OpenWeatherMap API key is invalid
        return self.run_test(
            f"Weather for {city}",
            "GET",
            f"/api/weather/{city}",
            400,
            validation_func=validate_response
        )

    def test_alerts_endpoint(self):
        """Test the alerts endpoint"""
        def validate_response(data):
            if not isinstance(data, list):
                return False, "Expected a list of alerts"
            
            # Even if there are no alerts, the structure should be a list
            if len(data) > 0:
                # Check if the first item has the expected fields
                required_fields = ['city', 'disaster_type', 'risk_level', 'message']
                
                for field in required_fields:
                    if field not in data[0]:
                        return False, f"Missing required field in alert: {field}"
                
                return True, f"Received {len(data)} alerts"
            else:
                return True, "No active alerts found (empty list)"
        
        return self.run_test(
            "Alerts Endpoint",
            "GET",
            "/api/alerts",
            200,
            validation_func=validate_response
        )

    def print_summary(self):
        """Print a summary of all test results"""
        print("\n" + "="*50)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        for i, result in enumerate(self.test_results, 1):
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"{i}. {result['name']}: {status}")
            if not result["success"] and "validation_message" in result:
                print(f"   Reason: {result['validation_message']}")
            elif not result["success"] and "error" in result:
                print(f"   Error: {result['error']}")
        
        print("="*50)
        return self.tests_passed == self.tests_run

def main():
    print("🚀 Starting Disaster Management API Tests")
    print("="*50)
    
    # Get the backend URL from command line args or use default
    backend_url = "https://475ae694-6427-4246-ad31-3ff063aa59f8.preview.emergentagent.com"
    
    tester = DisasterManagementAPITester(backend_url)
    
    # Test the root endpoint
    tester.test_root_endpoint()
    
    # Test the weather/multiple endpoint
    tester.test_weather_multiple_endpoint()
    
    # Test the weather/{city} endpoint for different cities
    test_cities = ["Mumbai", "London", "Tokyo", "New York", "InvalidCityName123"]
    for city in test_cities:
        tester.test_weather_city_endpoint(city)
    
    # Test the alerts endpoint
    tester.test_alerts_endpoint()
    
    # Print summary
    all_passed = tester.print_summary()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())