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
    print('getdekita')
    # ページが完全に読み込まれるまで待機
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.search_tab div.item-box__text-wrapper p > a"))
    )
    
    # 初回リンクの取得
    item_links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "div.search_tab div.item-box__text-wrapper p > a")]

    # ページの一番下までスクロールして、さらにリンクを取得
    for _ in range(10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight / 10 * ({_ + 1}));")
        time.sleep(1)  # スクロール後、少し待機してリンクがロードされるのを待つ

    # 再度リンクの取得
    item_links += [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "div.search_tab div.item-box__text-wrapper p > a")]

    # 重複リンクを削除して返す
    return list(set(item_links))


def fetch_info(url):
    driver = driver_factory.create_driver()
    souryo = kingaku = ''

    try:
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.item__description.only__pc div.item__description__line-limited span"))
        )

        # 送料
        if "送料込" in driver.page_source:
            souryo = "送料込"
        elif "着払い" in driver.page_source:
            souryo = "着払い"
        else:
            souryo = ""
        print(souryo)


        # 金額  
        kingaku_elem = driver.find_elements(By.CSS_SELECTOR, "span.item__price")
        if kingaku_elem:
            kingaku = kingaku_elem[0].text

        # 本人確認  
        if "本人確認済" in driver.page_source:
            honnnin = "本人確認済"
        elif "ラクマ公式ショップです" in driver.page_source:
            honnnin = "ラクマ公式ショップです"
        else:
            honnnin = "本人確認なし"
        print(honnnin)
        

        # 商品説明
        detail_elem = driver.find_elements(By.CSS_SELECTOR,"div.item__description.only__pc div.item__description__line-limited a span")
        if detail_elem:
            detail = detail_elem[0].get_attribute("textContent")
        # response = gemini_client.generate_content(detail + "\n この説明から重さを推測して。大体でいいから。わかったら単位はgとして、数字で答えて。500g以下と思われるなら500と答えて。")
        # omosa = response

        max_retries = 10
        retry_delay = 5  # 秒

        for attempt in range(max_retries):
            print(len(detail))
            try:
                response = gemini_client.generate_content(
                    detail + "\n この説明から重さを推測して。大体でいいから。わかったら単位はgとして、数字で答えて。500g以下と思われるなら500と答えて。"
                )
                omosa = response
                break  # 成功したらループ抜ける
            except Exception as e:
                print(f"geminiの呼び出しに失敗: {e}。{attempt + 1}回目のリトライを5秒後に実施します...")
                time.sleep(retry_delay)
        else:
            print("最大リトライ回数に達しました。処理を中断します。")
            omosa = ""
        print(f"omosa={omosa.strip()}")

        # 星
        link_honnnin = driver.find_elements(By.CSS_SELECTOR, "div.icon_and_shop_info_and_verifed-badge a")
        print(link_honnnin[0])
        item_links = link_honnnin[0].get_attribute("href")
        driver.get(item_links)
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h2.content-group__title"))
        )
        hoshi = driver.find_elements(By.CSS_SELECTOR, "div.shop_score__score")
        hoshi_score = hoshi[0].text

        print(f"{url=}, {souryo=}, {kingaku=},{omosa=}")
        return (url, souryo, kingaku, honnnin, detail,omosa.strip(),hoshi_score)

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

        with ThreadPoolExecutor(max_workers=1) as executor: 
            futures = [executor.submit(fetch_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    search_urls = const.rak_search_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.rakuma_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls = fetch_item_urls(search_url)
        print(urls)
        getget_parallel(urls,new_filename)  
