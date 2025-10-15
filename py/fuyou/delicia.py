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
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.flex-row.shop-list-card"))
    )
    
    # 初回リンクの取得
    blocks = driver.find_elements(By.CSS_SELECTOR, "div.flex-row.shop-list-card")
    # ページの一番下までスクロールして、さらにリンクを取得
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    for _ in range(10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight / 10 * ({_ + 1}));")
        time.sleep(1)  # スクロール後、少し待機してリンクがロードされるのを待つ

    # 再度リンクの取得
    # blocks += [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "div.flex-row.shop-list-card")]
    blocks += driver.find_elements(By.CSS_SELECTOR, "div.flex-row.shop-list-card")

    detail_urls = [
    block.find_element(
        By.CSS_SELECTOR, 'a[href*="/shop/"]:not([href*="#chirashi"])'
    ).get_attribute("href")
    for block in blocks
]

    # 重複リンクを削除して返す
    return list(set(detail_urls))


def fetch_info(url):
    driver = driver_factory.create_driver()
    try:
        driver.get(url)

        try:
            # 店舗情報ブロックの読み込み待機
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.shop-details-wrapper-35")
                )
            )
        except Exception as e:
            logger.error(f"Error occurred while waiting for elements: {e}")

        try:
            # 店舗情報ブロック
            block = driver.find_element(By.CSS_SELECTOR, "div.shop-details-wrapper-35")
            
            # 左側ラベルと右側値
            labels = block.find_elements(By.CSS_SELECTOR, "div.info-grid-left h4")
            values = block.find_elements(By.CSS_SELECTOR, "div.info-grid-right p")
            
            info_dict = {}
            for label, value in zip(labels, values):
                info_dict[label.text.strip()] = value.text.strip()

            zipcode = ""  # このHTMLでは郵便番号は住所の先頭に含まれるので分割してもよい
            if "住所" in info_dict:
                addr_text = info_dict["住所"]
                if addr_text.startswith("〒"):
                    zipcode, address = addr_text.split("　", 1)  # 「〒xxxx-xxxx　住所」の形式を分割
                else:
                    address = addr_text
            else:
                address = ""

            telno = info_dict.get("TEL", "")
            eigyo = info_dict.get("営業時間", "")
            teikyu = info_dict.get("定休日", "")
            parking = info_dict.get("駐車場", "")

        except Exception as e:
            logger.error(f"Error occurred while extracting shop info: {e}")
            zipcode = address = telno = eigyo = teikyu = parking = "取得失敗"

        print(f"{url=}, {zipcode=}, {address=}, {eigyo=}, {telno=}, {teikyu=}, {parking=}")
        return (url, zipcode, address, eigyo, telno, teikyu, parking)

    except Exception as e:
        print(f"エラーが発生しました: {url} - {e}")
        traceback.print_exc()
        return (url, '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
    finally:
        driver.quit()

def getget_parallel(urls,filename):
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '郵便番号', '住所', '営業時間', '電話番号', '定休日', '駐車場'])

        with ThreadPoolExecutor(max_workers=10) as executor: 
            futures = [executor.submit(fetch_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    search_urls = const.delicia_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.delicia_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls = fetch_item_urls(search_url)
        print(urls)  
        getget_parallel(urls,new_filename)  
