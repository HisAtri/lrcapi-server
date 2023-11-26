import argparse
import base64
import logging
import os

from urllib.parse import unquote_plus
from flask import Flask, request, abort, send_from_directory, jsonify
from waitress import serve
from threading import Thread

from pack import connectsql, textcompare
from pack import api
from pack import wdata
from pack import log
from pack import status

from pack.search import sql_key_search

from requests.exceptions import ChunkedEncodingError


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


# 搜索单个歌词
def get_lyrics(title, artist, album):
    if title is None and artist is None:
        status.stat(2)
        return None
    title = "" if title is None else title
    artist = "" if artist is None else artist
    album = "" if album is None else album

    # 从数据库查询
    sql_search = sql_key_search(title, artist, album)
    if not sql_search:
        converted_title = textcompare.text_convert(title)
        sql_search = sql_key_search(converted_title, artist, album)
    if sql_search:
        lrc_encode = sql_search[0].get("lyrics", "")
        song_name = sql_search[0].get("song_name", "")
        singer_name = sql_search[0].get("singer_name", "")
        sql_lrc = base64.b64decode(lrc_encode).decode('utf-8')
        status.stat(1)
        return f"[from:LrcAPI/db|{song_name}|{singer_name}]\n" + sql_lrc
    else:
        result = api.search_content(title, artist, album)
        if result:
            lrc_text = result[0]["lrc_text"]
            song_name = result[0].get("song_name", "")
            singer_name = result[0].get("singer_name", "")
            if lrc_text:
                status.stat(0)
                return f"[from:API/200|{song_name}|{singer_name}]\n" + lrc_text
    status.stat(2)
    return None


@app.route('/lyrics', methods=['GET'])
def lyrics():
    logger.info("request from /lyrics")
    query_string = unquote_plus(request.query_string.decode('utf-8'))
    if not query_string:
        log.write("None", 404)
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

    try:
        # 查询外部API与数据库
        lyrics_os = get_lyrics(title, artist, album)
    except ChunkedEncodingError:
        try:
            lyrics_os = get_lyrics(title, artist, album)
        except Exception as e:
            app.logger.error("Unable to get lyrics." + str(e))
            lyrics_os = None
    except Exception as e:
        app.logger.error("Unable to get lyrics." + str(e))
        lyrics_os = None
    if lyrics_os is not None:
        log.write(query_string, 200)
        return lyrics_os
    log.write(query_string, 404)
    return "未找到匹配的歌词", 404


@app.route('/')
def redirect_to_welcome():
    return send_from_directory('src', 'index.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('src', 'img/Logo_Design.svg')


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
        return jsonify(list(status.get_data_points()))
    elif request_args == "cache_st":
        logger.info("request from /api?cache_st")
        return jsonify(list(status.get_cache_statistics()))
    abort(403)


@app.route('/db')
def show_data():
    logger.info("request from /db")
    return status.statistics()


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
    refresh_task_thread = Thread(target=status.refresh_data)
    refresh_task_thread.start()
    # 添加线程：获取系统状态
    data_thread = Thread(target=status.record_data)
    data_thread.start()
    # WSGI 生产环境
    serve(app, host='0.0.0.0', port=args.port, threads=32, channel_timeout=60)
    # Flask 开发调试
    # app.run(host='0.0.0.0', port=args.port)
