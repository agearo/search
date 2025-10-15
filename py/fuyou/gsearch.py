import csv
import datetime
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from util.driver_factory import DriverFactory

# ===== 設定 =====
keywords = ["田村淳 現在 年収"]  # 検索キーワード
output_prefix = "gsearch"         # 出力ファイル名のプレフィックス

# ===== メイン処理 =====
def main():
    driver = DriverFactory().create_driver()
    results = []

    for kw in keywords:
        print(f"検索中: {kw}")
        driver.delete_all_cookies()
        driver.get(f"https://www.google.com/search?q={kw}")
        time.sleep(2)

        # Google検索結果の a タグの href をすべて取得
        links = driver.find_elements(By.TAG_NAME, "a")
        for a in links:
            href = a.get_attribute("href")
            if href and href.startswith("http"):  # 有効なURLのみ
                results.append({"keyword": kw, "url": href})
                print(f"{kw} -> {href}")

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
