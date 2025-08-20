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

def fetch_info(url):
    driver = driver_factory.create_driver()
    try:
        driver.get(url)
        stores = []

        for row in driver.find_elements(By.CSS_SELECTOR, "tr.store-row"):
            # 店舗名
            name = row.find_element(By.CSS_SELECTOR, ".store-name").text.strip()

            # 住所（駐車場や地図リンクを除いた最初の div のテキスト）
            address = row.find_element(By.CSS_SELECTOR, ".address div div").text.strip()

            # 駐車場（ない場合は "なし"）
            parking_elems = row.find_elements(By.CSS_SELECTOR, ".address .parking")
            parking = parking_elems[0].text.strip() if parking_elems else "なし"

            # 営業時間（<br>を含むHTMLそのまま）
            bizhours_html = row.find_element(By.CSS_SELECTOR, ".bizhours span").get_attribute("innerHTML").strip()

            # 電話番号
            phone = row.find_element(By.CSS_SELECTOR, ".tel a").text.strip()

            stores.append({
                "店舗名": name,
                "住所": address,
                "営業時間": bizhours_html,
                "駐車場": parking,
                "電話番号": phone
            })

            print(f"{name=}, {bizhours_html=}, {phone=},{address=},{parking=}")
        # storesをCSVに書き込む
        return stores

    except Exception as e:
        print(f"エラーが発生しました: {url} - {e}")
        traceback.print_exc()
        return ('取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
    finally:
        driver.quit()

def getget_parallel(urls, filename):
    with open(filename, 'w', newline='', encoding='cp932', errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['店舗名', '営業時間', '電話番号', '店舗所在地', '駐車場'])

        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(fetch_info, url) for url in urls]

            for future in as_completed(futures):
                store_list = future.result()  # 複数店舗のリストが返る
                with lock:
                    for store in store_list:
                        writer.writerow([
                            store["店舗名"],
                            store["営業時間"],
                            store["電話番号"],
                            store["住所"],
                            store["駐車場"]
                        ])

# メイン処理
if __name__ == "__main__":
    search_urls = const.marut_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.ribure_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls = ["https://www.keiseistore.co.jp/stores/"]
        print(urls)  
        getget_parallel(urls,new_filename)  
