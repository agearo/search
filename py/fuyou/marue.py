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
    
    # ページが完全に読み込まれるまで待機
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, '//*[starts-with(@id, "shop_id_")]'))
    )
    
    # 初回リンクの取得
    shops = driver.find_elements(By.XPATH, '//*[starts-with(@id, "shop_id_")]')

    # ページの一番下までスクロールして、さらにリンクを取得
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    for _ in range(10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight / 10 * ({_ + 1}));")
        time.sleep(1)  # スクロール後、少し待機してリンクがロードされるのを待つ
    
    shops += driver.find_elements(By.XPATH, '//*[starts-with(@id, "shop_id_")]')

    hrefs=[]
    shopnames=[]
    for shop in shops:
        try:
            a_tag = shop.find_element(By.CSS_SELECTOR, '.name a') # name クラスの <a> タグを取得
            href = a_tag.get_attribute('href') # リンクを取得
            text = a_tag.text # テキストを取得
            print(f'Text: {text}, Href: {href}')
            hrefs.append(href)
            shopnames.append(text)
        except:
            print("name クラスまたは <a> タグが見つかりませんでした")

    # 重複リンクを削除して返す
    return list(set(hrefs)), list(set(shopnames))

def kaigyo(moji):
    return moji
    # return moji.replace('\n', '').replace('\r', '')

def fetch_shop_info(url):
    try:
        driver = driver_factory.create_driver()
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR,"#w_7_pagetitle_2_1-title-text > h1"))
        )

        # 店名
        try:
            shopname_elem = driver.find_element(By.CSS_SELECTOR, "#w_7_pagetitle_2_1-title-text > h1")
            shopname = shopname_elem.text.strip()
        except Exception:
            shopname = "取得失敗"
        print(shopname)

        # 住所
        try:
            addresselem="#w_7_pagetitle_2_1-title-wrap > div.copper-title-sentence.col-xs-9.col-sm-9 > div.copper-font-normal"
            address = driver.find_element(By.CSS_SELECTOR, addresselem).text
        except Exception:
            address = "取得失敗"
        print(address)

        # 親コンテナを取得
        container = driver.find_element(By.ID, "w_7_detail_4_1-widget-body")

        # 店舗（spot1）の電話
        telnolist = container.find_elements(
            By.XPATH,
            ".//div[contains(@class,'w_7_detail_4_1_column-name-spot1') and contains(.,'電話')]/following-sibling::div[contains(@class,'w_7_detail_4_1_column-value-spot1')][1]"
        )

        # 店舗（spot1）の営業時間
        eigyolist = container.find_elements(
            By.XPATH,
            ".//div[contains(@class,'w_7_detail_4_1_column-name-spot1') and contains(.,'営業時間')]/following-sibling::div[contains(@class,'w_7_detail_4_1_column-value-spot1')][1]"
        )

        telno = ''
        eigyo = ''
        for t in telnolist:
            telno += t.text + '\n'

        for e in eigyolist:
            eigyo += e.text + '\n'

        print(f"{url=}, {shopname=}, {eigyo=}, {telno=}, {address=}, ")

        return (url, shopname, eigyo, telno, address)

    except Exception as e:
        print(f"エラーが発生しました: {url} - {e}")
        traceback.print_exc()
        return (url, '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
    finally:
        driver.quit()

def getget_parallel(urls,filename):
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '店名', '営業時間', '電話番号', '住所'])

        with ThreadPoolExecutor(max_workers=15) as executor: 
            futures = [executor.submit(fetch_shop_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    search_urls = ["aaa"]
    for search_url in search_urls:
        print(search_url)
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.maruefile.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        # urls = fetch_item_urls(search_url)
        urls=["https://store.welcia.co.jp/welcia/spot/detail?code=2870D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2859D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2874D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2840D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2849D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2802D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2813D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2850D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2852D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2842D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2829D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2837D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2872D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2861D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2827D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2860D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2831D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2862D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2808D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2845D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2826D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2814D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2806D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2807D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2809D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2828D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2836D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2843D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2853D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2856D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2858D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2869D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2871D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2873D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2876D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2877D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2878D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2880D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2822D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2867D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2801D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2820D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2821D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2833D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2864D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2865D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2866D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2868D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2875D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2879D&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2892C&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2893C&category=09",
"https://store.welcia.co.jp/welcia/spot/detail?code=2894C&category=09"]
        print(urls)
        getget_parallel(urls, new_filename)
