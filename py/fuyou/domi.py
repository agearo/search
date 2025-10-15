import re
import draconst
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
driver_factory = DriverFactory()
lock = threading.Lock()
driver_lock = threading.Lock()  # ★追加

# プロジェクトルートをsys.pathに追加
sys.path.append(str(Path(__file__).resolve().parent.parent))
from conf.log_config import setup_logging

# ログ設定を読み込み
setup_logging(__file__)
logger = logging.getLogger(__name__)

import re
from datetime import datetime

def geturls(url):
    with driver_lock:
        driver = driver_factory.create_driver()

    driver.get(url)
    rows = driver.find_elements(By.CSS_SELECTOR, "tbody.Store-list-table__body tr")
    for row in rows:
        #URL
        url = row.find_element(By.CSS_SELECTOR, "th a").get_attribute("href")
        namae = row.find_element(By.CSS_SELECTOR, "th a span").text
        print(url,namae)

def scroll_to_bottom(driver, pause_time=1.0):
    """ページ下までスクロールし、動的ロードを待つ"""
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # 下までスクロール
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)  # 読み込み待ち

        # 新しい高さを取得
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break  # 高さが変わらなければ終了
        last_height = new_height

def fetch_info(url):
    with driver_lock:
        driver = driver_factory.create_driver()

    driver.get(url)
    print(f"アクセス: {url}")
    scroll_to_bottom(driver)

    try:
        # ページロード待機（店名が表示されるまで待つ）
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h2.sec__title-border span"))
        )
        time.sleep(1)

        try:
            name = driver.find_element(By.CSS_SELECTOR, "h2.sec__title-border span").text.strip()
        except:
            # spanが無い場合はh2テキストを直接取る
            try:
                name = driver.find_element(By.CSS_SELECTOR, "h2.sec__title-border").text.strip()
            except:
                name = ""

        address = tel = closed = hours = parking = ""

        profile = driver.find_elements(By.CSS_SELECTOR, ".Detail-information__profile dl")
        for item in profile:
            key = item.find_element(By.CSS_SELECTOR, "dt").text.strip()
            value = item.find_element(By.CSS_SELECTOR, "dd").text.strip()

            if key == "所在地":
                address = value
            elif key == "TEL":
                tel = value
            elif key == "定休日":
                closed = value
            elif key == "営業時間":
                hours = value
            elif key == "駐車場":
                m = re.search(r"(\d+)", value)
                parking = m.group(1) if m else "0"

        print("取得結果:", [url, name, address, tel, closed, hours, parking])
        return [url, name, address, tel, closed, hours, parking]

    except Exception as e:
        logger.error(f"Error fetching info from {url}: {e}")
        print("エラー発生:", e)
        return [url, "失敗", "失敗", "失敗", "失敗", "失敗", "失敗"]

    finally:
        driver.quit()


def getget_parallel(urls):
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{const.out_dir}{const.domi_filename.replace('.csv', '')}_{current_time}.csv"
    filename=new_filename
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '店名', '住所', '電話番号', '定休日', '営業時間', '駐車場'])

        with ThreadPoolExecutor(max_workers=10) as executor: 
            futures = [executor.submit(fetch_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    getget_parallel(draconst.domiurls)
    # geturls("https://www.domy.co.jp/store/")
