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
このスクリプトは、トレファクの商品情報を自動で取得するためのものです。
主に以下の機能を持っています。 
1. 指定されたURLから商品リンクを取得する。(検索結果1ページに表示される商品数まで)
2. 各商品リンクから詳細情報を取得する。(金額、送料、本人確認、説明文、重さ、星)
3. 重さはGeminiを使用して推測します。
4. 取得した情報をCSVファイルに保存する。
"""

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
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#rightBox > ul > li.p-itemlist_item"))
    )
    
    # 初回リンクの取得
    item_links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "#rightBox > ul > li.p-itemlist_item > a.p-itemlist_btn")]

    # ページの一番下までスクロールして、さらにリンクを取得
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    for _ in range(10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight / 10 * ({_ + 1}));")
        time.sleep(1)  # スクロール後、少し待機してリンクがロードされるのを待つ

    # 再度リンクの取得
    item_links += [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "#rightBox > ul > li.p-itemlist_item > a.p-itemlist_btn")]

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
        priceSelector = ""

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#main > div.gdwrapper > div.gdinner.is-infoculumn > div.gdprice > p.gdprice_main.p-price1_a"))
            )
            priceSelector="#main > div.gdwrapper > div.gdinner.is-infoculumn > div.gdprice > p.gdprice_main.p-price1_a"
        except Exception:
            print(f"金額情報Aの読み込みがタイムアウトしました: {url}")
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#main > div.gdwrapper > div.gdinner.is-infoculumn > div.gdprice > p.gdprice_main.p-price1_b"))
                )
                priceSelector="#main > div.gdwrapper > div.gdinner.is-infoculumn > div.gdprice > p.gdprice_main.p-price1_b"
            except Exception:
                print(f"金額情報Bの読み込みがタイムアウトしました: {url}")
                return (url, '取得失敗', '取得失敗', '取得失敗')

        # 送料
        souryo_elem = driver.find_elements(By.CSS_SELECTOR, "#gddescription > table.gddescription_attr.p-table1_a > tbody > tr:nth-child(4) > td")
        if souryo_elem:
            lines = souryo_elem[0].text.splitlines()
            souryo = lines[0]
        else:
            souryo = "不明"

        # 金額
        price_elements = driver.find_elements(By.CSS_SELECTOR, priceSelector)
        if price_elements:
            kingaku = price_elements[0].text.strip()
        else:
            kingaku = "不明"

        # 詳細情報を取得
        # detail_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(2) > div > div > pre")
        # if detail_elem:
        #     detail = detail_elem[0].text
        #     prompt = (
        #         detail +
        #         "\n この説明から重さを推測して。大体でいいから。わかったら単位はgとして、数字で答えて。"
        #         "500g以下と思われるなら500と答えて。余計な説明はいらない"
        #     )

        #     # 最大3回リトライ
        #     max_retries = 3
        #     for attempt in range(max_retries):
        #         try:
        #             response = gemini_client.generate_content(prompt)
        #             omosa = response
        #             break  # 成功したら抜ける
        #         except Exception as e:
        #             print(f"Gemini リクエスト失敗 ({attempt+1}回目): {e}")
        #             if attempt < max_retries - 1:
        #                 time.sleep(30)  # 少し待ってからリトライ
        #             else:
        #                 omosa = ''  # 最後まで失敗したら None 等で扱う

        # --- 商品詳細テーブルを取得 ---
        detail_rows = driver.find_elements(By.CSS_SELECTOR, ".gddescription_detail tbody tr")

        details = []
        for row in detail_rows:
            th = row.find_element(By.CSS_SELECTOR, "th").text.strip()
            # <br>などを「、」に置換して取得
            td = row.find_element(By.CSS_SELECTOR, "td").get_attribute("innerText").strip().replace("\n", "、")
            details.append(f"{th}：{td}")

        detail_text = "、".join(details)

        # --- サイズテーブルを取得 ---
        size_rows = driver.find_elements(By.CSS_SELECTOR, ".item_size table.tbl_autosize tbody tr")

        sizes = []
        for row in size_rows:
            name = row.find_element(By.CSS_SELECTOR, ".autosize_title").text.strip()
            value = row.find_element(By.CSS_SELECTOR, ".autosize_value").text.strip()
            sizes.append(f"{name}：{value}")

        size_text = "、".join(sizes)

        # --- 両方まとめる ---
        full_text = f"{detail_text}、{size_text}"

        prompt = (
            full_text +
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

        print(f"{url=}, {souryo=}, {kingaku=}, {omosa=}")
        return (kaigyo(url), kaigyo(souryo), kaigyo(kingaku), kaigyo(omosa).strip())

    except Exception as e:
        print(f"エラーが発生しました: {url} - {e}")
        traceback.print_exc()
        return (url, '取得失敗', '取得失敗', '取得失敗')
    finally:
        driver.quit()

def getget_parallel(urls,filename):
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '送料', '金額', '重さ'])

        with ThreadPoolExecutor(max_workers=5) as executor: 
            futures = [executor.submit(fetch_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    search_urls = const.trefac_search_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.trefac_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls = fetch_item_urls(search_url)
#         urls = ["https://www.trefac.jp/store/3078000759546470/c2983278/",
# "https://www.trefac.jp/store/3090056013571541/c2950979/",
# "https://www.trefac.jp/store/3062002146961880/c3107617/",
# "https://www.trefac.jp/store/3024003666152541/c3489031/",
# "https://www.trefac.jp/store/3024003435079541/c3118759/",
# "https://www.trefac.jp/store/1101000451041278/c3261550/",
# "https://www.trefac.jp/store/3039003202217184/c3338646/",
# "https://www.trefac.jp/store/3040003798518271/c2855941/",
# "https://www.trefac.jp/store/2504007064662061/c3082133/",
# "https://www.trefac.jp/store/3024003539371541/c3283254/",
# "https://www.trefac.jp/store/3081000562511452/c2928264/",
# "https://www.trefac.jp/store/3079001506245477/c3450692/",
# "https://www.trefac.jp/store/3054001871777671/c3028487/",
# "https://www.trefac.jp/store/3056002154903463/c3061820/"]
#         print(urls)
        getget_parallel(urls,new_filename)  
