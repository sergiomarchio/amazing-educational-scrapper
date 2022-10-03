import time


def nap(seconds=3, activity="continuing"):
    print(f"Taking a quick nap of {seconds} seconds before {activity}...")
    time.sleep(seconds)
