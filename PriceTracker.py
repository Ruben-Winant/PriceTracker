import os
from datetime import date

import matplotlib.pyplot as plt
import numpy
import pandas as pd
import requests
from bs4 import BeautifulSoup
import uuid
from itertools import groupby

PRODUCT_URL_CSV = "products.csv"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.0 '
                         'Safari/537.36'}


def main():
    df = get_urls(PRODUCT_URL_CSV)
    df_updated = process_products(df)
    generate_history_data(df_updated)
    #   enable this to also show a price graph
    visualize_price_history()


def visualize_price_history():
    if os.path.exists("prices.csv"):
        data = pd.read_csv("prices.csv", sep=',').sort_values('prijs').sort_values('datum')
        unique_dates = numpy.unique(data['datum'])

        with open("prices.csv") as f:
            text = f.read().splitlines()[1:]
            for k, v in groupby(sorted(text, key=lambda x: (x.split(",")[1], x.split(",")[3])),
                                key=lambda x: (x.split(",")[1], x.split(",")[3])):
                product_name = " - ".join(list(k))
                product_prices = [float(val.split(",")[-1]) for val in v]
                plt.plot(unique_dates, product_prices, label=product_name)

        plt.xlabel("Datum")
        plt.xticks(rotation=45)
        plt.ylabel("Prijs")
        plt.legend(loc='lower right')
        plt.show()


def is_duplicate(item):
    if os.path.exists("prices.csv"):
        if os.path.getsize("prices.csv") == 0:
            print("empty file")
            return True
        else:
            file = pd.read_csv("prices.csv", sep=',').to_dict("records")
            today = date.today()
            for product in file:
                if product['product'] == item['product'] and product['datum'] == "{0}".format(today):
                    return True
    else:
        print("No dupe found")
        return True


def generate_history_data(updated_products):
    path_to_file = "prices.csv"
    for updated_product in updated_products.to_dict("records"):
        data = {'product': updated_product['product'], 'datum': date.today(),
                'winkel': get_site_name(updated_product['url']), 'prijs': updated_product['price']}
        data = pd.DataFrame(data, index=[uuid.uuid4()])
        data.to_csv(path_to_file, mode='a', header=not os.path.exists(path_to_file))


def get_urls(csv_file):
    df = pd.read_csv(csv_file, sep=',')
    return df


def get_response(url):
    response = requests.get(url, headers=headers)
    return response.text


def get_site_name(url):
    site_name = url.split('www.')[1].split('.')[0]
    return site_name


def get_price(html, site_name):
    soup = BeautifulSoup(html, "html.parser")
    price = None
    match site_name:
        case "coolblue":
            price = format(soup.select_one(".sales-price__current").text.strip().replace(',-', ',00'))
        case "alternate":
            price = soup.select_one(".price").text.strip()
        case "bol":
            decimal = soup.select_one(".promo-price").contents[0].text.strip()
            fraction = soup.select_one(".promo-price__fraction").text.strip()
            price = "{0},{1}".format(decimal, fraction)
        case "vandenborre":
            price = soup.select_one(".price-content .current").text.strip()
        case "krefel":
            price = soup.select_one(".current-price").text.strip()
        case "mediamarkt":
            price = soup.select_one(".price").text.strip().replace(',-', ',00')
        case "ikea":
            price = soup.select_one(".pip-temp-price__sr-text").text.strip().replace('Price ', '')

    if price:
        price = price.replace('€ ', '')
        price = price.replace(',', '.')
        price = price.replace('.-', '.0')
        return float(price)


def process_products(df):
    updated_products = []
    for product in df.to_dict("records"):
        if not is_duplicate(product):
            html = get_response(product["url"])
            product["price"] = get_price(html, get_site_name(product["url"]))
            updated_products.append(product)
        else:
            continue
    return pd.DataFrame(updated_products)


main()
