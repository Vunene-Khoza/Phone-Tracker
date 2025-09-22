import os
import phonenumbers
from phonenumbers import geocoder, carrier
import folium
import requests
import pytz
from datetime import datetime
import time

def get_accurate_coordinates(location_name, country_context=""):
    """Get more accurate coordinates by adding context and trying multiple queries"""
    try:
        # Try different query formats for better accuracy
        queries = [
            f"{location_name}, {country_context}",
            f"{location_name} city, {country_context}",
            f"{location_name} center, {country_context}",
            f"{location_name} downtown, {country_context}",
            location_name,
            f"{location_name} city",
        ]
        
        for query in queries:
            if not query or query.strip() == "":
                continue
                
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': query, 
                'format': 'json', 
                'limit': 5,
                'addressdetails': 1
            }
            headers = {'User-Agent': 'PhoneTrackerApp/1.0'}
            
            response = requests.get(url, params=params, headers=headers)
            data = response.json()
            
            if data:
                
                data.sort(key=lambda x: float(x.get('importance', 0)), reverse=True)
                best_result = data[0]
                lat = float(best_result['lat'])
                lng = float(best_result['lon'])
                display_name = best_result.get('display_name', 'Unknown location')
                
               
                if abs(lat) <= 90 and abs(lng) <= 180:
                    return lat, lng, display_name
        
        return None, None, "No accurate location found"
        
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None, f"Error: {str(e)}"

def get_local_time(lat, lng):
    """Get local time based on coordinates"""
    try:
        # Use TimezoneDB API (free) to get timezone from coordinates
        timezone_url = "http://api.timezonedb.com/v2.1/get-time-zone"
        params = {
            'key': '',  # Free key from https://timezonedb.com/api
            'format': 'json',
            'by': 'position',
            'lat': lat,
            'lng': lng
        }
        
        response = requests.get(timezone_url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            timezone_name = data['zoneName']
            local_time = datetime.now(pytz.timezone(timezone_name))
            return local_time.strftime("%Y-%m-%d %I:%M:%S %p"), timezone_name
        else:
            # Fallback: estimate timezone from longitude
            timezone_offset = int(lng / 15)  # Approximate timezone from longitude
            utc_time = datetime.utcnow()
            local_time = utc_time + timedelta(hours=timezone_offset)
            return local_time.strftime("%Y-%m-%d %I:%M:%S %p"), f"UTC{timezone_offset:+d}"
            
    except Exception as e:
        print(f"Time lookup error: {e}")
        # Fallback to current time
        current_time = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        return current_time, "Local time (approximate)"

def get_timezone_from_country(country_name):
    """Get approximate timezone from country name"""
    country_timezones = {
        "united states": "America/New_York",
        "usa": "America/New_York",
        "united kingdom": "Europe/London",
        "uk": "Europe/London",
        "germany": "Europe/Berlin",
        "france": "Europe/Paris",
        "canada": "America/Toronto",
        "australia": "Australia/Sydney",
        "india": "Asia/Kolkata",
        "china": "Asia/Shanghai",
        "brazil": "America/Sao_Paulo",
        "south africa": "Africa/Johannesburg",
        "japan": "Asia/Tokyo",
        "russia": "Europe/Moscow",
        "mexico": "America/Mexico_City",
    }
    
    if country_name:
        country_lower = country_name.lower()
        for country, timezone in country_timezones.items():
            if country in country_lower:
                try:
                    local_time = datetime.now(pytz.timezone(timezone))
                    return local_time.strftime("%Y-%m-%d %I:%M:%S %p"), timezone
                except:
                    continue
    return None, None

def create_detailed_map(lat, lng, phone_location, precise_location, service_provider, local_time, timezone_info):
    """Create a detailed map with multiple visual elements and time information"""
    # Create map with better view
    map_obj = folium.Map(location=[lat, lng], zoom_start=11, tiles='OpenStreetMap')
    
    # Create detailed popup content with time information
    popup_content = f"""
    <div style='max-width: 300px;'>
        <h3 style='color: #d9534f; margin-bottom: 10px;'>Phone Number Location</h3>
        <p><b>General Area:</b> {phone_location}</p>
        <p><b>Precise Location:</b> {precise_location}</p>
        <p><b>Service Provider:</b> {service_provider}</p>
        <p><b>Local Time:</b> {local_time}</p>
        <p><b>Timezone:</b> {timezone_info}</p>
        <hr style='margin: 10px 0;'>
        <small style='color: #666;'>
        Note: Phone number locations show the general service area, 
        not the exact device location. Accuracy is typically within 10-50 km.
        </small>
    </div>
    """
    
    # Main marker for the estimated location
    folium.Marker(
        [lat, lng], 
        popup=popup_content,
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(map_obj)
    
    # Add circle to show approximate area (typical phone number coverage)
    folium.Circle(
        location=[lat, lng],
        radius=8000,  # 8km radius
        color='blue',
        fill=True,
        fillColor='blue',
        fillOpacity=0.2,
        popup="Approximate service coverage area",
        tooltip="This circle shows the general area served by this phone number"
    ).add_to(map_obj)
    
    # Add another circle for visual reference (wider area)
    folium.Circle(
        location=[lat, lng],
        radius=15000,  # 15km radius
        color='green',
        fill=False,
        weight=2,
        popup="Extended service area reference"
    ).add_to(map_obj)
    
    return map_obj

def get_country_center(country_name):
    """Get approximate country center coordinates for fallback"""
    country_centers = {
        "united states": (39.8283, -98.5795),
        "usa": (39.8283, -98.5795),
        "united kingdom": (55.3781, -3.4360),
        "uk": (55.3781, -3.4360),
        "germany": (51.1657, 10.4515),
        "france": (46.6031, 1.8883),
        "canada": (56.1304, -106.3468),
        "australia": (-25.2744, 133.7751),
        "india": (20.5937, 78.9629),
        "china": (35.8617, 104.1954),
        "brazil": (-14.2350, -51.9253),
        "south africa": (-30.5595, 22.9375),
        "japan": (36.2048, 138.2529),
        "russia": (61.5240, 105.3188),
        "mexico": (23.6345, -102.5528),
    }
    
    if country_name:
        country_lower = country_name.lower()
        for country, coords in country_centers.items():
            if country in country_lower:
                return coords
    return None

def main():
    """Main function to track phone number location"""
    print("=== Advanced Phone Number Tracker ===")
    print("=" * 50)

    # Replace with your phone number (include country code)
    number = "+"  

    try:
        # Parse and validate phone number
        print(f"Processing number: {number}")
        parsed_number = phonenumbers.parse(number)
        
        if not phonenumbers.is_valid_number(parsed_number):
            print("ERROR: Invalid phone number format")
            print("Tip: Include country code (e.g., +1 for US, +44 for UK, +27 for South Africa, +61 for Australia)")
            return
        
        # Get basic information
        general_location = geocoder.description_for_number(parsed_number, "en")
        country = geocoder.description_for_number(parsed_number, "en") 
        service_provider = carrier.name_for_number(parsed_number, "en") or "Unknown carrier"
        
        print(f"General Location: {general_location}")
        print(f"Country: {country}")
        print(f"Service Provider: {service_provider}")
        
        if not general_location or general_location == "None":
            print("Could not determine location from phone number")
            return
        
        # Get accurate coordinates
        print("Getting precise coordinates...")
        lat, lng, precise_location = get_accurate_coordinates(general_location, country)
        
        # Get local time information
        local_time = "Unknown"
        timezone_info = "Unknown"
        
        if lat is not None and lng is not None:
            local_time, timezone_info = get_local_time(lat, lng)
        else:
            # Try to get time from country name
            local_time, timezone_info = get_timezone_from_country(country or general_location)
            if local_time is None:
                local_time = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                timezone_info = "Local time (approximate)"
        
        print(f"Local Time: {local_time}")
        print(f"Timezone: {timezone_info}")
        
        # Fallback if coordinates aren't accurate
        if lat is None or lng is None:
            print("Using country-level accuracy as fallback...")
            country_coords = get_country_center(country or general_location)
            if country_coords:
                lat, lng = country_coords
                precise_location = f"Approximate center of {country or general_location}"
                print(f"Country Center: {lat}, {lng}")
            else:
                print("Could not determine any coordinates")
                return
        else:
            print(f"Precise Coordinates: {lat}, {lng}")
            print(f"Precise Location: {precise_location}")
        
        # Create detailed map
        print("Creating detailed map...")
        detailed_map = create_detailed_map(lat, lng, general_location, precise_location, service_provider, local_time, timezone_info)
        
        # Save map
        filename = "phone_location_map.html"
        detailed_map.save(filename)
        
        # Verify and display results
        if os.path.exists(filename):
            abs_path = os.path.abspath(filename)
            file_size = os.path.getsize(filename)
            
            print("=" * 50)
            print("SUCCESS: Map created successfully!")
            print(f"File: {abs_path}")
            print(f"Size: {file_size} bytes")
            print("=" * 50)
            print("\nLocation Information:")
            print(f"   * Phone Number: {number}")
            print(f"   * General Area: {general_location}")
            print(f"   * Country: {country}")
            print(f"   * Service Provider: {service_provider}")
            print(f"   * Coordinates: {lat:.6f}, {lng:.6f}")
            print(f"   * Precise Location: {precise_location}")
            print(f"   * Local Time: {local_time}")
            print(f"   * Timezone: {timezone_info}")
            print("\nAccuracy Note: Phone number locations show the general")
            print("service area, not exact device location.")
            
            # Try to open automatically
            try:
                os.startfile(abs_path)
                print("\nOpening map in your browser...")
            except:
                print(f"\nPlease open this file manually: {filename}")
                
        else:
            print("ERROR: Map file was not created")

    except phonenumbers.NumberParseException:
        print("ERROR: Invalid phone number format")
        print("Tip: Use format like +1234567890 (with country code)")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()