import csv
import datetime
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from util.driver_factory import DriverFactory
import const

# 出力ファイル名の設定
current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
output_filename = f"{const.out_dir}{const.amazon_filename.replace('.csv', '')}_{current_time}.csv"

driver_factory = DriverFactory()

def fetch_item_urls(search_url):
    driver = driver_factory.create_driver()
    driver.get(search_url)
    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.s-main-slot div.s-result-item")))
    
    item_links = set()
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        product_elements = driver.find_elements(By.CSS_SELECTOR, "div.s-main-slot div.s-result-item[data-asin]")
        for product in product_elements:
            try:
                asin = product.get_attribute("data-asin")
                if not asin:
                    continue
                a_tag = product.find_element(By.CSS_SELECTOR, "a.a-link-normal.s-no-outline")
                href = a_tag.get_attribute("href")
                data_index = product.get_attribute("data-index")
                if href and "/dp/" in href and data_index:
                    item_links.add((int(data_index), href))  # 重複を防ぐためsetを使用
                    item_links.add(href.split("?")[0])
            except Exception as e:
                print(f"Error extracting link: {e}")

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    driver.quit()
    return list(item_links)


def extract_product_data(driver, url):
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
    asin = asin_match.group(1) if asin_match else ""

    try:
        title_elem = wait.until(EC.presence_of_element_located((By.ID, "productTitle")))
        title = title_elem.text.strip()
    except:
        title = ""

    try:
        desc_elem = driver.find_element(By.ID, "productDescription")
        description = desc_elem.text.strip()
    except:
        # fallback
        try:
            bullets = driver.find_elements(By.CSS_SELECTOR, "#feature-bullets ul li span")
            description = "\n".join(b.text.strip() for b in bullets if b.text.strip())
        except:
            description = ""

    return asin, title, description


def write_product_data_to_csv(product_data_list, filename):
    with open(filename, mode='w', newline='', encoding='cp932') as f:
        writer = csv.writer(f)
        writer.writerow(["ASIN", "Title", "Description", "URL"])
        for asin, title, desc, url in product_data_list:
            writer.writerow([asin, title, desc, url])


if __name__ == "__main__":
    search_url = "https://www.amazon.co.jp/s?k=playstation5&rh=p_6%3AAN1VRQENFRJN5"

    print("検索結果からURLを取得中...")
    product_urls = fetch_item_urls(search_url)

    print("各商品ページから情報を取得中...")
    driver = driver_factory.create_driver()
    product_data_list = []
    for i, url in enumerate(product_urls):
        print(f"{i+1}/{len(product_urls)}: {url}")
        try:
            asin, title, desc = extract_product_data(driver, url)
            product_data_list.append((asin, title, desc, url))
        except Exception as e:
            print(f"Error on {url}: {e}")
        time.sleep(1.5)  # 負荷を下げるための待機

    driver.quit()

    print("CSVに出力中...")
    write_product_data_to_csv(product_data_list, output_filename)
    print(f"完了！ → {output_filename}")
