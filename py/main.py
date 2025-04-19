import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import logging

# プロジェクトルートをsys.pathに追加
sys.path.append(str(Path(__file__).resolve().parent.parent))

from conf.log_config import setup_logging

# ログ設定を読み込み
setup_logging()
logger = logging.getLogger(__name__)

def show_message():
    result = messagebox.askokcancel("メッセージ", "こんにちは！")
    if result:
        logger.info("ユーザーがOKを押しました。")
    else:
        logger.info("ユーザーがキャンセルを押しました。")

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    show_message()
