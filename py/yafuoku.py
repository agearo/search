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
    time.sleep(3)

    # ヤフオクはF5でリロードしないと表示されない
    driver.refresh()
    
    # ページが完全に読み込まれるまで待機
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.Product__titleLink"))
    )
    
    # 初回リンクの取得
    # item_links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "ul.Products__items li div.Product__detail h3 a")]
    atags = driver.find_elements(By.CSS_SELECTOR, "a.Product__titleLink")

    # ページの一番下までスクロールして、さらにリンクを取得
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    for _ in range(10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight / 10 * ({_ + 1}));")
        time.sleep(1)  # スクロール後、少し待機してリンクがロードされるのを待つ

    # 再度リンクの取得
    # item_links += [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "ul.Products__items li div.Product__detail h3 a")]
    atags += driver.find_elements(By.CSS_SELECTOR, "a.Product__titleLink")
    atags = list(set(atags))

    links_with_index= []
    for atag in atags:
        url = atag.get_attribute("href")
        index = atag.get_attribute("data-cl_cl_index")
        links_with_index.append((url, int(index)))

    # インデックス順に並び替え
    links_with_index.sort(key=lambda x: x[1])

    # ソートされたURLだけ取得
    print(links_with_index)
    sorted_urls = [link[0] for link in links_with_index]
    sorted_index = [link[1] for link in links_with_index]

    # 重複リンクを削除して返す
    return sorted_urls



def fetch_info(url):
    print('fetch info start' + url)
    driver = driver_factory.create_driver()
    max_retries=3

    for attempt in range(1, max_retries + 1):
        try:
            driver.get(url)
            time.sleep(1)

            # ヤフオクはF5でリロードしないと表示されない
            driver.refresh()

            # 商品名の部分読むまで待つ
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h1.gv-u-fontSize16--_aSkEz8L_OSLLKFaubKB.gv-u-fontWeightBold--sVSx7bUE6MAd26cg9XrB"))
            )

            # 送料無料部分
            try:
                shipping = driver.find_element(By.CSS_SELECTOR, "#itemPostage > div > dl > dd > p").text
            except:
                try:
                    shipping = driver.find_element(By.CSS_SELECTOR, "#itemPostage > div > dl > dd > span").text
                except:
                    shipping = "取得失敗"

            # 金額部分
            try:
                price = driver.find_element(By.CSS_SELECTOR, "span.sc-1f0603b0-2.kxUAXU").text
            except:
                price = "取得失敗"

            # 本人部分
            try:
                elems = driver.find_elements(By.PARTIAL_LINK_TEXT, "本人")
                identity = elems[0].text if elems else "取得失敗"
            except:
                identity = "取得失敗"

            # 星部分
            try:
                stars = driver.find_elements(By.CSS_SELECTOR, "span.sc-7f092fc9-8.DMZbS").text
            except:
                stars = "取得失敗"

            # # 説明部分
            # try:
            #     description = driver.find_element(By.CSS_SELECTOR, "span.sc-43a21b02-0.bgOrgw").text
            # except:
            #     description = "取得失敗"
            description = "取得失敗"

            # try:
            #     response = gemini_client.generate_content(description + "\n この説明から重さを推測して。大体でいいから。わかったら単位はgとして、数字で答えて。500g以下と思われるなら500と答えて。余計な説明はしないで。")
            #     omosa = response
            # except:
            #     omosa = "取得失敗"
            omosa = "取得失敗"

            print(f"{url}, {shipping}, {price},{identity},{stars},{omosa}")
            return (url, shipping, price, identity, description,omosa.strip(),stars)

        except Exception as e:
            print(f"エラーが発生しました: {url} - {e}")
            traceback.print_exc()
            if attempt == max_retries:
                return (url, '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
            else:
                time.sleep(3)  # 少し待ってからリトライする
        finally:
            driver.quit()

def fetch_paypay_info(url):
    print('paypay info fetch start' + url)
    driver = driver_factory.create_driver()
    max_retries=3

    for attempt in range(1, max_retries + 1):
        try:
            driver.get(url)
            time.sleep(1)

            # ヤフオクはF5でリロードしないと表示されない
            driver.refresh()

            # 商品名の部分読むまで待つ
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.sc-43a21b02-0.gHRTcR"))
            )

            # 送料無料部分
            try:
                shipping = driver.find_element(By.CSS_SELECTOR, "span.sc-548d96fb-18.kwkwJH.ItemDetail__ShippingFreeLabel").text
            except:
                shipping = "取得失敗"

            # 金額部分
            try:
                price = driver.find_element(By.CSS_SELECTOR, ".sc-43a21b02-0.lfSzHD").text
            except:
                price = "取得失敗"

            # 本人部分
            try:
                elems = driver.find_elements(By.PARTIAL_LINK_TEXT, "本人確認済")
                identity = "本人確認済" if elems else "取得失敗"
            except:
                identity = "取得失敗"

            # 星部分
            try:
                stars = driver.find_elements(By.CSS_SELECTOR, "span.sc-7f092fc9-8.DMZbS").text
            except:
                stars = "取得失敗"

            # # 説明部分
            try:
                description = driver.find_element(By.CSS_SELECTOR, "span.sc-43a21b02-0.jkBqum").text
            except:
                description = "取得失敗"
            # print(description)

            try:
                response = gemini_client.generate_content(description + "\n この説明から重さを推測して。大体でいいから。わかったら単位はgとして、数字で答えて。500g以下と思われるなら500と答えて。余計な説明はしないで。")
                omosa = response
            except:
                omosa = "取得失敗"
            # print(omosa)

            print(f"{url}, {shipping}, {price},{identity},{stars},{omosa}")
            return (url, shipping, price, identity, description,omosa.strip(),stars)

        except Exception as e:
            print(f"エラーが発生しました: {url} - {e}")
            traceback.print_exc()
            if attempt == max_retries:
                return (url, '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗', '取得失敗')
            else:
                time.sleep(3)  # 少し待ってからリトライする
        finally:
            driver.quit()


def getget_parallel(urls,filename):
    with open(filename, 'w', newline='', encoding='cp932',errors="ignore") as f:
        writer = csv.writer(f)
        writer.writerow(['URL', '送料', '金額', '本人', '説明', '重さ', '星'])

        # 10個までとる
        with ThreadPoolExecutor(max_workers=5) as executor: 
            # auctionを含む場合はfetch_infoを使う
            # paypayを含む場合はfetch_paypay_infoを使う
            futures = [executor.submit(select_function(url), url) for url in urls]

            for future in as_completed(futures):
                row = future.result()
                with lock:
                    writer.writerow(row)

def select_function(url):
    return fetch_paypay_info if "paypay" in url else fetch_info

# メイン処理
if __name__ == "__main__":
    search_urls = const.yafu_search_urls
    for search_url in search_urls:
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{const.out_dir}{const.yafu_filename.replace('.csv', '')}_{current_time}.csv"
        print(new_filename)
        urls = fetch_item_urls(search_url)
        # urls = ['https://auctions.yahoo.co.jp/jp/auction/j1193476690', 'https://auctions.yahoo.co.jp/jp/auction/c1193474420', 'https://auctions.yahoo.co.jp/jp/auction/d1186056582', 'https://auctions.yahoo.co.jp/jp/auction/s1166979447', 'https://paypayfleamarket.yahoo.co.jp/item/z469805206', 'https://auctions.yahoo.co.jp/jp/auction/l1194148445', 'https://auctions.yahoo.co.jp/jp/auction/t1187442959', 'https://auctions.yahoo.co.jp/jp/auction/v1187237759', 'https://paypayfleamarket.yahoo.co.jp/item/z304155128', 'https://auctions.yahoo.co.jp/jp/auction/x1187377968', 'https://auctions.yahoo.co.jp/jp/auction/1141267104', 'https://auctions.yahoo.co.jp/jp/auction/q1176561086', 'https://auctions.yahoo.co.jp/jp/auction/o1194620635', 'https://paypayfleamarket.yahoo.co.jp/item/z419316780', 'https://auctions.yahoo.co.jp/jp/auction/r1188355129', 'https://auctions.yahoo.co.jp/jp/auction/b1179326899', 'https://paypayfleamarket.yahoo.co.jp/item/z454435884', 'https://auctions.yahoo.co.jp/jp/auction/m1179429723', 'https://paypayfleamarket.yahoo.co.jp/item/z459181300', 'https://paypayfleamarket.yahoo.co.jp/item/z400807772', 'https://auctions.yahoo.co.jp/jp/auction/t1180157601', 'https://paypayfleamarket.yahoo.co.jp/item/z399057462', 'https://auctions.yahoo.co.jp/jp/auction/g1187407374', 'https://auctions.yahoo.co.jp/jp/auction/r1168566889', 'https://auctions.yahoo.co.jp/jp/auction/x783520044', 'https://auctions.yahoo.co.jp/jp/auction/g1180638068', 'https://paypayfleamarket.yahoo.co.jp/item/z368947840', 'https://paypayfleamarket.yahoo.co.jp/item/z434750580', 'https://auctions.yahoo.co.jp/jp/auction/c1172913528', 'https://auctions.yahoo.co.jp/jp/auction/u1187407847', 'https://auctions.yahoo.co.jp/jp/auction/k1194736527', 'https://auctions.yahoo.co.jp/jp/auction/c1193514052', 'https://paypayfleamarket.yahoo.co.jp/item/z368949128', 'https://auctions.yahoo.co.jp/jp/auction/h1013983700', 'https://auctions.yahoo.co.jp/jp/auction/n1160362926', 'https://auctions.yahoo.co.jp/jp/auction/r1194733039', 'https://auctions.yahoo.co.jp/jp/auction/h1160233411', 'https://auctions.yahoo.co.jp/jp/auction/h1156748032', 'https://auctions.yahoo.co.jp/jp/auction/e1178315346', 'https://auctions.yahoo.co.jp/jp/auction/b1129208485', 'https://auctions.yahoo.co.jp/jp/auction/k1129212221', 'https://auctions.yahoo.co.jp/jp/auction/g1187387488', 'https://paypayfleamarket.yahoo.co.jp/item/z323390752', 'https://auctions.yahoo.co.jp/jp/auction/o1134544305', 'https://paypayfleamarket.yahoo.co.jp/item/z454226490', 'https://auctions.yahoo.co.jp/jp/auction/t1142532495', 'https://auctions.yahoo.co.jp/jp/auction/h1176513894', 'https://auctions.yahoo.co.jp/jp/auction/k1178923761', 'https://paypayfleamarket.yahoo.co.jp/item/z249582254', 'https://paypayfleamarket.yahoo.co.jp/item/z201796260', 'https://auctions.yahoo.co.jp/jp/auction/n186594336', 'https://paypayfleamarket.yahoo.co.jp/item/z255433448', 'https://auctions.yahoo.co.jp/jp/auction/q1062439155', 'https://paypayfleamarket.yahoo.co.jp/item/z395076296', 'https://auctions.yahoo.co.jp/jp/auction/v1129560001', 'https://paypayfleamarket.yahoo.co.jp/item/z185282600', 'https://auctions.yahoo.co.jp/jp/auction/d1075424154', 'https://paypayfleamarket.yahoo.co.jp/item/z442884682', 'https://auctions.yahoo.co.jp/jp/auction/w225999861', 'https://auctions.yahoo.co.jp/jp/auction/j1102509408', 'https://auctions.yahoo.co.jp/jp/auction/j1141313408', 'https://auctions.yahoo.co.jp/jp/auction/k1078284349', 'https://auctions.yahoo.co.jp/jp/auction/l689420024', 'https://auctions.yahoo.co.jp/jp/auction/g236397162', 'https://auctions.yahoo.co.jp/jp/auction/c620576836', 'https://auctions.yahoo.co.jp/jp/auction/e209355767', 'https://auctions.yahoo.co.jp/jp/auction/t1103662096', 'https://auctions.yahoo.co.jp/jp/auction/c572597248', 'https://paypayfleamarket.yahoo.co.jp/item/z81026002', 'https://auctions.yahoo.co.jp/jp/auction/w1177535567', 'https://auctions.yahoo.co.jp/jp/auction/h284984330', 'https://auctions.yahoo.co.jp/jp/auction/g1095216396', 'https://auctions.yahoo.co.jp/jp/auction/o1179782485', 'https://auctions.yahoo.co.jp/jp/auction/c1090579849', 'https://auctions.yahoo.co.jp/jp/auction/o455694806', 'https://auctions.yahoo.co.jp/jp/auction/m1174718724', 'https://paypayfleamarket.yahoo.co.jp/item/z448152032', 'https://auctions.yahoo.co.jp/jp/auction/j1017408072', 'https://auctions.yahoo.co.jp/jp/auction/s588650596', 'https://auctions.yahoo.co.jp/jp/auction/q1189021350', 'https://auctions.yahoo.co.jp/jp/auction/t1014826738', 'https://auctions.yahoo.co.jp/jp/auction/n1173079086', 'https://auctions.yahoo.co.jp/jp/auction/r1017699644', 'https://auctions.yahoo.co.jp/jp/auction/w1172804221', 'https://auctions.yahoo.co.jp/jp/auction/t1186527857', 'https://paypayfleamarket.yahoo.co.jp/item/z173692098', 'https://auctions.yahoo.co.jp/jp/auction/n1174762812', 'https://auctions.yahoo.co.jp/jp/auction/m1190625335', 'https://auctions.yahoo.co.jp/jp/auction/h1194232925', 'https://auctions.yahoo.co.jp/jp/auction/w1194475191']
        print(urls)  
        getget_parallel(urls,new_filename)  
