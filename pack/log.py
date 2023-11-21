import threading
import datetime

# 创建锁
lock = threading.Lock()


def write(args: str, code: int):
    # 获取锁
    lock.acquire()
    current_time = datetime.datetime.now()
    time_string = current_time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{time_string} - {args} - {code}"
    try:
        # 打开文件并以追加模式写入日志
        with open("log.txt", "a", encoding="utf-8") as file:
            file.write(message + "\n")
    finally:
        # 释放锁
        lock.release()
