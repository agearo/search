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

def parse_hours(text):
    """
    "09:00～18:00" の形式から (duration_hours, text) を返す
    """
    match = re.search(r"(\d{2}:\d{2})\s*～\s*(\d{2}:\d{2})", text)
    if match:
        start = datetime.strptime(match.group(1), "%H:%M")
        end = datetime.strptime(match.group(2), "%H:%M")
        hours = (end - start).seconds / 3600
        return hours, match.group(0)  # 時間数, "09:00～18:00"
    return None

def fetch_info(url):
    # driver作成時にロックをかける ★ここだけ変更
    with driver_lock:
        driver = driver_factory.create_driver()

    driver.get(url)
    print(url)
    try:
        entity = driver.find_element(By.CLASS_NAME, "entity")

        # 店名
        try:
            name = entity.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            name = ""

        # 郵便番号 & 住所
        try:
            address_text = entity.find_element(By.TAG_NAME, "address").text.strip()
            zipcode, address = address_text.split(" ", 1)
        except:
            zipcode, address = "", ""

        # 営業時間（曜日ごとまとめて1セル）
        try:
            raw_hours = entity.find_element(
                By.XPATH, ".//th[contains(text(),'営業時間')]/following-sibling::td"
            ).get_attribute("innerText").strip()
            business_hours = raw_hours.replace("\n", " / ")

            # 計算営業時間（最も長い時間帯の文字列を選ぶ）
            max_hours = 0
            longest_time = ""
            for line in raw_hours.split("\n"):
                parsed = parse_hours(line)
                if parsed:
                    h, t = parsed
                    if h > max_hours:
                        max_hours = h
                        longest_time = t
            calc_hours = longest_time
        except:
            business_hours = ""
            calc_hours = ""

        # 定休日
        try:
            holiday = driver.find_element(
            By.XPATH,"//table[@id='drugStore']//th[normalize-space()='定休日']/following::td[1]"
            ).text.strip()
        except:
            holiday = ""

        # 電話番号
        try:
            tel = entity.find_element(
                By.XPATH, ".//th[contains(text(),'電話番号')]/following::td[1]//a"
            ).text.strip()
        except:
            tel = ""

        # 調剤薬局判定
        try:
            if entity.find_elements(By.XPATH, ".//caption[contains(text(),'調剤薬局')]"):
                pharmacy = "調剤薬局"
            else:
                pharmacy = ""
        except:
            pharmacy = ""

        # 駐車場
        try:
            parking = driver.find_element(
                By.XPATH,
                "//table[caption[normalize-space()='施設・サービス']]//th[normalize-space()='施設']/following::td[1]"
            ).text.strip()
        except :
            parking = "なし"

        # 取扱商品テーブルを取得
        products_table = driver.find_element(By.XPATH, "//table[caption[text()='取扱商品']]")

        # td要素のテキストをすべて取得
        td_texts = [td.text for td in products_table.find_elements(By.TAG_NAME, "td")]

        # "たばこ"が含まれているか判定
        has_tobacco = any("たばこ" in text for text in td_texts)

        return [url, name, zipcode, address, business_hours, holiday, tel, pharmacy, calc_hours, parking, has_tobacco]
    except Exception as e:
        logger.error(f"Error fetching info from {url}: {e}")
        return [url, "失敗","失敗","失敗","失敗","失敗","失敗","失敗","失敗","失敗","失敗"]

    finally:
        driver.quit()

def getget_parallel(urls):
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{const.out_dir}{const.dra_filename.replace('.csv', '')}_{current_time}.csv"
    filename=new_filename
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '店名', '郵便番号', '住所', '営業時間', '定休日', '電話番号', '調剤薬局','計算時間','駐車場','たばこ'])

        with ThreadPoolExecutor(max_workers=10) as executor: 
            futures = [executor.submit(fetch_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    getget_parallel(draconst.tabakourls)
        
