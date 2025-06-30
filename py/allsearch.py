import sys
from pathlib import Path
import logging
import const
import threading  
from util.driver_head_factory import DriverFactory
import urllib.parse
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

# キーワード読み込み（例）
filepath = r"D:\prj\ECHO\py\keyword.txt"
with open(filepath, "r", encoding="utf-8") as f:
    keyword_raw = f.readline().strip()

# URLエンコード（半角スペースを%20に）
keyword_encoded = urllib.parse.quote(keyword_raw)

driver = driver_factory.create_driver()

# 最初のサイトを1つ目のタブで開く
first = True
for site in const.ec_prefix.keys():
    url = const.ec_prefix[site] + keyword_encoded + const.ec_suffix.get(site, "")
    if first:
        driver.get(url)
        first = False
    else:
        # 新しいタブで開く
        driver.execute_script(f"window.open('{url}')")

# 処理が終わってもウィンドウを残す
response = gemini_client.generate_content(keyword_raw + "\n この商品の重さを教えて。大体でいい。数字で答えて。余計な説明はいらない。")
print(response)
gemini_client.close()
input("終了するにはEnterキーを押してください")
