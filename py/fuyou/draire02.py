import base64
import csv
import datetime

# 元 CSV
input_filename = "D:\\prj\\ECHO\\tsuruha_20250823005231.csv"
current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
output_filename = f"tsuruha_decoded_{current_time}.csv"

results = []

# CSV 読み込み & デコード
with open(input_filename, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        encoded_url = row["url"]
        if encoded_url.startswith("a1"):
            encoded_url = encoded_url[2:]  # a1 を取り除く
        # Base64 パディング補正
        missing_padding = len(encoded_url) % 4
        if missing_padding != 0:
            encoded_url += "=" * (4 - missing_padding)
        decoded_bytes = base64.b64decode(encoded_url)
        decoded_url = decoded_bytes.decode("utf-8")
        results.append({
            "keyword": row["keyword"],
            "encoded_url": row["url"],
            "decoded_url": decoded_url
        })

# デコード済み CSV 出力
with open(output_filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["keyword", "encoded_url", "decoded_url"])
    writer.writeheader()
    writer.writerows(results)

print(f"完了！ {output_filename} に出力されました")
