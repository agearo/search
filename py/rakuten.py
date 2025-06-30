from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import sys
import traceback
from pathlib import Path
import logging
from webdriver_manager.chrome import ChromeDriverManager
import const
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading  
import google.generativeai as genai
import datetime
from util.driver_factory import DriverFactory
from util.gemini_client import GeminiClient

gemini_client = GeminiClient()
driver_factory=DriverFactory()
lock = threading.Lock()

# プロジェクトルートをsys.pathに追加
sys.path.append(str(Path(__file__).resolve().parent.parent))
from conf.log_config import setup_logging

# ログ設定を読み込み
setup_logging(__file__)
logger = logging.getLogger(__name__)

# 商品リンクを取得する関数
def fetch_item_urls(search_url):
    driver = driver_factory.create_driver()
    
    
    # URLにアクセス
    driver.get(search_url)

    # ページが完全に読み込まれるまで待機
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#risFil > table:nth-child(3)"))
    )
    scroll_to_bottom(driver)
    # 商品名と価格があるtdを取得
    td_elements = driver.find_elements(By.CSS_SELECTOR, 'td')

    products=[]

    i=0
    for td in td_elements:
        len(products)
        try:
            # 商品リンク
            link_el = td.find_element(By.CSS_SELECTOR, 'a.category_itemnamelink')
            link = link_el.get_attribute("href")
            title = link_el.text.strip()

            # 価格
            price_el = td.find_element(By.CSS_SELECTOR, 'span.category_itemprice')
            price = price_el.text.strip().replace('\u00a0', '').replace('円', '').replace(',', '')

            # 送料無料判定
            try:
                shipping_el = td.find_element(By.CSS_SELECTOR, 'span.shippingCost_free')
                shipping = '送料無料' in shipping_el.text
            except:
                shipping = False

            products.append({
                'タイトル': title,
                '価格': price,
                'URL': link,
                '送料無料': 'はい' if shipping else 'いいえ',
            })
        except:
            continue
    driver.quit()   
    return products

def scroll_to_bottom(driver, pause_time=5):
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # 一番下までスクロール
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # 読み込み待ち
        time.sleep(pause_time)

        # 新しい高さを取得
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # スクロール後の高さが変わらなければ一番下まで到達したと判断
            break
        last_height = new_height



def write_to_csv(products, filename):
    with open(filename, 'w', newline='', encoding='cp932') as f:
        writer = csv.DictWriter(f, fieldnames=['タイトル', '価格', 'URL', '送料無料'])
        writer.writeheader()
        writer.writerows(products)

# メイン処理
if __name__ == "__main__":
    search_urls = const.rakuten_search_urls
    urls = fetch_item_urls(search_urls[0])
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{const.out_dir}{const.rakuten_filename.replace('.csv', '')}_{current_time}.csv"
    write_to_csv(urls,new_filename)
