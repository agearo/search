import re
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
    store_data = []
    try:
        # URLにアクセス
        driver.get(search_url)

        # ページが完全に読み込まれるまで待機
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.store-list__outline"))
        )

        # 店舗情報を含む要素を取得
        store_blocks = driver.find_elements(By.CSS_SELECTOR, "div.store-list__outline")

        for i, store_block in enumerate(store_blocks, start=1):
            try:
                # 店名
                try:
                    name = store_block.find_element(By.CSS_SELECTOR, "h2.happy-town-detail__outline__title").text.strip()
                except:
                    try:
                        name = store_block.find_element(By.CSS_SELECTOR, "h2.happys-detail__outline__title").text.strip()
                    except:
                        name = store_block.find_element(By.CSS_SELECTOR, "h2.happymart-detail__outline__title").text.strip()

                # 所在地 (郵便番号 + 住所)
                address_text = store_block.find_element(By.CSS_SELECTOR, "dd.store-list__outline__address").text.strip()
                zipcode_match = re.search(r"(\d{3}-\d{4})", address_text)
                zipcode = zipcode_match.group(1) if zipcode_match else ""
                address = address_text.replace("〒" + zipcode, "").strip()

                # 電話番号
                tel = store_block.find_element(By.CSS_SELECTOR, "dd.store-list__outline__tel").text.strip()

                # 営業時間
                business_hours = store_block.find_element(By.CSS_SELECTOR, "dd.store-list__outline__note").text.strip()

                # 配列に追加
                store_data.append([name, zipcode, address, tel, business_hours])
                print(name, zipcode, address, tel, business_hours)

            except Exception as e:
                logger.error(f"Error fetching store {i}: {e}")
                traceback.print_exc()

    finally:
        driver.quit()

    return store_data

# メイン処理
if __name__ == "__main__":
    search_urls = const.hapiurl
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.hapi_filename.replace('.csv', '')}_{current_time}.csv"
        stores = fetch_item_urls(search_url)
        # CSV保存
        with open(new_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["店名", "郵便番号", "住所", "電話番号", "営業時間"])  # ヘッダー
            writer.writerows(stores)  # データをまとめて書く