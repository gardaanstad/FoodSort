from typing import *
import os
import time
from lxml import html
import requests
import aiohttp
import asyncio
import json



def item_urls_from_category_html(tree: html, options):
    return tree.xpath(options["item_url_path"])

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def fetch_all(session, urls):
    tasks = []
    for url in urls:
        task = asyncio.create_task(fetch(session, url))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results

async def get_htmls(urls: list[str]) -> AsyncGenerator[html.HtmlElement, None]:
    async with aiohttp.ClientSession() as session:
        for html_string in await fetch_all(session, urls):
            yield html.fromstring(html_string)

def amount_float(s: str):
    if not s:
        return 0
    
    if ',' in s:
        return 0
    
    if 'kJ' in s and 'kcal' not in s:
        return 0

    if 'kcal' in s:
        s = s.split(' ')
        return float(s[3])
    else:
        s = s.split(' ')
        return float(s[0])

class Item:
    def __init__(self, tree, item_id, options):
        self.item_id = item_id
        self.__parse_item(tree, options)

    def __repr__(self):
        return (f"{self.item_id} {self.navn} ({self.merke})\n  Vekt: {self.vekt}g\n  Kalorier: {self.kalorier} kcal\n  Fett: {self.fett}g\n  Karbohydrater: {self.karbohydrater}g\n  Kostfiber: {self.kostfiber}g\n  Protein: {self.protein}g")

    def __str__(self):
        return f"{self.item_id} {self.navn} ({self.merke})"
    
    def get(self, key):
        return getattr(self, key)
    
    def __parse_item(self, tree, options):
        self.navn = tree.xpath(options["name_path"])[0]
        
        merke = tree.xpath(options["brand_path"])[0]
        
        merke = merke.split(' g, ')
        if merke[-1][-1] == 'g':
            merke = "Ikke oppgitt"
        else:
            merke = merke[-1]
        
        self.merke = merke
        
        self.vekt = amount_float(tree.xpath(options["weight_path"])[0])
        
        self.ingredienser = tree.xpath(options["ingredients_path"])
        
        self.kalorier = amount_float(tree.xpath(options["energi_path"])[0])
        self.fett = amount_float(tree.xpath(options["fett_path"])[0])
        self.karbohydrater = amount_float(tree.xpath(options["karbohydrater_path"])[0])
        self.kostfiber = amount_float(tree.xpath(options["kostfiber_path"])[0])
        self.protein = amount_float(tree.xpath(options["protein_path"])[0])

def sort_dict(d: dict, sort_by: str):
    new_d = {id: item.get(sort_by) for id, item in d.items()}
    return dict(sorted(new_d.items(), key=lambda item: item[1], reverse=True))

def sort_items(items: dict[int, Item]):
    while True:
        os.system('clear')
        print("Hva vil du sortere matvarene etter?\n  1: Vekt\n  2: Kalorier\n  3: Fett\n  4: Karbohydrater\n  5: Kostfiber\n  6: Protein\n  0: Gå tilbake til hovedmenyen")
        sort_by = input("\n> ")
        
        match sort_by:
            case '1':
                sort_by = "vekt"
            case '2':
                sort_by = "kalorier"
            case '3':
                sort_by = "fett"
            case '4':
                sort_by = "karbohydrater"
            case '5':
                sort_by = "kostfiber"
            case '6':
                sort_by = "protein"
            case '0':
                return
            case _:
                print("Ugyldig input")
                
        
        sorted_dict = sort_dict(items, sort_by)
        
        if sort_by == "kalorier":
            suffix = "kcal"
        else:
            suffix = "g"
        
        os.system('clear')
        print(f"Sortert etter {sort_by}")
        
        for item_id, value in sorted_dict.items():
            print(f"{value} {suffix} | {items[item_id].navn}")
        
        print("\nHva vil du gjøre?\n  0: Gå tilbake til hovedmenyen\n  1: Sorter på nytt\n")
        sort_by = input("> ")
        
        if sort_by == '0':
            return
        elif sort_by == '1':
            continue
        else:
            print("Ugyldig input")

def user_interaction(items: dict[int, Item]):
    os.system('clear')
    print("Alle matvarer har blitt lastet inn!")
    time.sleep(2)
    
    quit = False
    while not quit:
        os.system('clear')
        print("Hva vil du gjøre?\n  1: Vis alle matvarene\n  2: Sorter matvarene\n  3: Filtrer matvarene med allergener\n  0: Avslutt")
        action = input("\n> ").lower()
        match action:
            case '1':
                os.system('clear')
                print("Liste over alle matvarene:")
                for item in items.values():
                    print(item)
                
                input("\nTrykk enter for å gå tilbake til hovedmenyen... ")
                os.system('clear')
            case '2':
                sort_items(items)
                os.system('clear')
            case '3':
                os.system('clear')
                print("Kommer snart")
                input("\nTrykk enter for å gå tilbake til hovedmenyen... ")
                os.system('clear')
            case '0':
                quit = True
            case _:
                print("Ugyldig input")

async def main():
    os.system('clear')
    
    print("(1/4) Henter innstillinger...")
    json_string = open("options.json", "r").read()
    options = json.loads(json_string)
    options = options["oda.com"]
    assert options is not None, "Options for nettsiden finnes ikke"
    
    category_urls = [
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=1",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=2",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=3",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=4",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=5",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=1",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=2",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=3",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=4",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=5",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=6",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=7",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=1",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=2",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=3",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=4",
                    # "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=5",
                    ]
    
    print("(2/4) Henter matvare-URLer fra kategoriene...")
    category_htmls = get_htmls(category_urls)
    
    item_urls = []
    
    async for category_html in category_htmls:
        item_urls.extend(item_urls_from_category_html(category_html, options))
    
    item_urls = [("https://oda.com" + url) for url in item_urls]
    
    print("(3/4) Henter informasjon for hver matvare...")
    htmls = get_htmls(item_urls)
    
    items = {}
    
    i = 1
    async for tree in htmls:
        items[i] = Item(tree, i, options)
        i += 1
    
    print("(4/4) Starter brukerinteraksjon...")
    
    user_interaction(items)

if __name__ == '__main__':
    asyncio.run(main())