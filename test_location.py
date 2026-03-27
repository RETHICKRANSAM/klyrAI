import geocoder
try:
    g = geocoder.ip('me')
    print(f"Success: {g.city}, {g.latlng}")
except Exception as e:
    print(f"Error: {e}")
