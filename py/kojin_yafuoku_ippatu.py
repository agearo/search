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

def fetch_item_urls(search_url):
    driver = driver_factory.create_driver()

    driver.get(search_url)
    time.sleep(3)

    # ヤフオクはリロードしないと正しく表示されないことがある
    driver.refresh()

    initlink = "div.Product__detail"

    # ページが完全に読み込まれるまで待機
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, initlink))
    )

    # スクロールして商品をすべて読み込む
    for i in range(10):
        driver.execute_script(
            f"window.scrollTo(0, document.body.scrollHeight / 10 * ({i + 1}));"
        )
        time.sleep(1)

    # 商品要素を取得
    items = driver.find_elements(By.CSS_SELECTOR, initlink)

    results = []
    for item in items:
        try:
            url = item.find_element(By.CSS_SELECTOR, "p.Product__title a").get_attribute("href")
        except:
            url = None

        try:
            price = item.find_element(By.CSS_SELECTOR, ".Product__priceValue").text.strip()
        except:
            price = None

        try:
            shipping = item.find_element(By.CSS_SELECTOR, "p.Product__postage").text.strip()
            shipping = shipping.replace('+', '').replace('円','')
        except:
            shipping = "送料情報なし"

        results.append({
            "url": url,
            "price": price,
            "shipping": shipping
        })

    driver.quit()
    return results


# メイン処理
if __name__ == "__main__":
    search_urls = const.kojin_yafu_search_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.yafu_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)

        results = fetch_item_urls(search_url)

        with open(new_filename, "w", newline="", encoding="cp932") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "price", "shipping"])
            writer.writeheader()
            writer.writerows(results)