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
    print('アクセス中:', search_url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#risFil > table:nth-child(3) > tbody > tr"))
    )

    # ページの一番下までスクロールして、さらにリンクを取得
    scroll_to_bottom(driver)

    # 複数の商品親要素を取得
    item_rows = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR,"#risFil > table:nth-child(3) > tbody > tr"))
    )
    filtered_items = []

    for row in item_rows:
        tds = row.find_elements(By.TAG_NAME, "td")
        for td in tds:
            try:
                td.find_element(By.CLASS_NAME, "category_itemnamelink")  # 存在確認
                filtered_items.append(td)
            except:
                continue

    # 再度リンクの取得
    results = []
    for item in filtered_items:
        try:
            # URL取得
            url = item.find_element(By.CLASS_NAME, "category_itemnamelink").get_attribute("href")

            # 価格取得
            price = item.find_element(By.CLASS_NAME, "category_itemprice").text

            # 送料判定
            try:
                shipping=item.find_element(By.CLASS_NAME, "category_itemtaxpostage").text
            except:
                try:
                    shipping=item.find_element(By.CLASS_NAME, "category_itemtaxpostage").text
                except:
                    shipping = "送料情報なし"

            # 1セットとして追加
            results.append({
                "url": url,
                "price": price,
                "shipping": shipping
            })

        except Exception as e:
            print("要素取得失敗:", e)

    return results
    

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

# メイン処理
if __name__ == "__main__":
    search_urls = const.rakuten_koten_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.rakuten_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        results = fetch_item_urls(search_url)
        print(results) 
        with open(new_filename, "w", newline="", encoding="cp932") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "price", "shipping"])
            writer.writeheader()
            writer.writerows(results)




