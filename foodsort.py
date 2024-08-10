from lxml import html
import requests
import aiohttp
import asyncio



def item_urls_from_category_html(tree: html):
    return tree.xpath('//a[@class="k-text-style k-text-style--body-m k-text--weight-bold k-text--none k-link AppLink_LinkContainer__JZumo components_ModalTileLink__xMAm0 k-link--text AppLink_AppLink__uXETs"]/@href')

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

def item_dict_from_html(tree: html, vare_id: int):
    vare_navn = tree.xpath('//*[@class="k-text-style k-text-style--display-xs k-text-color--display"]/text()')[0]
    print(f"  {vare_id} | {vare_navn}")
    
    vare_merke = tree.xpath('//*[@class="k-text-style k-text-style--body-xl k-text-color--subdued"]/text()')[0]
    
    vare_info = tree.xpath('//div[@data-state="open"]/div/div/p[@class="k-text-style k-text-style--body-m k-text--pre-wrap"]/text()')
    
    info_index = 0
    if not vare_info[1][0].isnumeric():
        info_index += 1
    vare_vekt = vare_info[1 + info_index]
    vare_ingredienser = vare_info[2 + info_index]
    
    
    content_labels = tree.xpath('//div[@data-state="closed"]/div/div/span[@class="k-text-style k-text-style--body-m k-text--weight-bold"]/text()')
    del content_labels[0] # "Næringsinnhold pr. 100g/ml"
    
    content = tree.xpath('//div[@data-state="closed"]/div/div/p[@class="k-text-style k-text-style--body-m k-text--pre-wrap"]/text()')
    
    content_dict = {}
    for label, amount in zip(content_labels, content):
        content_dict.update({label: amount})

    vare_dict = {vare_id: {"navn": vare_navn, # string
                            "merke": vare_merke, # string
                            "ingredienser": vare_ingredienser, # string
                            "vekt": amount_float(vare_vekt), # float gram
                            "kalorier": amount_float(content_dict.get('Energi')), # float kcal
                            "fett": amount_float(content_dict.get('Fett')), # float gram
                            "karbohydrater": amount_float(content_dict.get('Karbohydrater')), # float gram
                            "protein": amount_float(content_dict.get('Protein'))}} # float gram
    
    return vare_dict

def sort_dict(d: dict, sort_by: str):            
    return dict(sorted(d.items(), key=lambda item: item[1][sort_by], reverse=True))

async def main():
    category_urls = [
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=1",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=2",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=3",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=4",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/68-chips-og-snacks/?cursor=5",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=1",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=2",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=3",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=4",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=5",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=6",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/69-sjokolade/?cursor=7",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=1",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=2",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=3",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=4",
                    "https://oda.com/no/categories/67-sjokolade-snacks-og-godteri/70-godteri/?cursor=5",
                    ]
    
    print("Getting item URLs from category URLs...")
    async with aiohttp.ClientSession() as session:
        category_htmls = await fetch_all(session, category_urls)
    
    item_urls = []
    
    for tree_html in category_htmls:
        tree = html.fromstring(tree_html)
        item_urls.append(item_urls_from_category_html(tree))
    
    item_urls = [item for row in item_urls for item in row]
    
    item_urls = [("https://oda.com" + url) for url in item_urls]
    
    print("Scraping information for each item...")
    async with aiohttp.ClientSession() as session:
        htmls = await fetch_all(session, item_urls)
    
    items_dict = {}
    
    count = 1
    for tree_html in htmls:
        tree = html.fromstring(tree_html)
        items_dict.update(item_dict_from_html(tree, count))
        count += 1
    
    print("All items have been loaded!\n")
    
    keep_going = True
    while keep_going:
        print("\nWhat do you want to do?\n  1: List all items\n  2: Sort items\n  3: Filter items with allergy\n  Q: Exit")
        action = input("\n> ").lower()
        match action:
            case 'q':
                keep_going = False
            case '1':
                for item in items_dict.values():
                    print(f"{item['navn']}:\n  Weight: {item['vekt']}\n  Calories: {item['kalorier']}\n  Fat: {item['fett']}\n  Carbohydrates: {item['karbohydrater']}\n  Protein: {item['protein']}")
            case '2':
                print("\nWhat do you want to sort the items by?\n  Weight\n  Calories\n  Fat\n  Carbohydrates\n  Protein")
                sort_by = input("\n> ").lower()
                sorted_dict = sort_dict(items_dict, sort_by)
                
                if sort_by == "kalorier":
                    suffix = "kcal"
                else:
                    suffix = "gram"
                
                for item_id, item_info in sorted_dict.items():
                    print(f"{item_info[sort_by]} {suffix} | {item_info['navn']}")

if __name__ == '__main__':
    asyncio.run(main())