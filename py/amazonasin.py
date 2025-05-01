import csv
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Chromeドライバーを作成する関数
class ChromeDriverFactory:
    def __init__(self):
        self.options = Options()
        self.options.add_argument("--headless")  # ヘッドレスモード（ブラウザを表示しない）
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")

    def create_driver(self):
        service = Service()
        return webdriver.Chrome(service=service, options=self.options)

# 商品詳細を取得する関数
def fetch_item_details(driver, item_url):
    driver.get(item_url)
    wait = WebDriverWait(driver, 10)

    asin_match = re.search(r'/dp/([A-Z0-9]{10})', item_url)
    asin = asin_match.group(1) if asin_match else ""

    details = {
        "ASIN": asin,
        "Title": "",
        "Description": "",
        "IsUsed": "No",
        "StockOne": "No",
        "URL": item_url
    }

    try:
        title_elem = wait.until(EC.presence_of_element_located((By.ID, "productTitle")))
        details["Title"] = title_elem.text.strip()
    except:
        pass

    try:
        desc_elem = driver.find_element(By.ID, "productDescription")
        details["Description"] = desc_elem.text.strip()
    except:
        try:
            bullets = driver.find_elements(By.CSS_SELECTOR, "#feature-bullets ul li span")
            details["Description"] = "\n".join(b.text.strip() for b in bullets if b.text.strip())
        except:
            pass

    try:
        condition_elems = driver.find_elements(By.ID, "condition")
        if condition_elems:
            condition_text = condition_elems[0].text.lower()
            if "中古" in condition_text or "used" in condition_text:
                details["IsUsed"] = "Yes"
    except:
        pass

    try:
        avail_elems = driver.find_elements(By.ID, "availability")
        if avail_elems:
            avail_text = avail_elems[0].text
            if "残り1点" in avail_text or "Only 1 left" in avail_text:
                details["StockOne"] = "Yes"
    except:
        pass

    return details

# メイン処理
if __name__ == "__main__":
    item_urls = [
    "https://www.amazon.co.jp/%E3%82%BD%E3%83%8B%E3%83%BC%E3%83%BB%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%A9%E3%82%AF%E3%83%86%E3%82%A3%E3%83%96%E3%82%A8%E3%83%B3%E3%82%BF%E3%83%86%E3%82%A4%E3%83%B3%E3%83%A1%E3%83%B3%E3%83%88-PlayStation-5-CFI-2000A01/dp/B0CKYM15RJ/ref=sr_1_1?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&crid=2XHWXAIK20BWV&dib=eyJ2IjoiMSJ9.UJboFd4tPtz19BNAXbBl3cmB_cf5brYiIdwxtcSEIQ_ivcdp-svUdgUxEXH-6ufZT-jISzl_fXDZ1EIiKOM9tZffpYZHSLtOJ1TwkWtriulO8e3IY57gHBBszwEK1CBdMPnoLCUtrUVD1REvG-Mi0Yt5VhJyJhgPFzn-ShWRJPJ2bedeIfh9Qh55lPoQ_E4DC6oo3MRjghGOzaTeLu1HFp0nzUCR_CfyiuSIGmimLe6UZLEJguSRInB8Pq8HFQbX80L9V7HHERW2n5LDNR_HHDkqnv81MZU_iaUFpjuJfdw.rhjjyLamEPhQQJ2eEvIzZY_jtcgL2rsR23cgaK2yRMA&dib_tag=se&keywords=playstation+5&m=AN1VRQENFRJN5&qid=1745145935&refinements=p_6%3AAN1VRQENFRJN5&sprefix=playstation%2Caps%2C185&sr=8-1",
    "https://www.amazon.co.jp/%E3%82%BD%E3%83%8B%E3%83%BC%E3%83%BB%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%A9%E3%82%AF%E3%83%86%E3%82%A3%E3%83%96%E3%82%A8%E3%83%B3%E3%82%BF%E3%83%86%E3%82%A4%E3%83%B3%E3%83%A1%E3%83%B3%E3%83%88-PlayStation-5-%E3%83%87%E3%82%B8%E3%82%BF%E3%83%AB%E3%83%BB%E3%82%A8%E3%83%87%E3%82%A3%E3%82%B7%E3%83%A7%E3%83%B3-CFI-2000B01/dp/B0CKYL9MCP/ref=sr_1_2?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&crid=2XHWXAIK20BWV&dib=eyJ2IjoiMSJ9.UJboFd4tPtz19BNAXbBl3cmB_cf5brYiIdwxtcSEIQ_ivcdp-svUdgUxEXH-6ufZT-jISzl_fXDZ1EIiKOM9tZffpYZHSLtOJ1TwkWtriulO8e3IY57gHBBszwEK1CBdMPnoLCUtrUVD1REvG-Mi0Yt5VhJyJhgPFzn-ShWRJPJ2bedeIfh9Qh55lPoQ_E4DC6oo3MRjghGOzaTeLu1HFp0nzUCR_CfyiuSIGmimLe6UZLEJguSRInB8Pq8HFQbX80L9V7HHERW2n5LDNR_HHDkqnv81MZU_iaUFpjuJfdw.rhjjyLamEPhQQJ2eEvIzZY_jtcgL2rsR23cgaK2yRMA&dib_tag=se&keywords=playstation+5&m=AN1VRQENFRJN5&qid=1745145935&refinements=p_6%3AAN1VRQENFRJN5&sprefix=playstation%2Caps%2C185&sr=8-2",
    "https://www.amazon.co.jp/%E3%82%BD%E3%83%8B%E3%83%BC%E3%83%BB%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%A9%E3%82%AF%E3%83%86%E3%82%A3%E3%83%96%E3%82%A8%E3%83%B3%E3%82%BF%E3%83%86%E3%82%A4%E3%83%B3%E3%83%A1%E3%83%B3%E3%83%88-CFI-7000B01-PlayStation-5-Pro/dp/B0DGT79B1T/ref=sr_1_3?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&crid=2XHWXAIK20BWV&dib=eyJ2IjoiMSJ9.UJboFd4tPtz19BNAXbBl3cmB_cf5brYiIdwxtcSEIQ_ivcdp-svUdgUxEXH-6ufZT-jISzl_fXDZ1EIiKOM9tZffpYZHSLtOJ1TwkWtriulO8e3IY57gHBBszwEK1CBdMPnoLCUtrUVD1REvG-Mi0Yt5VhJyJhgPFzn-ShWRJPJ2bedeIfh9Qh55lPoQ_E4DC6oo3MRjghGOzaTeLu1HFp0nzUCR_CfyiuSIGmimLe6UZLEJguSRInB8Pq8HFQbX80L9V7HHERW2n5LDNR_HHDkqnv81MZU_iaUFpjuJfdw.rhjjyLamEPhQQJ2eEvIzZY_jtcgL2rsR23cgaK2yRMA&dib_tag=se&keywords=playstation+5&m=AN1VRQENFRJN5&qid=1745145935&refinements=p_6%3AAN1VRQENFRJN5&sprefix=playstation%2Caps%2C185&sr=8-3",
    "https://www.amazon.co.jp/PlayStation-CFI-2000A01-%E3%80%90Amazon-co-jp%E9%99%90%E5%AE%9A%E3%80%91-%E3%82%AA%E3%83%AA%E3%82%B8%E3%83%8A%E3%83%AB%E5%A3%81%E7%B4%99-%E9%85%8D%E4%BF%A1/dp/B0DLZRT358/ref=sr_1_4?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&crid=2XHWXAIK20BWV&dib=eyJ2IjoiMSJ9.UJboFd4tPtz19BNAXbBl3cmB_cf5brYiIdwxtcSEIQ_ivcdp-svUdgUxEXH-6ufZT-jISzl_fXDZ1EIiKOM9tZffpYZHSLtOJ1TwkWtriulO8e3IY57gHBBszwEK1CBdMPnoLCUtrUVD1REvG-Mi0Yt5VhJyJhgPFzn-ShWRJPJ2bedeIfh9Qh55lPoQ_E4DC6oo3MRjghGOzaTeLu1HFp0nzUCR_CfyiuSIGmimLe6UZLEJguSRInB8Pq8HFQbX80L9V7HHERW2n5LDNR_HHDkqnv81MZU_iaUFpjuJfdw.rhjjyLamEPhQQJ2eEvIzZY_jtcgL2rsR23cgaK2yRMA&dib_tag=se&keywords=playstation+5&m=AN1VRQENFRJN5&qid=1745145935&refinements=p_6%3AAN1VRQENFRJN5&sprefix=playstation%2Caps%2C185&sr=8-4"
        # 必要に応じてURLを追加
    ]

    driver_factory = ChromeDriverFactory()
    driver = driver_factory.create_driver()

    item_details_list = []

    for url in item_urls:
        print(f"処理中: {url}")
        try:
            details = fetch_item_details(driver, url)
            item_details_list.append(details)
        except Exception as e:
            print(f"エラー発生: {e}")
        time.sleep(1.5)

    driver.quit()

    # CSV出力
    with open("item_details.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["ASIN", "Title", "Description", "IsUsed", "StockOne", "URL"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in item_details_list:
            writer.writerow(item)

    print("CSVファイルを出力しました: item_details.csv")
