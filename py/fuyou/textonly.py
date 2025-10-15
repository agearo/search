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
from bs4 import BeautifulSoup

gemini_client = GeminiClient()
driver_factory=DriverFactory()
lock = threading.Lock()

# プロジェクトルートをsys.pathに追加
sys.path.append(str(Path(__file__).resolve().parent.parent))
from conf.log_config import setup_logging

# ログ設定を読み込み
setup_logging(__file__)
logger = logging.getLogger(__name__)
driver = driver_factory.create_driver()

driver.get("https://youtubelib.com/tamura-atsushi")

html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

# script, style を削除
for tag in soup(["script", "style"]):
    tag.extract()

# 改行付きでテキスト抽出
text = soup.get_text(separator="\n", strip=True)

with open('output.txt', 'a', encoding='shift_jis',errors='ignore') as f:
    f.write(text)

driver.quit()
