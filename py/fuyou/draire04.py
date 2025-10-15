import base64
from urllib.parse import unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import csv
import datetime
from util.driver_factory import DriverFactory
import draconst

# ===== 設定 =====
keywords = draconst.list   # 複数検索OK
output_prefix = "tsuruha_shop"           # 出力ファイル名のプレフィックス

# ===== メイン処理 =====
def main():
    driver = DriverFactory().create_driver()
    results = []

    for kw in keywords:
        print(f"検索中: {kw}")
        driver.delete_all_cookies()  # 前のセッションをリセット
        driver.get(f"https://www.bing.com/search?q={kw}")
        time.sleep(2)

        links = driver.find_elements(By.CSS_SELECTOR, "li.b_algo h2 a")
        for a in links:
            href = a.get_attribute("href")

            decoded_url = None
            if "&u=" in href:  # Bing のエンコード形式
                u_part = href.split("&u=")[1].split("&")[0]
                if u_part.startswith("a1"):  # a1 付き base64
                    encoded_url_body = u_part[2:]
                    padding = len(encoded_url_body) % 4
                    if padding != 0:
                        encoded_url_body += "=" * (4 - padding)
                    try:
                        decoded_url = base64.b64decode(encoded_url_body).decode("utf-8")
                    except Exception:
                        decoded_url = unquote(u_part)
                else:
                    decoded_url = unquote(u_part)
            else:
                decoded_url = href

            print(f"{kw} -> {decoded_url}")

            # shop.tsuruha-g.com だけ抽出
            if "shop.tsuruha-g.com" in decoded_url:
                results.append({"keyword": kw, "url": decoded_url})
                print(f"抽出: {kw}, {decoded_url}")

    driver.quit()

    # ===== CSV 出力 =====
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_file = f"{output_prefix}_{current_time}.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword", "url"])
        writer.writeheader()
        writer.writerows(results)

    print(f"完了！ {output_file} に {len(results)} 件出力されました")

# 実行
if __name__ == "__main__":
    main()
