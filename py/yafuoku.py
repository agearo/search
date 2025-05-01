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
    
    # 初回リンクの取得
    # item_links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "ul.Products__items li div.Product__detail h3 a")]
    atags = driver.find_elements(By.CSS_SELECTOR, "ul.Products__items li div.Product__detail h3 a")

    # ページの一番下までスクロールして、さらにリンクを取得
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    for _ in range(10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight / 10 * ({_ + 1}));")
        time.sleep(1)  # スクロール後、少し待機してリンクがロードされるのを待つ

    # 再度リンクの取得
    # item_links += [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "ul.Products__items li div.Product__detail h3 a")]
    atags += driver.find_elements(By.CSS_SELECTOR, "ul.Products__items li div.Product__detail h3 a")
    atags = list(set(atags))

    links_with_index= []
    for atag in atags:
        url = atag.get_attribute("href")
        index = atag.get_attribute("data-cl_cl_index")
        links_with_index.append((url, int(index)))

    # インデックス順に並び替え
    links_with_index.sort(key=lambda x: x[1])

    # ソートされたURLだけ取得
    print(links_with_index)
    sorted_urls = [link[0] for link in links_with_index]
    sorted_index = [link[1] for link in links_with_index]

    # 重複リンクを削除して返す
    return sorted_urls


def fetch_info(url):
    driver = driver_factory.create_driver()
    max_retries=3

    for attempt in range(1, max_retries + 1):
        try:
            driver.get(url)
            time.sleep(1)

            # ヤフオクはF5でリロードしないと表示されない
            driver.refresh()

            # 商品名の部分読むまで待つ
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.sc-f3056978-17.qnBjW.ItemDetail__ShippingFreeLabel"))
            )


            # 送料無料部分
            try:
                shipping = driver.find_element(By.CSS_SELECTOR, "span.sc-f3056978-17.qnBjW.ItemDetail__ShippingFreeLabel").text
            except:
                shipping = "取得失敗"

            # 金額部分
            try:
                price = driver.find_element(By.CSS_SELECTOR, "span.sc-43a21b02-0.lfSzHD").text
            except:
                price = "取得失敗"

            # 本人部分
            try:
                identity = driver.find_element(By.CSS_SELECTOR, "p.sc-368024b-5.kDifBZ").text
            except:
                identity = "取得失敗"

            # 星部分
            try:
                stars = driver.find_elements(By.CSS_SELECTOR, "span.sc-a4717d6d-1.ijyROn")
                # 星の数（要素の数）をカウント
                star_count = len(stars)
            except:
                star_count = "取得失敗"

            # 説明部分
            try:
                description = driver.find_element(By.CSS_SELECTOR, "span.sc-43a21b02-0.bgOrgw").text
            except:
                description = "取得失敗"

            try:
                response = gemini_client.generate_content(description + "\n この説明から重さを推測して。大体でいいから。わかったら単位はgとして、数字で答えて。500g以下と思われるなら500と答えて。余計な説明はしないで。")
                omosa = response
            except:
                omosa = "取得失敗"

            print(f"{url}, {shipping}, {price},{identity},{star_count},{omosa}")
            return (url, shipping, price, identity, description,omosa.strip(),star_count)

        except Exception as e:
            print(f"エラーが発生しました: {url} - {e}")
            traceback.print_exc()
            if attempt == max_retries:
                return (url, '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
            else:
                time.sleep(3)  # 少し待ってからリトライする
        finally:
            driver.quit()

def getget_parallel(urls,filename):
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '送料', '金額', '本人', '説明', '重さ', '星'])

        with ThreadPoolExecutor(max_workers=5) as executor: 
            futures = [executor.submit(fetch_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    search_urls = const.yafu_search_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.yafu_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls = fetch_item_urls(search_url)
        print(urls)  
        getget_parallel(urls,new_filename)  
