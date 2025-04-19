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

current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
new_filename = f"{const.out_dir}{const.mercari_filename.replace('.csv', '')}_{current_time}.csv"

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
    souryo = kingaku = ''

    try:
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#item-info > section:nth-child(1) > section:nth-child(2) > div > div > p"))
        )

        souryo_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(1) > section:nth-child(2) > div > div > p")
        if souryo_elem:
            souryo = souryo_elem[0].text

        kingaku_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(1) > section:nth-child(2) > div > div > div > span:nth-child(2)")
        if kingaku_elem:
            kingaku = kingaku_elem[0].text

        honnnin_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(5) > div.sc-b26963ff-0.lhhXf > a > div.merUserObject > div > div.content__a9529387 > div.verificationContainer__a9529387 > div > div.text__fafde459")
        if honnnin_elem:
            honnnin = honnnin_elem[0].text
        else :
            honnnin_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(6) > div.sc-b26963ff-0.lhhXf > a > div.merUserObject > div > div.content__a9529387 > div.verificationContainer__a9529387 > div > div.text__fafde459")
            if honnnin_elem:
                honnnin = honnnin_elem[0].text

        hoshi_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(5) > div.sc-b26963ff-0.lhhXf > a > div.merUserObject > div > div.content__a9529387 > div.merRating > div > div:nth-child(5)")
        if hoshi_elem:
            class_list = hoshi_elem[0].get_attribute("class").split()
            if class_list == ['star__60fe6cce']:
                hoshi="hoshi_5"
            else:
                hoshi="hoshi_4"
        else :
            hoshi_elem = driver.find_elements(By.CSS_SELECTOR, "#item-info > section:nth-child(6) > div.sc-b26963ff-0.lhhXf > a > div.merUserObject > div > div.content__a9529387 > div.merRating > div > div:nth-child(5)")
            if hoshi_elem:
                class_list = hoshi_elem[0].get_attribute("class").split()
                if class_list == ['star__60fe6cce']:
                    hoshi="hoshi_5"
                else:
                    hoshi="hoshi_4"

        detail_elem = driver.find_elements(By.CSS_SELECTOR,"#item-info > section:nth-child(2) > div > div > pre")
        if detail_elem:
            detail = detail_elem[0].text
        response = gemini_client.generate_content(detail + "\n この説明から重さを推測して。大体でいいから。わかったら単位はgとして、数字で答えて。500g以下と思われるなら500と答えて。")
        omosa = response

        print(f"{url=}, {souryo=}, {kingaku=},{omosa=}")
        return (kaigyo(url), kaigyo(souryo), kaigyo(kingaku), kaigyo(honnnin), kaigyo(detail),omosa.strip(),hoshi)

    except Exception as e:
        print(f"エラーが発生しました: {url} - {e}")
        traceback.print_exc()
        return (url, '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
    finally:
        driver.quit()

def getget_parallel(urls):
    with open(new_filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '送料', '金額', '本人', '説明', '重さ', '星'])

        with ThreadPoolExecutor(max_workers=10) as executor: 
            futures = [executor.submit(fetch_info, url) for url in urls[:2]]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    print(sys.argv[1])
    search_url = sys.argv[1]
    urls = fetch_item_urls(search_url)
    print(urls)  
    getget_parallel(urls)  
