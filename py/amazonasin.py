import csv
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from util.driver_factory import DriverFactory
import time
import const

# 出力ファイル名の設定
current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
new_filename = f"{const.out_dir}{const.amazon_filename.replace('.csv', '')}_{current_time}.csv"

driver_factory = DriverFactory()

def fetch_item_urls(search_url):
    # ドライバの作成
    driver = driver_factory.create_driver()

    # 検索結果ページを開く
    driver.get(search_url)
    
    # 最初に少し待機してページが完全に読み込まれるのを待つ
    wait = WebDriverWait(driver, 20)
    wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.s-main-slot div.s-result-item"))
    )

    item_links = set()  # 重複を防ぐためsetにする

    # スクロールを繰り返してすべての商品を表示させる
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # 商品リンクを取得
        product_elements = driver.find_elements(By.CSS_SELECTOR, "div.s-main-slot div.s-result-item")
        for product in product_elements:
            try:
                # 商品ページへのリンクを取得
                a_tag = product.find_element(By.CSS_SELECTOR, "a.a-link-normal.s-no-outline")
                href = a_tag.get_attribute("href")
                data_index = product.get_attribute("data-index")
                if href and "/dp/" in href and data_index:
                    # リストに追加 (data-indexでソートするため、タプル形式で保存)
                    item_links.add((int(data_index), href))  # 重複を防ぐためsetを使用
                    # print(f"Found URL: {href} with data-index {data_index}")  # デバッグ用にURLを表示
            except Exception as e:
                pass
                # print(f"Error extracting link: {e}")
        
        # ページを下にスクロールして読み込ませる
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # 少し待機して新しいリンクを読み込ませる

        # スクロール後の高さを取得
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # 高さが変わらなくなったらスクロールを停止
        if new_height == last_height:
            break
        last_height = new_height

    # ドライバを終了
    driver.quit()

    # data-indexで並び替え (若い順に並べ替え)
    item_links = sorted(item_links)  # data-indexが若い順にソートされる

    # URLのみをリストとして返す
    return [url for _, url in item_links]  

def write_urls_to_csv(urls, filename):
    # CSVファイルに書き込む
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # ヘッダーの書き込み
        writer.writerow(["Product URL"])
        # 各URLを行ごとに書き込む
        for url in urls:
            writer.writerow([url])

if __name__ == "__main__":
    # 検索後のURLを引数として渡す
    search_url = "https://www.amazon.co.jp/s?k=playstation5&rh=p_6%3AAN1VRQENFRJN5&__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&crid=2XHWXAIK20BWV&sprefix=playstation%2Caps%2C185&ref=nb_sb_noss_1"
    
    # 商品URLを取得
    urls = fetch_item_urls(search_url)
    
    # URLをCSVに書き込む
    write_urls_to_csv(urls, new_filename)
    print(f"URLs written to {new_filename}")
