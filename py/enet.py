from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import sys
from pathlib import Path
import time
import logging
from webdriver_manager.chrome import ChromeDriverManager
import time
import const
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# プロジェクトルートをsys.pathに追加
sys.path.append(str(Path(__file__).resolve().parent.parent))

from conf.log_config import setup_logging

# ログ設定を読み込み
setup_logging(__file__)
logger = logging.getLogger(__name__)

# Chromeドライバーを自動DL＆設定
logger.info("ドライバーインストールします")

# Serviceオブジェクトを作成
service = Service(const.chrome_driver_path)
driver = webdriver.Chrome(service=service)

# サイトにアクセス
driver.get("https://www.enscsp.com/")

# 適当に5秒待つ（ページ読み込み待ち）
time.sleep(5)

# ログインフォームの入力（例）
username_input = driver.find_element(By.CSS_SELECTOR, "#mount input[type='text']")
password_input = driver.find_element(By.CSS_SELECTOR, "#mount input[type='password']")

username_input.send_keys(const.account)
password_input.send_keys(const.password)

WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "#login_control_2 > span.login_button_css"))
).click()


# 10秒以内に見つかるまで待つ
WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.LINK_TEXT, "最近の電力使用状況"))
).click()

input("Press Enter to close the browser...")
driver.quit()