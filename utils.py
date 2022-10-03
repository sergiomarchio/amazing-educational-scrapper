import time

from log import Logger


def nap(seconds=3, activity="continuing"):
    Logger.log(f"Taking a quick nap of {seconds} second{'s' if seconds > 1 else ''} before {activity}...")
    time.sleep(seconds)
