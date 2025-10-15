import requests
from bs4 import BeautifulSoup
import os
import re
from util.driver_factory import DriverFactory

URLS = [
"https://dic.pixiv.net/a/%E3%82%BF%E3%83%BC%E3%83%96%E3%83%AB",
"https://dragon-ball-official.com/news/01_1428.html",
"https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q12110914487",
"https://www.reddit.com/r/dbz/comments/173uo1q/is_vegetas_brother_tarble_canon_or_not/?tl=ja",
"https://www.reddit.com/r/dragonball/comments/165swy9/if_you_were_to_bring_vegetas_brother_tarble_into/?tl=ja",
"https://dragonball-plus.net/vegeta-brother/",
"https://dragoncompedia.com/bejitaotoutotaburu/",
"https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q12110914487",
"https://dragoncompedia.com/bejitaotoutotaburu/",
"https://dragonball-plus.net/vegeta-brother/",
"https://dic.pixiv.net/a/%E3%82%BF%E3%83%BC%E3%83%96%E3%83%AB",
"https://www.reddit.com/r/dbz/comments/173uo1q/is_vegetas_brother_tarble_canon_or_not/?tl=ja",
"https://dragonball.fandom.com/ja/wiki/%E3%82%BF%E3%83%BC%E3%83%96%E3%83%AB",
"https://dragon-ball-official.com/news/01_1428.html",
"https://dic.pixiv.net/a/%E3%82%B0%E3%83%AC",
"https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q14122370169",
"https://manga-manga.site/2019/03/31/%E3%83%99%E3%82%B8%E3%83%BC%E3%82%BF%E3%81%AE%E5%BC%9F%E3%83%BB%E3%82%BF%E3%83%BC%E3%83%96%E3%83%AB%E3%81%A8%E3%81%AF%E3%80%90%E5%AB%81%E3%81%AF%E7%95%B0%E6%98%9F%E4%BA%BA%E3%80%91/",
"https://pondya.com/vegeta-otouto-yome-seiyu/",
"https://www.reddit.com/r/dbz/comments/1adm97t/goku_vegeta_and_broly_are_brothers/?tl=ja",
"https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q10157852655",
"https://w.atwiki.jp/brolymad2626/pages/20.html",
"https://dic.pixiv.net/a/%E3%83%96%E3%83%AD%E3%83%AA%E3%83%BC",
"https://dic.pixiv.net/a/%E3%82%BF%E3%83%BC%E3%83%96%E3%83%AB",
"https://www.reddit.com/r/dbz/comments/ow2s4q/oc_billion_dollar_idea_give_tarble_and_gure_a/?tl=ja",
"https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q10164029380"
]

OUTPUT_FILE = "ベジータ　弟.txt"

# 重複を削除
URLS = list(dict.fromkeys(URLS))

# 出力ファイル準備
if not os.path.exists(OUTPUT_FILE):
    open(OUTPUT_FILE, "a", encoding="utf-8").close()

for idx, url in enumerate(URLS, 1):
    try:
        response = requests.get(url, timeout=10)
        response.encoding = response.apparent_encoding  # 文字化け防止
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        # ヘッダー、ナビ、フッターを削除
        for tag in soup.find_all(['header', 'nav', 'footer', 'script', 'style']):
            tag.decompose()

        # 目に見えるテキスト取得
        texts = []
        for element in soup.find_all(text=True):
            text = element.strip()
            if text:
                texts.append(text)

        body_text = "\n".join(texts)

        # 空白整理
        body_text = re.sub(r'\n+', '\n', body_text)
        body_text = re.sub(r'[ \t]+', ' ', body_text)

        # ファイルに追記
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(url + "\n")
            f.write(body_text + "\n\n")

        print(f"[OK] {idx}/{len(URLS)}: {url}")

    except Exception as e:
        print(f"[ERROR] {idx}/{len(URLS)}: {url} -> {e}")

print("完了！")