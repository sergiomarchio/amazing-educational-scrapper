from datetime import datetime
from pathlib import Path

from config import config


def save_log(content):
    if config['debug']:
        log_dir = config['log_dir']
        Path(log_dir).mkdir(exist_ok=True)

        filename = Path(log_dir, f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        with open(str(filename), 'w', encoding="utf-8") as f:
            print("Saving")
            f.write(content)

        print(f"Saved log file {filename}")
        print()
