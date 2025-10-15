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





import csv
import datetime

# 取得済みのリンク（Bing の &u= 部分）
links = [
    "a1aHR0cHM6Ly9zaG9wLnRzdXJ1aGEtZy5jb20vNDY4Mg",
    "a1aHR0cHM6Ly9tYXAueWFob28uY28uanAvdjMvcGxhY2UvOTBWWHRNcV9uekk",
    "a1aHR0cHM6Ly93d3cuZHJ1Z2VsZXZlbi5jb20vbmV3cy8yMDI0MDIyMl8wMS8",
    "a1aHR0cHM6Ly93d3cuc2h1Zm9vLm5ldC9wbnR3ZWIvc2hvcERldGFpbC8yODc0NTgv",
    "a1aHR0cHM6Ly93d3cuaG9tZW1hdGUtcmVzZWFyY2gtZHJ1Z3N0b3JlLmNvbS9kdGwvMDAwMDAwMDAwMDAwMDA1MjU1MzMv"
]

results = []

for link in links:
    results.append({
        "keyword": "ドラッグイレブン 松岡店",
        "url": link
    })

# CSV 出力
current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
filename = f"tsuruha_{current_time}.csv"

with open(filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["keyword", "url"])
    writer.writeheader()
    writer.writerows(results)
    

print(f"完了！ {filename} に出力されました")





import base64
import csv
import datetime

# 元 CSV
input_filename = "D:\\prj\\ECHO\\tsuruha_20250823005231.csv"
current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
output_filename = f"tsuruha_decoded_{current_time}.csv"

results = []

# CSV 読み込み & デコード
with open(input_filename, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        encoded_url = row["url"]
        if encoded_url.startswith("a1"):
            encoded_url = encoded_url[2:]  # a1 を取り除く
        # Base64 パディング補正
        missing_padding = len(encoded_url) % 4
        if missing_padding != 0:
            encoded_url += "=" * (4 - missing_padding)
        decoded_bytes = base64.b64decode(encoded_url)
        decoded_url = decoded_bytes.decode("utf-8")
        results.append({
            "keyword": row["keyword"],
            "encoded_url": row["url"],
            "decoded_url": decoded_url
        })

# デコード済み CSV 出力
with open(output_filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["keyword", "encoded_url", "decoded_url"])
    writer.writeheader()
    writer.writerows(results)

print(f"完了！ {output_filename} に出力されました")
