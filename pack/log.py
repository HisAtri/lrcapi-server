import os
import threading
import datetime
import tarfile


# 创建锁
lock = threading.Lock()


def check_and_compress(file_path):
    # 判断文件体积是否大于1MB
    if os.path.getsize(file_path) > 1024 * 1024:
        # 获取当前时间
        current_time = datetime.datetime.now()
        time_string = current_time.strftime("%Y_%m_%d_%H_%M")

        # 构建压缩文件名
        compressed_filename = f"log/log_{time_string}.tar.gz"

        # 压缩文件
        with tarfile.open(compressed_filename, "w:gz") as tar:
            tar.add(file_path, arcname=os.path.basename(file_path))

        # 删除原始文件
        os.remove(file_path)

    return None


def write(args: str, code: int):
    # 获取锁
    lock.acquire()

    try:
        # 打开文件并以追加模式写入日志
        file_path = "log/log.txt"
        check_and_compress(file_path)

        with open(file_path, "a", encoding="utf-8") as file:
            current_time = datetime.datetime.now()
            time_string = current_time.strftime("%Y-%m-%d %H:%M:%S")
            message = f"{time_string} - {args} - {code}"
            file.write(message + "\n")

    finally:
        # 释放锁
        lock.release()
