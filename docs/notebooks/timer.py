import time


class Timer:
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()
        result = round(self.end_time - self.start_time, 4)
        if result > 0.0:
            print(f"{result} seconds")
        else:
            print("< 10 ms")
