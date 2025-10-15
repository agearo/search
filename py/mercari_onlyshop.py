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

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def fetch_item_urls(search_url):
    driver = driver_factory.create_driver()
    driver.get(search_url)

    # 商品リンクが出るまで待つ
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.chakra-link.css-19p30tk"))
    )

    urls = []
    # 全てのリンクを取る
    links = driver.find_elements(By.CSS_SELECTOR, "a.chakra-link.css-19p30tk")
    for link in links:
        # 子要素に soldout-label があるか確認
        soldout = link.find_elements(By.CSS_SELECTOR, "div[data-testid='soldout-label']")
        if soldout:  # リストが空じゃない = soldout
            continue
        urls.append(link.get_attribute("href"))

    return urls



def kaigyo(moji):
    return moji
    # return moji.replace('\n', '').replace('\r', '')

def fetch_info(url):
    driver = driver_factory.create_driver()
    souryo = kingaku = honnnin = detail = hoshi = ''

    try:
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#product-info > section:nth-child(1) > section:nth-child(2) > div > div > span.currency"))
        )

        souryo_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(1) > section:nth-child(2) > div > div > p")
        if souryo_elem:
            souryo = souryo_elem[0].text

        price_elements = driver.find_elements(By.CSS_SELECTOR, '#product-info > section:nth-child(1) > section:nth-child(2) > div > div > span:nth-child(2)')
        kingaku = price_elements[0].text if price_elements else ''

        honnnin='本人確認済み'
        hoshi = "hoshi_5"

        # 詳細情報を取得
        detail_elem = driver.find_elements(By.CSS_SELECTOR, "#product-info > section:nth-child(2) > div.merShowMore.mer-spacing-b-16 > div > pre")
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
        print(f"{url=}, {souryo=}, {kingaku=},{omosa=},{honnnin=},{hoshi=}")
        return (kaigyo(url), kaigyo(souryo), kaigyo(kingaku), kaigyo(honnnin), kaigyo(detail),omosa.strip(),hoshi)

    except Exception as e:
        print(f"エラーが発生しました: {url} - {e}")
        traceback.print_exc()
        return (url, '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
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
    search_urls = const.mer_shop_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.mershop_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls = fetch_item_urls(search_url)
        print(urls)  
        getget_parallel(urls,new_filename)  
