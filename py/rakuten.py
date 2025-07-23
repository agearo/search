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

"""
このスクリプトは、メルカリの商品情報を自動で取得するためのものです。
主に以下の機能を持っています。 
1. 指定されたURLから商品リンクを取得する。(検索結果1ページに表示される商品数まで)
2. 各商品リンクから詳細情報を取得する。(金額、送料、本人確認、説明文、重さ、星)
3. 重さはGeminiを使用して推測します。
4. 取得した情報をCSVファイルに保存する。
"""

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
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".image-wrapper--3eWn3"))
    )

    # 初回リンクの取得 
    item_links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, ".image-wrapper--3eWn3 a[target='_top']")]

    # ページの一番下までスクロールして、さらにリンクを取得
    scroll_to_bottom(driver)

    # 複数の商品親要素を取得
    items = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((
            By.CSS_SELECTOR,
            ".dui-card.searchresultitem.overlay-control-wrapper--3KBO0.title-control-wrapper--1rzvX"
        ))
    )

    # 再度リンクの取得
    results = []
    for item in items:
        try:
            # URL取得
            url = item.find_element(By.CSS_SELECTOR, ".image-wrapper--3eWn3 a[target='_top']").get_attribute("href")

            # 価格取得
            price = item.find_element(By.CSS_SELECTOR, ".price--3zUvK").text

            # 送料判定
            try:
                item.find_element(By.CLASS_NAME, "free-shipping-label--1shop")
                shipping = "送料無料"
            except:
                try:
                    shipping = item.find_element(By.CLASS_NAME, "paid-shipping-wrapper--1Sq8U").text
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



    # 重複リンクを削除して返す
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
    search_urls = const.rakuten_search_urls
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




