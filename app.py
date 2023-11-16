import argparse
import base64
import logging
import os
import schedule
import psutil
import time

from collections import deque
from datetime import datetime
from urllib.parse import unquote_plus

from flask import Flask, request, abort, send_from_directory, jsonify
from waitress import serve
from threading import Thread

from pack import connectsql
from pack import api
from pack import wdata

from pack.search import sql_key_search

# 检查数据库
conn_f = connectsql.connect_to_database()
connectsql.check_database_structure(conn_f)
conn_f.close()

# 创建一个解析器
parser = argparse.ArgumentParser(description="启动LRC-API服务器")
# 添加一个 `--port` 参数，默认值28883
parser.add_argument('--port', type=int, default=28884, help='应用的运行端口，默认28884')
parser.add_argument('--auth', type=str, help='用于验证Header.Authentication字段，建议纯ASCII字符')
args = parser.parse_args()
# 赋值到token，启动参数优先性最高，其次环境变量，如果都未定义则赋值为false
token = args.auth if args.auth is not None else os.environ.get('API_AUTH', False)
data_points = deque(maxlen=24 * 60)  # Assuming data is collected every minute
cache_statistics = deque([0, 1, 2], maxlen=1000)  # 缓存统计的最大长度

app = Flask(__name__)


# Warning检查器
class WarningHandler(logging.Handler):
    def emit(self, record):
        if "queue" in record.message:
            app.logger.warning('正在结束进程')
            # 结束进程
            os._exit(0)


def read_file_with_encoding(file_path, encodings):
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return None


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


def record_data():
    last_bandwidth = None
    while True:
        cpu_percent = psutil.cpu_percent()
        current_bandwidth = psutil.net_io_counters()
        memory = psutil.virtual_memory().percent
        timestamp = datetime.now()

        if last_bandwidth is not None:
            delta_bandwidth = {
                'bytes_sent': current_bandwidth.bytes_sent - last_bandwidth.bytes_sent,
                'bytes_recv': current_bandwidth.bytes_recv - last_bandwidth.bytes_recv
            }
        else:
            delta_bandwidth = {
                'bytes_sent': 0,
                'bytes_recv': 0
            }

        data_points.append({
            'timestamp': timestamp,
            'cpu_percent': cpu_percent,
            'bandwidth': delta_bandwidth,
            'memory': memory
        })

        last_bandwidth = current_bandwidth
        time.sleep(600)


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


# 搜索单个歌词
def get_lyrics(title, artist, album):
    if title is None and artist is None:
        cache_statistics.append(2)
        return None
    title = "" if title is None else title
    artist = "" if artist is None else artist
    album = "" if album is None else album

    # 从数据库查询
    sql_search = sql_key_search(title, artist, album)
    if sql_search:
        lrc_encode = sql_search[0].get("lyrics", "")
        sql_lrc = base64.b64decode(lrc_encode).decode('utf-8')
        cache_statistics.append(1)
        return "[from:LrcAPI/db]\n" + sql_lrc
    else:
        result = api.search_content(title, artist, album)
        if result:
            lrc_text = result[0]["lrc_text"]
            if lrc_text:
                cache_statistics.append(0)
                return "[from:API/200]\n" + lrc_text
    cache_statistics.append(2)
    return None


@app.route('/lyrics', methods=['GET'])
def lyrics():
    logger.info("request from /lyrics")
    if not bool(request.args):
        return "请携带参数访问", 404
    # 通过request参数获取文件路径
    try:
        # 通过request参数获取音乐Tag
        title = unquote_plus(request.args.get('title'))
        artist = unquote_plus(request.args.get('artist', ''))
        album = unquote_plus(request.args.get('album', ''))
        if (not album) or (album == "[Unknown Album]"):
            album = ""
    except Exception as e:
        app.logger.error("Unable to get song tags." + str(e))
        title, artist, album = None, None, None

    #try:
        # 查询外部API与数据库
    lyrics_os = get_lyrics(title, artist, album)
    #except Exception as e:
        #app.logger.error("Unable to get lyrics." + str(e))
        #lyrics_os = None
    if lyrics_os is not None:
        return lyrics_os

    return "未找到匹配的歌词", 404


@app.route('/')
def redirect_to_welcome():
    return send_from_directory('src', 'index.html')


@app.route('/src')
def return_index():
    return send_from_directory('src', 'index.html')


@app.route('/api')
def json_api():
    request_args = request.args.get('get')
    if request_args == "data":
        logger.info("request from /api?data")
        return wdata.load_json()
    elif request_args == "status":
        logger.info("request from /api?status")
        return jsonify(list(data_points))
    elif request_args == "cache_st":
        logger.info("request from /api?cache_st")
        return jsonify(list(cache_statistics))
    abort(403)


@app.route('/db')
def show_data():
    logger.info("request from /db")
    return statistics()


@app.route('/src/<path:filename>')
def serve_file(filename):
    try:
        return send_from_directory('src', filename)
    except FileNotFoundError:
        abort(404)


if __name__ == '__main__':
    # 日志处理
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('')
    warning_handler = WarningHandler()
    logger.addHandler(warning_handler)
    # 添加线程：定时更新JSON
    refresh_task_thread = Thread(target=refresh_data)
    refresh_task_thread.start()
    # 添加线程：获取系统状态
    data_thread = Thread(target=record_data)
    data_thread.start()
    # WSGI 生产环境
    serve(app, host='0.0.0.0', port=args.port, threads=32, channel_timeout=60)
    # Flask 开发调试
    # app.run(host='0.0.0.0', port=args.port)
