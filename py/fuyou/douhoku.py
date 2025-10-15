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
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#results > li.listItem"))
    )
    
    # 初回リンクの取得
    item_links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "#results >  li.listItem >  div.listHeader > a")]

    # ページの一番下までスクロールして、さらにリンクを取得
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    for _ in range(10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight / 10 * ({_ + 1}));")
        time.sleep(1)  # スクロール後、少し待機してリンクがロードされるのを待つ

    # 再度リンクの取得
    item_links += [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "#results  > li.listItem  > div.listHeader > a")]

    # 重複リンクを削除して返す
    return list(set(item_links))


def fetch_info(url):
    driver = driver_factory.create_driver()
    try:
        driver.get(url)

        try:
            WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#VcArea-Tab > section.d-sec.-detailBottom > div > div.b-parts.-p21-1")))
        except Exception as e:
            logger.error(f"Error occurred while waiting for elements: {e}")

        try:
            # 郵便番号
            zipcode = driver.find_element(By.CSS_SELECTOR, 'span[data-key="zipCode"]').text.strip()

            # 住所（都道府県 + 市区町村）
            prefecture = driver.find_element(By.CSS_SELECTOR, 'span[data-key="prefecture"]').text.strip()
            city = driver.find_element(By.CSS_SELECTOR, 'span[data-key="city"]').text.strip()

            # 電話番号
            telno = driver.find_element(By.CSS_SELECTOR, 'dd[data-key="tel"] a').text.strip()

            # 営業時間（複数あれば結合）
            hours = [e.text.strip() for e in driver.find_elements(By.CSS_SELECTOR, 'dd[data-key^="openHour"]') if e.text.strip()]
            eigyo =  " / ".join(hours)

            # 売場面積
            uriba = driver.find_element(By.CSS_SELECTOR, 'span[data-key="floorArea"]').text.strip()

            # 駐車場台数
            parking= driver.find_element(By.CSS_SELECTOR, 'span[data-key="numOfParkingSpaces"]').text.strip()

        except Exception as e:
            logger.error(f"Error occurred while extracting shop name: {e}")
        
      

        print(f"{url=}, {zipcode=}, {eigyo=}, {telno=},{prefecture=},{city=},{uriba=},{parking=}")
        return (url, zipcode, eigyo, telno, prefecture, city, uriba, parking)

    except Exception as e:
        print(f"エラーが発生しました: {url} - {e}")
        traceback.print_exc()
        return (url, '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
    finally:
        driver.quit()

def getget_parallel(urls,filename):
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '郵便番号', '営業時間', '電話番号', '都道府県', '市区町村', '売場面積', '駐車場台数'])

        with ThreadPoolExecutor(max_workers=5) as executor: 
            futures = [executor.submit(fetch_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    search_urls = const.douhoku_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.maruto_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls = fetch_item_urls(search_url)
        print(urls)  
        getget_parallel(urls,new_filename)  
