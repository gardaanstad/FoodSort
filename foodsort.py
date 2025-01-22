import sys
from typing import *
import os
import time
from lxml import html
import aiohttp
import asyncio
import json
import datetime

DEBUG = True

class Stats:
    def __init__(self):
        self.start_time = time.time()
        self.cache_hits = []
        self.cache_misses = []
        self.total_items = 0
        self.errors = 0
        self.scrape_time = 0.0
        self.total_categories = 0
        self.processed_categories = 0

    def print_cache_status(self):
        print("\n=== Cache Status ===")
        for url in self.cache_hits:
            print(f"✅ [Cached] {url}")
        for url in self.cache_misses:
            print(f"❌ [Uncached] {url}")
        print()

async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        return await response.text()

async def fetch_all(session: aiohttp.ClientSession, urls: list[str]) -> list[str]:
    tasks = [asyncio.create_task(fetch(session, url)) for url in urls]
    return await asyncio.gather(*tasks)

def amount_float(s: str):
    if not s:
        return 0
    
    if ',' in s:
        return 0
    
    if 'kJ' in s and 'kcal' not in s:
        return 0

    if 'kcal' in s:
        s = s.split(' ') # ["2000", "kJ", "/", "500", "kcal"]
        return float(s[3]) # 500.0              ^^^
    else:
        s = s.split(' ') # ["200", "g"]
        return float(s[0]) # 200.0

class Item:
    def __init__(self, tree: html.HtmlElement, item_url: str, options: dict):
        self.item_url = item_url
        self.__parse_item(tree, options)

    def __parse_item(self, tree: html.HtmlElement, options: dict):
        self.name = tree.xpath(options["name_path"])[0].strip()
        brand_text = tree.xpath(options["brand_path"])[0].strip()
        self.brand = brand_text.split(' g, ')[-1] if ' g, ' in brand_text else "Not specified"
        self.weight = amount_float(tree.xpath(options["weight_path"])[0])
        ingredients = tree.xpath(options["ingredients_path"])
        self.ingredients = ingredients[0] if ingredients else None
        self.calories = amount_float(tree.xpath(options["energi_path"])[0])
        self.fat = amount_float(tree.xpath(options["fett_path"])[0])
        self.carbs = amount_float(tree.xpath(options["karbohydrater_path"])[0])
        self.fiber = amount_float(tree.xpath(options["kostfiber_path"])[0])
        self.protein = amount_float(tree.xpath(options["protein_path"])[0])

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'brand': self.brand,
            'weight': self.weight,
            'ingredients': self.ingredients,
            'calories': self.calories,
            'fat': self.fat,
            'carbs': self.carbs,
            'fiber': self.fiber,
            'protein': self.protein
        }

def load_cache() -> dict:
    try:
        with open('cache.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_cache(cache_data: dict):
    with open('cache.json', 'w') as f:
        json.dump(cache_data, f, indent=2)

def update_progress(stats: Stats):
    processed = stats.processed_categories
    total = stats.total_categories
    if total == 0:
        return
    
    bar_length = 40
    progress = processed / total
    filled = int(bar_length * progress)
    bar = '█' * filled + ' ' * (bar_length - filled)
    percentage = progress * 100
    print(f"\rScraping progress: [{bar}] {percentage:.0f}% ({processed}/{total} categories)", end='')

async def process_category(category_url: str, options: dict, stats: Stats) -> dict:
    items = {}
    async with aiohttp.ClientSession() as session:
        # Fetch category page
        html_string = await fetch(session, category_url)
        category_tree = html.fromstring(html_string)
        
        # Extract item URLs
        item_urls = [f"https://oda.com{url}" 
                    for url in category_tree.xpath(options["item_url_path"])]
        
        # Fetch all items in category
        item_htmls = await fetch_all(session, item_urls)
        
        # Parse items
        for url, html_content in zip(item_urls, item_htmls):
            try:
                tree = html.fromstring(html_content)
                item = Item(tree, url, options)
                items[url] = item.to_dict()
            except Exception as e:
                stats.errors += 1
                if DEBUG:
                    print(f"\nError processing {url}: {str(e)}")
        
        # Update progress
        stats.processed_categories += 1
        update_progress(stats)
        return items


# ===================================================================================

# I/O

# ===================================================================================


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def display_stats(stats: Stats):
    print("—" * 30)
    print("Statistics".center(30))
    print("—" * 30)
    print(f"Total scrape time: {stats.scrape_time:.2f}s")
    print(f"Total items: {stats.total_items}")
    print(f"Errors: {stats.errors}")
    stats.print_cache_status()

def display_menu():
    print("—" * 30)
    print("Main Menu".center(30))
    print("—" * 30)
    print("1. List all items")
    print("2. Sort items")
    print("3. Show processing statistics")
    print("4. Clear cache")
    print("0. Exit")

async def main():
    stats = Stats()
    clear_screen()
    
    # Load configuration
    with open("options.json") as f:
        options = json.load(f)["oda.com"]
    
    category_urls = [
        "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=1",
        "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=2",
        "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=3",
        "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=4",
        "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=5",
    ]
    
    # Cache handling
    cache_data = load_cache()
    items = {}
    
    # Check cache status for each category
    print("Initial cache check:")
    for url in category_urls:
        if url in cache_data:
            items.update(cache_data[url]["items"])
            stats.cache_hits.append(url)
            print(f"✅ [Cached] {url}")
        else:
            stats.cache_misses.append(url)
            print(f"❌ [Uncached] {url}")
    
    # Setup progress tracking
    stats.total_categories = len(stats.cache_misses)
    stats.processed_categories = 0
    
    # Process uncached categories
    if stats.cache_misses:
        print("\nStarting scraping process...")
        start_time = time.time()
        for category_url in stats.cache_misses:
            category_items = await process_category(category_url, options, stats)
            items.update(category_items)
            
            # Update cache
            cache_data[category_url] = {
                "timestamp": datetime.datetime.now().isoformat(),
                "items": category_items
            }
            save_cache(cache_data)
        stats.scrape_time = time.time() - start_time
        print("\n\nScraping complete!")
    
    stats.total_items = len(items)
    
    # Cross-platform key detection setup
    if os.name == 'nt':
        import msvcrt
        def get_key():
            return msvcrt.getch().decode('utf-8')
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        original_settings = termios.tcgetattr(fd)

        def get_key():
            try:
                tty.setraw(sys.stdin.fileno())
                char = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, original_settings)
            return char

    # User interaction loop
    try:
        skip_to = "-1"
        while True:
            clear_screen()
            display_menu()
            print("\nSelect an option\n> ", end='', flush=True)
            
            # Get choice
            choice = get_key() if skip_to == "-1" else f"{skip_to}"
            
            if choice == "1":
                clear_screen()
                
                for url, data in items.items():
                    print(f"{data['name']} ({data['brand']})")
                print("\nPress any key to return\n> ", end="", flush=True)
                get_key()

            elif choice == "2":
                clear_screen()
                
                print("What do you want to sort the items by?\n1. Calories\n2. Protein\n3. Carbs\n4. Fat\n5. Weight\n0. Return\n\nSelect an option\n> ", end="", flush=True)
                sort_choice = get_key()
                
                fields = {"1": "calories", "2": "protein", 
                        "3": "carbs", "4": "fat", "5": "weight"}
                
                if sort_choice == "0":
                    continue
                
                if sort_choice in fields:
                    clear_screen()
                    
                    sorted_items = sorted(items.items(), 
                                        key=lambda x: x[1][fields[sort_choice]], 
                                        reverse=True)
                    
                    for url, data in sorted_items:
                        print(f"{data['name']}: {data[fields[sort_choice]]}g")
                    
                    print("\nPress any key to return\n> ", end="", flush=True)
                    get_key()
                else:
                    print("Invalid choice")
                    skip_to = "2"
                    time.sleep(1)
                    continue
            
            elif choice == "3":
                clear_screen()
                
                display_stats(stats)
                
                print("\nPress any key to return\n> ", end="", flush=True)
                get_key()
            
            elif choice == "4":
                clear_screen()
                
                if os.path.exists("cache.json"):
                    os.remove("cache.json")
                    print("Cache cleared")
                else:
                    print("No cache found")
                
                print("\nPress any key to return\n> ", end="", flush=True)
                get_key()

            elif choice == "0":
                print("\n\nGoodbye!")
                break

            # Add slight delay to ensure terminal stability
            skip_to = "-1"
            time.sleep(0.01)

    finally:
        if os.name != 'nt':
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original_settings)

if __name__ == '__main__':
    asyncio.run(main())