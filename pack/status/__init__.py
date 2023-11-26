import time
import psutil

from datetime import datetime
from collections import deque

import schedule

from pack import wdata, connectsql

data_points = deque(maxlen=24 * 60)  # Assuming data is collected every minute
cache_statistics = deque([0, 1, 2], maxlen=1000)  # 缓存统计的最大长度


def record_data():
    global data_points
    last_bandwidth = None
    while True:
        cpu_percent = psutil.cpu_percent()
        current_bandwidth = psutil.net_io_counters()
        memory = psutil.virtual_memory().percent
        time_str = datetime.now()

        if last_bandwidth is not None:
            delta_bandwidth = {
                's': current_bandwidth.bytes_sent - last_bandwidth.bytes_sent,
                'r': current_bandwidth.bytes_recv - last_bandwidth.bytes_recv
            }
        else:
            delta_bandwidth = {
                's': 0,
                'r': 0
            }

        data_points.append({
            'time': time_str,
            'c': cpu_percent,
            'b': delta_bandwidth,
            'm': memory
        })

        last_bandwidth = current_bandwidth
        time.sleep(60)


def refresh_data():
    # 计算日期差距
    def day_count():
        now_time = int(time.time())
        # 开始时间 2023-10-21 00:00:00 的时间戳
        start_time = 1697817600
        time_diff = now_time - start_time
        date_diff = time_diff // 86400
        return date_diff

    # 修改data
    def _data():
        val = statistics()
        val_s = val["api_key"]
        this_date = day_count()
        data = wdata.load_data()
        data[this_date] = val_s
        wdata.append_data(data)

    schedule.every().day.at("00:00").do(_data)
    schedule.every().minute.do(_data)
    while True:
        schedule.run_pending()
        time.sleep(1)


# 数据库统计
def statistics():
    with connectsql.connect_to_database() as conn_d:
        with conn_d.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_data = {}

            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                record_count = cursor.fetchone()[0]
                table_data[table_name] = record_count

    return table_data


def stat(data):
    global cache_statistics
    cache_statistics.append(data)


def get_data_points():
    return data_points


def get_cache_statistics():
    return cache_statistics
