import base64
from urllib.parse import unquote
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

keywords = ["ドラッグイレブン 松岡店"]  # 例。必要に応じて追加
results = []

def getURL():
    driver = driver_factory.create_driver()
    
    for kw in keywords:
        print(f"検索中: {kw}")
        driver.get(f"https://www.bing.com/search?q={kw}")
        time.sleep(2)  # 少し待つ

        # 検索結果の各リンクを直接取得
        links = driver.find_elements(By.CSS_SELECTOR, "li.b_algo h2 a")
        for a in links:
            href = a.get_attribute("href")
            print(f"{kw} -> {href}")
            if "shop.tsuruha-g.com" in href:
                results.append({"keyword": kw, "url": href})
                print(f"見つかった: {kw}, {href}")

    # CSVに出力
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{const.out_dir}{const.draire.replace('.csv', '')}_{current_time}.csv"
    with open(new_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword", "url"])
        writer.writeheader()
        writer.writerows(results)

    driver.quit()
    print("完了！")


# メイン処理
if __name__ == "__main__":
    getURL()