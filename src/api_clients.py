import requests
from bs4 import BeautifulSoup
import json
import os
import re

# Load Overframe Cache
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'overframe_cache.json')
OVERFRAME_CACHE = {}
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            OVERFRAME_CACHE = json.load(f)
    except:
        print("Failed to load Overframe cache.")

class OverframeClient:
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    @staticmethod
    def get_item_url(item_name):
        key = item_name.lower().strip()
        # Direct match
        if key in OVERFRAME_CACHE:
            return OVERFRAME_CACHE[key]['url']
        
        # Fuzzy match (contains)
        for k, v in OVERFRAME_CACHE.items():
            if key in k or k in key:
                return v['url']
        return None

    @staticmethod
    def get_top_build(item_name):
        item_url = OverframeClient.get_item_url(item_name)
        if not item_url:
            return None, "Item not found in Overframe cache."

        try:
            # 1. Fetch Item Page
            resp = requests.get(item_url, headers=OverframeClient.HEADERS)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # 2. Find Top Build Link
            # Look for links starting with /build/
            # They are usually sorted by rating by default.
            build_links = []
            for a in soup.find_all('a', href=True):
                if a['href'].startswith('/build/') and '/new/' not in a['href']:
                    build_links.append(a['href'])
            
            if not build_links:
                return None, "No builds found."

            # Take the first one (usually the top rated one in the list)
            top_build_path = build_links[0]
            top_build_url = f"https://overframe.gg{top_build_path}"
            
            # 3. Fetch Build Page
            resp = requests.get(top_build_url, headers=OverframeClient.HEADERS)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # 4. Extract Mods & Stats
            mods = []
            arcanes = []
            stats = []

            # 4a. Mods (Pattern: div class*=Mod_container__ -> p class*=Mod_name__)
            # Capturing metadata for improved display
            mod_containers = soup.find_all('div', class_=re.compile(r'Mod_container__'))
            for mc in mod_containers:
                mod_data = {'name': 'Unknown', 'cost': '', 'polarity': '', 'rarity': 'common'}
                
                # Name
                name_tag = mc.find(class_=re.compile(r'Mod_name__'))
                if name_tag:
                    mod_data['name'] = name_tag.get_text(strip=True)
                
                # Image
                img_tag = mc.find('img')
                if img_tag:
                    mod_data['image_url'] = img_tag.get('src')
                
                # Drain
                drain_tag = mc.find(class_=re.compile(r'Mod_drain__'))
                if drain_tag:
                    mod_data['cost'] = drain_tag.get_text(strip=True)
                
                # Polarity (icon class usually)
                # Look for <i class="wfic ...">
                polarity_icon = mc.find('i', class_=re.compile(r'Mod_polarity__'))
                if polarity_icon:
                    classes = polarity_icon.get('class', [])
                    for c in classes:
                        if c.startswith('wfic-AP_'):
                            mod_data['polarity'] = c.replace('wfic-AP_', '').title()
                
                # Rarity (from container class)
                # Mod_rare__McUwv, Mod_common__..., Mod_uncommon__..., Mod_legendary__...
                container_classes = mc.find('div', class_=re.compile(r'Mod_mod__'))
                if container_classes:
                    c_classes = container_classes.get('class', [])
                    for c in c_classes:
                        if 'rare' in c: mod_data['rarity'] = 'gold'
                        elif 'common' in c: mod_data['rarity'] = 'brown' # Bronzeish
                        elif 'uncommon' in c: mod_data['rarity'] = 'silver'
                        elif 'legendary' in c: mod_data['rarity'] = 'white' # Primed
                        elif 'requiem' in c: mod_data['rarity'] = 'red'

                if mod_data['name'] != 'Unknown':
                    mods.append(mod_data)
            
            # 4b. Arcanes
            arcane_containers = soup.find_all('div', class_=re.compile(r'ArcaneMod_arcaneMod__'))
            for ac in arcane_containers:
                name_tag = ac.find(class_=re.compile(r'ArcaneMod_name__'))
                if name_tag:
                    # Try to detect rarity too
                    rarity = 'silver'
                    classes = ac.get('class', [])
                    for c in classes:
                         if 'rare' in c: rarity = 'gold'
                         elif 'legendary' in c: rarity = 'white'
                    
                    arcanes.append({'name': name_tag.get_text(strip=True), 'rarity': rarity})

            # 4c. Stats
            stat_containers = soup.find_all('div', class_=re.compile(r'TitleStat_titleStat__'))
            for sc in stat_containers:
                label = sc.find('dt')
                value = sc.find('dd')
                if label and value:
                    stats.append((label.get_text(strip=True), value.get_text(strip=True)))

            # Deduplicate preserving order
            seen = set()
            unique_mods = []
            for m in mods:
                if m['name'] not in seen:
                    unique_mods.append(m)
                    seen.add(m['name'])
            
            # Use improved mod list
            filtered_mods = unique_mods[:10] # Standard build size

            return top_build_url, {
                'mods': filtered_mods,
                'arcanes': arcanes,
                'stats': stats
            }

        except Exception as e:
            return None, str(e)

class WarframeAPI:
    WORLD_STATE_URL = "https://api.warframestat.us/pc"
    MARKET_BASE_URL = "https://api.warframe.market/v1"

    @staticmethod
    def get_world_state():
        try:
            # We use the 'en' locale for consistent naming
            # Disable verify to fix common SSL cert issues on some windows machines with this specific API
            # Add Cache-Control to prevent stale data
            # Add timestamp to force fresh fetch
            import time
            headers = {'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}
            response = requests.get(f"{WarframeAPI.WORLD_STATE_URL}/?language=en&_={int(time.time())}", verify=False, headers=headers)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error fetching world state: {e}")
            return None

    @staticmethod
    def process_invasions(invasions):
        # Filter mostly for "good" rewards: Potatoes, Forma, Wraith/Vandal parts
        interesting = []
        for inv in invasions:
            if inv.get('completed', False): continue
            
            rewards = []
            for side in ['attacker', 'defender']:
                reward = inv.get(f'{side}Reward', {}).get('asString', '')
                if any(x in reward.lower() for x in ['catalyst', 'reactor', 'forma', 'vandal', 'wraith', 'mutagen mass', 'fieldron', 'detonite', 'exilus', 'adapter']):
                    rewards.append(f"{reward} ({inv.get('node', 'Unknown')})")
            
            if rewards:
                interesting.extend(rewards)
        return interesting

    @staticmethod
    def process_void_trader(void_trader):
        if not void_trader: return "Unknown"
        if void_trader.get('active', False):
            # If active, list inventory
            inventory_str = f"Baro is at {void_trader.get('location', 'Unknown')}!<br>Inventory:<br>"
            for item in void_trader.get('inventory', []):
                item_name = item.get('item', 'Unknown')
                ducats = item.get('ducats', '?')
                credits = item.get('credits', '?')
                inventory_str += f"- {item_name} ({ducats}d + {credits}cr)<br>"
            return inventory_str
        else:
            return f"Baro arrives in {void_trader.get('startString', 'Unknown')} at {void_trader.get('location', 'Unknown')}"

    @staticmethod
    def get_drop_locations(item_name):
        # Try WarframeStat Items API for drop data
        try:
            url = f"https://api.warframestat.us/items/search/{item_name.lower()}"
            resp = requests.get(url)
            if resp.status_code == 200:
                results = resp.json()
                item = next((i for i in results if i.get('name', '').lower() == item_name.lower()), None)
                if not item and results: item = results[0]
                
                if item:
                    # Check for direct drops
                    drops = item.get('drops', [])
                    if drops:
                        drops.sort(key=lambda x: x.get('chance', 0), reverse=True)
                        drop_str = "Drops From:<br>"
                        for d in drops[:5]:
                            chance = d.get('chance', 0) * 100
                            loc = d.get('location', 'Unknown')
                            rarity = d.get('rarity', '')
                            drop_str += f"- {loc} ({rarity}, {chance:.1f}%)<br>"
                        return drop_str
                    
                    # Check for research (Dojo)
                    if 'buildPrice' in item and 'research' in str(item): # Heuristic
                        return "Source: Dojo Research (Tenno Lab likely)"
                        
            return "Drops not listed in API. Check Wiki/Market/Dojo."
        except Exception as e:
            return f"Drop API error: {e}"

    @staticmethod
    def get_market_item_price(item_name):
        # Warframe Market requires headers sometimes to avoid 403
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # Clean name
        clean_name = item_name.lower().strip().replace(" ", "_").replace("'", "")
        
        def fetch_price(url_key, display_name):
            try:
                # Get orders directly
                url = f"{WarframeAPI.MARKET_BASE_URL}/items/{url_key}/orders"
                response = requests.get(url, headers=headers)
                
                if response.status_code == 404:
                    return None
                    
                if response.status_code == 200:
                    orders = response.json().get('payload', {}).get('orders', [])
                    online_orders = [o for o in orders if o['user']['status'] == 'ingame' and o['order_type'] == 'sell']
                    if online_orders:
                        price = min(o['platinum'] for o in online_orders)
                        return f"<b>Market Price:</b> <span style='color:#00ff88; font-size:14px;'>{price}p</span> (Lowest Online)"
                    else:
                        return "<b>Market Price:</b> No players in-game."
                return None
            except:
                return None

        # 1. Try exact name (e.g. "volt_prime_set")
        # Most items are "set" on market if they have parts. Warframes are definitely "sets".
        # But for non-prime, "volt" isn't tradeable.
        
        res = fetch_price(clean_name, item_name)
        if res: return res, item_name
        
        # 2. Try adding "_set"
        res = fetch_price(f"{clean_name}_set", item_name)
        if res: return res, item_name

        # 3. If original was not prime, try finding Prime variant
        if "prime" not in clean_name:
            prime_name_url = f"{clean_name}_prime_set"
            res = fetch_price(prime_name_url, item_name + " Prime")
            if res:
                return f"{res} (Prime Set)", item_name + " Prime"

        return "<b>Market Price:</b> Item not tradeable or not found.", item_name

    @staticmethod
    def get_wiki_info(item_name):
        # Use Parse API to get HTML of the first section
        # https://warframe.fandom.com/api.php?action=parse&page=Volt&prop=text&format=json&section=0
        try:
            # First clean up the name for Wiki URL (Spaces -> Underscores)
            wiki_title = item_name.replace(" ", "_").title()
            
            url = f"https://warframe.fandom.com/api.php?action=parse&page={wiki_title}&prop=text&format=json&section=0&redirects=1"
            headers = {'User-Agent': 'PyFrameOverlay/1.0'}
            resp = requests.get(url, headers=headers)
            
            data = resp.json()
            if 'error' in data:
                return f"Wiki: {data['error'].get('info', 'Page not found')}"
            
            html_content = data.get('parse', {}).get('text', {}).get('*', '')
            
            # Use BeautifulSoup to extract just the first paragraph
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                # Find the first paragraph that isn't a likely warning/box
                # Usually the first <p> after some infoboxes
                for p in soup.find_all('p'):
                    # Use separator to avoid "Volthas" (merging valid tags without space)
                    text = p.get_text(separator=' ', strip=True)
                    
                    # Filter out short/empty paragraphs or Update notes
                    if len(text) > 50 and "Update" not in text: 
                         # Return full paragraph up to 800 chars 
                         return f"<h3>Wiki: {item_name}</h3>{text[:800]}{'...' if len(text) > 800 else ''}"
                
                # Fallback
                return f"Wiki: Found page, click for details."
            
            return "Wiki: No summary content found."
        except Exception as e:
            return f"Wiki search failed: {e}"

    @staticmethod
    def get_bis_mods(item_name):
        url, result = OverframeClient.get_top_build(item_name)
        
        if not url:
            # Fallback to search link
            url_name = item_name.replace(' ', '%20')
            overframe_url = f"https://overframe.gg/items/search?q={url_name}"
            return overframe_url

        return url

if __name__ == "__main__":
    # Test
    state = WarframeAPI.get_world_state()
    if state:
        print(f"Current Date: {state['timestamp']}")

class WarframeReference:
    # Simplified Damage Effectiveness
    DAMAGE_TABLE = """
    <style>
        th { text-align: left; color: #00d2ff; }
        td { padding-right: 15px; }
        .plus { color: #00ff88; }
        .minus { color: #ff5555; }
    </style>
    <h3>Damage Types</h3>
    <table>
        <tr><th>Faction</th><th>Weakness (++)</th><th>Resistance (--)</th></tr>
        <tr><td>Grineer (Ferrite)</td><td class='plus'>Corrosive</td><td class='minus'>Blast</td></tr>
        <tr><td>Grineer (Alloy)</td><td class='plus'>Radiation</td><td class='minus'>Electric, Magnetic</td></tr>
        <tr><td>Corpus (Shields)</td><td class='plus'>Magnetic, Cold</td><td class='minus'>Radiation</td></tr>
        <tr><td>Corpus (Proto)</td><td class='plus'>Magnetic, Toxin</td><td class='minus'>Corrosive</td></tr>
        <tr><td>Infested (Light)</td><td class='plus'>Gas, Heat</td><td class='minus'>Radiation, Viral</td></tr>
        <tr><td>Infested (Fossil)</td><td class='plus'>Corrosive, Blast</td><td class='minus'>Cold</td></tr>
    </table>
    
    <h3>Status Effects</h3>
    <table>
        <tr><th width="80">Status</th><th>Effect</th></tr>
        <tr><td>Slash</td><td>Health Dmg over time (Bypasses Armor)</td></tr>
        <tr><td>Impact</td><td>Stagger / Mercy Kill threshold</td></tr>
        <tr><td>Puncture</td><td>Reduces Enemy Damage</td></tr>
        <tr><td>Heat</td><td>DoT + Strips 50% Armor</td></tr>
        <tr><td>Cold</td><td>Slows Enemy + Crit Dmg Bonus</td></tr>
        <tr><td>Electric</td><td>Chain Lightning DoT</td></tr>
        <tr><td>Toxin</td><td>Health DoT (Bypasses Shield)</td></tr>
        <tr><td>Blast</td><td>AoE Dmg + Reduces Accuracy</td></tr>
        <tr><td>Corrosive</td><td>Strips Armor</td></tr>
        <tr><td>Gas</td><td>AoE Gas Clouds</td></tr>
        <tr><td>Magnetic</td><td>Increased Shield Dmg + Disables Regen</td></tr>
        <tr><td>Radiation</td><td>Confusion (Friendly Fire)</td></tr>
        <tr><td>Viral</td><td>Increases Damage to Health</td></tr>
    </table>
    """
