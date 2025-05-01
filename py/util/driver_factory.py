# webdriver_factory.py（ファイルを分けてもOK）
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import const

class DriverFactory:
    def __init__(self):
        self.options = self._create_options()

    def _create_options(self):
        prefs = {"profile.managed_default_content_settings.images": 2}
        # prefs = {}
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--log-level=3")
        # options.add_argument("accept-language=ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        options.add_argument("window-size=800x600")
        # options.add_argument("window-size=1920x1080")
        options.add_experimental_option("prefs", prefs)
        return options

    def create_driver(self):
        return webdriver.Chrome(service=Service(const.chrome_driver_path), options=self.options)
