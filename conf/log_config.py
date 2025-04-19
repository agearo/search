import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import sys
import os

def setup_logging(filename='app'):
    log_dir = Path(__file__).resolve().parent.parent / "log"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / (os.path.basename(filename).split('.')[0]+ ".log")

    # ロガーの設定
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 既存のハンドラを消す（再読み込み対策）
    if logger.hasHandlers():
        logger.handlers.clear()

    # フォーマット
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # ファイル出力（ローテーション付き）
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # コンソール出力
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # ハンドラ追加
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
