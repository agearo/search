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
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#item-grid ul li > div > a"))
    )
    
    # 初回リンクの取得
    item_links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "#item-grid ul li > div > a")]

    # ページの一番下までスクロールして、さらにリンクを取得
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    for _ in range(10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight / 10 * ({_ + 1}));")
        time.sleep(1)  # スクロール後、少し待機してリンクがロードされるのを待つ

    # 再度リンクの取得
    item_links += [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "#item-grid ul li > div > a")]

    # 重複リンクを削除して返す
    return list(set(item_links))

def kaigyo(moji):
    return moji
    # return moji.replace('\n', '').replace('\r', '')

def fetch_info(url):
    driver = driver_factory.create_driver()
    souryo = kingaku = honnnin = detail = hoshi = ''

    try:
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#item-info > section:nth-child(1) > section:nth-child(2) > div > div > p"))
        )

        souryo_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(1) > section:nth-child(2) > div > div > p")
        if souryo_elem:
            souryo = souryo_elem[0].text

        price_elements = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="price"]')
        if price_elements:
            kingaku = price_elements[0].text.strip()
        else:
            # なければ取り消し線の旧価格（セール前など）を探す
            old_price_elements = driver.find_elements(By.CSS_SELECTOR, 'span.number__6b270ca7.strikethrough__6b270ca7')
            if old_price_elements:
                kingaku = old_price_elements[0].text.strip()
            else:
                kingaku = "不明"

        honnnin_elem = driver.find_elements(By.CSS_SELECTOR, "div.text__fafde459")
        if honnnin_elem:
            honnnin = honnnin_elem[0].text.strip()

        mer_rating_elem = driver.find_element(By.CSS_SELECTOR, "div.merRating")
        stars = mer_rating_elem.find_elements(By.CSS_SELECTOR, "div.star__60fe6cce")
        star_count = len(stars)
        hoshi = f"hoshi_{star_count}"


        # 詳細情報を取得
        if gflg==True:
            detail_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(2) > div > div > pre")
            if detail_elem:
                detail = detail_elem[0].text
                prompt = (
                    detail +
                    "\n この説明から重さを推測して。大体でいいから。わかったら単位はgとして、数字で答えて。"
                    "500g以下と思われるなら500と答えて。余計な説明はいらない。"
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
        else:
            omosa='500'
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
    search_urls = const.mer_search_urls
    i=1
    global gemini_client
    global gflg
    gflg=True
    if(gflg==True):
        print("Geminiを使用します")
    else:
        print("Geminiは使用しません")
    for search_url in search_urls:
        if(i>=3):
            i=0
        else:
            i=i+1
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.mercari_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls = fetch_item_urls(search_url)
        print(urls)
        gemini_client = GeminiClient(apikey=i)
        getget_parallel(urls,new_filename)
