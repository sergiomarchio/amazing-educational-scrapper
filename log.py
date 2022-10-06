from datetime import datetime
from pathlib import Path

from config import config


def save_debug(content):
    if config['debug']:
        log_dir = config['debug-dir']
        Path(log_dir).mkdir(exist_ok=True)

        filename = Path(log_dir, f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        with open(str(filename), 'w', encoding="utf-8") as f:
            Logger.log("Saving")
            f.write(content)

        Logger.log(f"Saved debug file {filename}")
        Logger.log()


class Logger:
    filename = config['log-file']

    @staticmethod
    def log(*lines: str):
        with open(Logger.filename, 'a', encoding="utf-8") as f:
            str_lines = "".join([str(line) for line in lines])
            f.write(str_lines + "\n")
            print(str_lines)
