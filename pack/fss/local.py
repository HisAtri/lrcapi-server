import concurrent.futures
import logging
import os
import threading
import requests
import io
from pathlib import Path
from PIL import Image

from pack.read_config import cfg

logger = logging.getLogger(__name__)
# 读取配置中的根目录
root_ = cfg.fss.Local.path
balance = cfg.fss.Local.balance
balances = balance.split()

if root_:
    root_dir = Path(root_)
else:
    raise ValueError("FSS: root directory is undefined")


# 使用Pillow处理图片，压缩转码为多种分辨率的JPG，返回转码后的列表
def compress(image_data) -> list:
    """
    处理过程中，图片宽度按照以下标准进行调整，图片比例保持不变
    需要完成以下几种尺寸，
    250*px(thumbnail), 500*px(small), 750*px(middle), 1250*px(large)
    jpeg/jpg
    """
    image = Image.open(io.BytesIO(image_data))
    if image.mode != 'RGB':
        image = image.convert('RGB')

    resolutions = [250, 500, 750, 1250]
    content_list = []

    for resolution in resolutions:
        # 计算等比例缩放的高度
        base_width = resolution
        w_percent = (base_width / float(image.size[0]))
        h_size = int((float(image.size[1]) * float(w_percent)))

        # 使用thumbnail方法按照指定分辨率进行缩放
        # 使用新方法 Image.LANCZOS
        img_resized = image.copy()
        img_resized.thumbnail((base_width, h_size), Image.LANCZOS)

        # 将缩放后的图像转为字节流
        img_bytes = io.BytesIO()
        img_resized.save(img_bytes, format='JPEG')
        content_list.append(img_bytes.getvalue())

    return content_list


# 保存文件的方法
def save_file(obj_type, obj_id, filename, content):
    file_path = root_dir / obj_type / obj_id / filename
    if not os.path.exists(file_path):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as file:
            file.write(content)
            logger.info(f"FSS: Successfully saved: {file_path}")
    else:
        logger.info(f"FSS: File exists: {file_path}")


# 请求URL，获取2xx响应的内容
def request(url, timeout=10):
    response = requests.get(url, timeout=timeout)
    if response.status_code < 300:
        return response.content


# 以下是主逻辑部分
def task(url, obj_type, obj_id):
    # 先检查是否存在，写入前也要检查一次防止并发导致问题
    if exist_file(obj_type, obj_id):
        return
    image_content = request(url, timeout=10)
    content_list = compress(image_content)
    filenames = ["thumb.jpg", "small.jpg", "middle.jpg", "large.jpg"]
    content_n = len(content_list)
    for i in range(content_n):
        save_file(obj_type, obj_id, filenames[i], content_list[i])


# 以下是超时管理控制
def run_with_timeout(managed_task, args: tuple, timeout=30):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(managed_task, *args)
        try:
            future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            logger.warning("FSS: local.save_url Thread time out")
            future.cancel()


# 以下是供外部调用的系统解决方案，不阻塞线程
# 因此调试时需要等待的方法
# 以防止主进程结束
def save_url(url: str, obj_type: str, obj_id):
    if any(not x for x in [url, obj_type, obj_id]):
        return
    args = (url, obj_type, obj_id)
    threading.Thread(target=run_with_timeout, args=(task, args, 30)).start()
    # 不阻塞调用之后的逻辑
    return


# 检查是否存在文件，并返回URL或者FALSE
def exist_file(obj_type: str, obj_id):
    file_path = root_dir / obj_type / obj_id
    filenames = ["large.jpg", "middle.jpg", "small.jpg", "thumb.jpg"]
    for filename in filenames:
        file_path_local = file_path / filename
        if os.path.exists(file_path_local):
            urls = []
            for bal_url in balances:
                urls.append(f"{bal_url}/{obj_type}/{obj_id}/{filename}")
            return urls
        return False


if __name__ == "__main__":
    save_url("http://p2.music.126.net/UJyEk9xa1T66zDnS0U8wGA==/109951169061111938.jpg", "ar", "114514")
    # 等待
    input()
