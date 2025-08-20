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
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#wrap > div.st-main-body > div.st-detail-top > div.st-detail-top-right.delivery > div"))
        )

        # 店名
        try:
            official_elem = driver.find_element(By.CSS_SELECTOR, "span.official")
            official_text = official_elem.text
            h2_elem = official_elem.find_element(By.XPATH, "..")
            full_text = h2_elem.text
            shopname = full_text.replace(official_text, "").strip()
        except Exception:
            shopname = "取得失敗"

        # 営業時間
        try:
            dl_elem = driver.find_element(
                By.XPATH,
                '//div[contains(@class, "st-sales-time")]//dl[dt[text()="本日の営業時間"]]/dd/span'
            )
            eigyo = dl_elem.text
        except Exception:
            eigyo = "取得失敗"

        # 初期化
        telno = address = parking = restday = handleitem = "取得失敗"

        # st-shop-infoから住所・電話番号・駐車場・定休日・取扱い商品を取得
        try:
            dls = driver.find_elements(By.CSS_SELECTOR, '.st-shop-info')
            # 一時格納用
            info_map = {}
            for dl in dls:
                try:
                    dt = dl.find_element(By.TAG_NAME, 'dt').text.strip()
                    dd = dl.find_element(By.TAG_NAME, 'dd').text.strip()
                    info_map[dt] = dd
                except Exception:
                    continue

            telno = info_map.get('電話番号', "取得失敗")
            telno = telno.replace('※電話でお問い合わせの際は「くすりの窓口を見た」とお伝えください。', '').replace('\n', '')  # 電話番号のスペースを削除
            telno = f"'{telno}'" 
            address = info_map.get('住所', "取得失敗")
            parking = info_map.get('駐車場', "取得失敗")
            restday = info_map.get('定休日', "取得失敗")
            handleitem = info_map.get('取扱い商品', "取得失敗")
            janru = info_map.get('ジャンル', "取得失敗")

        except Exception:
            # ここでエラーが出たら全部取得失敗のままに
            pass

        print(f"{url=}, {shopname=}, {eigyo=}, {telno=}, {address=}, {parking=}, {restday=}, {handleitem=}, {janru=}")

        return (url, shopname, eigyo, telno, address, parking, restday, handleitem, janru)

    except Exception as e:
        print(f"エラーが発生しました: {url} - {e}")
        traceback.print_exc()
        return (url, '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
    finally:
        driver.quit()

def getget_parallel(urls,filename):
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '店名', '営業時間', '電話番号', '住所', '駐車場', '定休日','取り扱い商品', 'ジャンル'])

        with ThreadPoolExecutor(max_workers=5) as executor: 
            futures = [executor.submit(fetch_shop_info, url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

# メイン処理
if __name__ == "__main__":
    search_urls = const.kusurinofuku_search_urls
    for search_url in search_urls:
        print(search_url)
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.kusurinofuku_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls, shopnames = fetch_item_urls(search_url)
        print(urls)
        getget_parallel(urls, new_filename)
