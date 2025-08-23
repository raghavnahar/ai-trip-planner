import json
import hashlib
import os
from datetime import datetime, timedelta

CACHE_DIR = "data/cache"
CACHE_DURATION = timedelta(hours=24)  # Cache for 24 hours

def ensure_cache_dir():
    """Ensure the cache directory exists"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_key(user_input):
    """Generate a unique cache key from user input"""
    input_str = json.dumps(user_input, sort_keys=True, default=str)
    return hashlib.md5(input_str.encode()).hexdigest()

def cache_itinerary(cache_key, itinerary):
    """Cache an itinerary with expiration"""
    ensure_cache_dir()
    
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    cache_data = {
        "itinerary": itinerary,
        "expires": (datetime.now() + CACHE_DURATION).isoformat()
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f)

def get_cached_itinerary(cache_key):
    """Retrieve a cached itinerary if it exists and hasn't expired"""
    ensure_cache_dir()
    
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache has expired
        expires = datetime.fromisoformat(cache_data["expires"])
        if datetime.now() > expires:
            # Cache expired, delete it
            os.remove(cache_file)
            return None
        
        return cache_data["itinerary"]
    except (json.JSONDecodeError, KeyError, ValueError):
        # Invalid cache file, delete it
        os.remove(cache_file)
        return None

def clear_expired_cache():
    """Clear all expired cache files"""
    ensure_cache_dir()
    
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith('.json'):
            cache_file = os.path.join(CACHE_DIR, filename)
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                expires = datetime.fromisoformat(cache_data["expires"])
                if datetime.now() > expires:
                    os.remove(cache_file)
            except (json.JSONDecodeError, KeyError, ValueError):
                # Invalid cache file, delete it
                os.remove(cache_file)