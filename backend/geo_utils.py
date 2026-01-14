from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Initialize the free geolocator
# IMPORTANT: You must provide a unique user_agent string
geolocator = Nominatim(user_agent="road_condition_monitor_v1")

def get_location_details(lat, lng):
    """
    FREE: Reverse geocodes using OpenStreetMap (Nominatim).
    Returns: (is_in_india, formatted_address, city_name)
    """
    try:
        # 1. Get location data
        location = geolocator.reverse((lat, lng), exactly_one=True, language='en')
        
        if not location:
            return False, "Unknown Location", None

        address = location.raw.get('address', {})
        
        # 2. Check if in India
        country_code = address.get('country_code', '').lower()
        if country_code != 'in':
            return False, "Location is outside India", None

        # 3. Extract City/District for the Authority Name
        # OSM keys vary, so we check multiple fields
        city = address.get('city') or address.get('town') or address.get('village') or address.get('state_district') or "Unknown District"
        
        return True, location.address, city

    except GeocoderTimedOut:
        return False, "Geocoding Service Timed Out", None
    except Exception as e:
        return False, f"Error: {str(e)}", None

def get_municipal_authority(city_name):
    """
    Generates the authority name based on the detected city.
    """
    if not city_name:
        return "Local Municipal Authority"
    return f"Municipal Corporation of {city_name}"