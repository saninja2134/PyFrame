import requests
import re
import json
import os

CACHE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'overframe_cache.json')

def update_cache():
    print("Fetching sitemap...")
    url = "https://overframe.gg/sitemap.xml"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"Failed to fetch sitemap: {r.status_code}")
            return
        
        content = r.text
        print(f"Sitemap size: {len(content)} bytes")
        
        # Regex to find all Arsenal item URLs
        # <loc>https://overframe.gg/items/arsenal/60/volt/</loc>
        pattern = re.compile(r'https://overframe\.gg/items/arsenal/(\d+)/([\w-]+)/')
        matches = pattern.findall(content)
        
        print(f"Found {len(matches)} items.")
        
        cache = {}
        for item_id, slug in matches:
            # Normalize name: "volt-prime" -> "Volt Prime"
            name = slug.replace('-', ' ').title()
            
            # Key by lowercase name for easy search
            key = name.lower()
            
            cache[key] = {
                "id": item_id,
                "slug": slug,
                "name": name,
                "url": f"https://overframe.gg/items/arsenal/{item_id}/{slug}/"
            }
            
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)
            
        print(f"Saved {len(cache)} items to {CACHE_FILE}")
        
    except Exception as e:
        print(f"Error updating cache: {e}")

if __name__ == "__main__":
    update_cache()
