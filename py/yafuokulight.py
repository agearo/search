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
    time.sleep(3)

    # ヤフオクはF5でリロードしないと表示されない
    driver.refresh()
    
    # ページが完全に読み込まれるまで待機
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul.Products__items li div.Product__detail h3 a"))
    )

    # ページの一番下までスクロールして、さらにリンクを取得
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    for _ in range(10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight / 10 * ({_ + 1}));")
        time.sleep(1)  # スクロール後、少し待機してリンクがロードされるのを待つ

    # 複数の商品親要素を取得
    items = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR,"ul.Products__items li div.Product__detail"))
    )

    # 詳細取得
    results = []
    for item in items:
        try:
            url = item.find_element(By.CSS_SELECTOR, ".Product__title a").get_attribute("href")
            price = item.find_element(By.CSS_SELECTOR, ".Product__priceValue").text
            try:
                shipping = item.find_element(By.CSS_SELECTOR, ".Product__postage").text
            except:
                shipping = "不明"
            # 1セットとして追加
            results.append({
                "url": url,
                "price": price,
                "shipping": shipping
            })
        except:
            print(f"商品情報の取得に失敗しました: {item.text}")
            continue
    
    # 重複リンクを削除して返す
    return results


# メイン処理
if __name__ == "__main__":
    search_urls = const.yafu_search_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.yafu_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        results = fetch_item_urls(search_url)
        with open(new_filename, "w", newline="", encoding="cp932") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "price", "shipping"])
            writer.writeheader()
            writer.writerows(results)

