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

def get_gemini_calc(search_url):
    driver = driver_factory.create_driver()
    driver.get(search_url)

    caption = "#item-cont-re > div.item-caption > p"
    # ページが完全に読み込まれるまで待機
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, caption))
        )
    except Exception as e:
        logger.error(f"Error waiting for elements: {e}")
        return {"url": search_url, "weight": ''}

    # 詳細情報を取得
    try:
        detail_elem = driver.find_elements(By.CSS_SELECTOR, caption)
    except Exception as e:
        return {"url": search_url, "weight": ''}

    if detail_elem:
        detail = detail_elem[0].text
        prompt = (
            detail +
        "\n この説明から重さを推測して。大体でいいから。わかったら単位はgとして、数字で答えて。"
        "500g以下と思われるなら500と答えて。余計な説明はいらない"
    )

    # 最大3回リトライ
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = gemini_client.generate_content(prompt)
            omosa = response
            break  # 成功したら抜ける
        except Exception as e:
            print(f"Gemini リクエスト失敗 ({attempt+1}回目): {e}")
            if attempt < max_retries - 1:
                time.sleep(30)  # 少し待ってからリトライ
            else:
                omosa = ''  # 最後まで失敗したら None 等で扱う
    print(search_url,omosa)

    return {"url": search_url, "weight": omosa}



# メイン処理
if __name__ == "__main__":
    search_urls = const.rakuten_gemini_urls

    with ThreadPoolExecutor(max_workers=10) as executor: 
        futures = [executor.submit(get_gemini_calc, url) for url in search_urls]

    # Future の結果を取り出す
    results = [future.result() for future in futures]

    # まとめて1ファイルに出力
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{const.out_dir}{const.rakuten_filename.replace('.csv', '')}_{current_time}.csv"
    print(new_filename)

    with open(new_filename, "w", newline="", encoding="cp932") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "weight"])
        writer.writeheader()
        writer.writerows(results)  # 辞書のリストなのでOK





