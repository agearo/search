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

def to_zenkaku(s: str) -> str:
    """数字とハイフンを全角にする"""
    table = str.maketrans("0123456789-", "０１２３４５６７８９－")
    return s.translate(table)

def fetch_info(url):
    with driver_lock:
        driver = driver_factory.create_driver()

    driver.get(url)
    print(url)
    try:
        table = driver.find_element(By.XPATH, "//table[@class='common']")

        # 店舗名
        try:
            name = table.find_element(By.XPATH, ".//th[normalize-space()='店舗名']/following-sibling::td").text.strip()
        except:
            name = ""

        # 郵便番号・住所
        try:
            addr_block = table.find_element(By.XPATH, ".//th[normalize-space()='住所']/following-sibling::td").text.strip()
            # 改行で郵便番号と住所が分かれている
            lines = addr_block.split("\n")
            zipcode = to_zenkaku(lines[0].strip()) if lines else ""
            address = to_zenkaku(lines[1].strip()) if len(lines) > 1 else ""
        except:
            zipcode, address = "", ""

        # 電話番号（代表番号のみ）
        try:
            tel_raw = table.find_element(By.XPATH, ".//th[normalize-space()='代表番号']/following-sibling::td").text.strip()
            tel = tel_raw.split("（")[0].strip()
            tel = to_zenkaku(tel)
        except:
            tel = ""

        # 営業時間
        try:
            hours = table.find_element(By.XPATH, ".//th[normalize-space()='営業時間']/following-sibling::td").text.strip()
            hours = to_zenkaku(hours)
        except:
            hours = ""

        # 駐車場
        try:
            parking_raw = table.find_element(By.XPATH, ".//th[normalize-space()='駐車場']/following-sibling::td").text.strip()
            import re
            m = re.search(r"(\d+)", parking_raw)
            parking = to_zenkaku(m.group(1)) if m else "０"
        except:
            parking = "０"

        # 取扱商品（電子マネー以降を除外）
        try:
            prod_td = table.find_element(By.XPATH, ".//th[contains(text(),'取扱商品')]/following-sibling::td")
            raw_html = prod_td.get_attribute("innerHTML")
            items = [i.strip() for i in re.split(r"<br\s*/?>", raw_html) if i.strip()]
            products = []
            for item in items:
                if "電子マネー" in item:
                    break
                products.append(to_zenkaku(re.sub(r"\s+", "", item)))
            products = ", ".join(products)
        except:
            products = ""

        return [url, name, zipcode, address, tel, hours, parking, products]

    except Exception as e:
        logger.error(f"Error fetching info from {url}: {e}")
        return [url, "失敗","失敗","失敗","失敗","失敗","失敗","失敗"]

    finally:
        driver.quit()

def getget_parallel(urls):
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{const.out_dir}{const.seims_filename.replace('.csv', '')}_{current_time}.csv"
    filename=new_filename
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '店名', '郵便番号', '住所', '電話番号', '営業時間', '駐車場', '取扱商品'])

        with ThreadPoolExecutor(max_workers=10) as executor: 
            futures = [executor.submit(fetch_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    getget_parallel(draconst.seimsconst)
