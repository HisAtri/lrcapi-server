import base64
from flask import Flask, request, abort, redirect, send_from_directory
import os, sys
import requests
from urllib.parse import unquote_plus
from flask_caching import Cache
import argparse
from waitress import serve
import logging

from pack import connectsql


# Warning检查器
class WarningHandler(logging.Handler):
    def emit(self, record):
        if record.levelno == logging.WARNING and "Task queue depth is 2" in record.message:
            # 结束进程
            sys.exit()


# 检查数据库
conn_f = connectsql.connect_to_database()
connectsql.check_database_structure(conn_f)
conn_f.close()

# 创建一个解析器
parser = argparse.ArgumentParser(description="启动LRCAPI服务器")
# 添加一个 `--port` 参数，默认值28883
parser.add_argument('--port', type=int, default=28883, help='应用的运行端口，默认28883')
parser.add_argument('--auth', type=str, help='用于验证Header.Authentication字段，建议纯ASCII字符')
args = parser.parse_args()
# 赋值到token，启动参数优先性最高，其次环境变量，如果都未定义则赋值为false
token = args.auth if args.auth is not None else os.environ.get('API_AUTH', False)

app = Flask(__name__)

app.config['CACHE_TYPE'] = 'filesystem'  # 使用文件系统缓存
app.config['CACHE_DIR'] = './flask_cache'  # 缓存的目录
cache = Cache(app)


# 鉴权函数，在token存在的情况下，对请求进行鉴权
def require_auth():
    if token is not False:
        auth_header = request.headers.get('Authorization', False) or request.headers.get('Authentication', False)
        if auth_header and auth_header == token:
            return
        else:
            abort(403)


def read_file_with_encoding(file_path, encodings):
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return None


# 在key索引中进行搜索
# 搜索次序为关键词搜索主表-关键词搜索副表hash查主表-API搜索后写入
def sql_key_search(song_name, singer_name, album_name):
    conn_r = connectsql.connect_to_database()
    cursor = conn_r.cursor()
    # 从主表查询
    query = "SELECT lyrics FROM api_key WHERE song_name = %s AND singer_name = %s AND album_name = %s"
    values = (song_name, singer_name, album_name)
    cursor.execute(query, values)
    result = cursor.fetchone()
    cursor.close()
    if result:
        conn_r.close()
        # 找到对应的lyrics了，结束，返回
        lyrics = result[0]
        return lyrics
    else:
        # 未找到对应的歌词，保持连接，尝试使用search表查询
        cursor = conn_r.cursor()
        query = "SELECT hash FROM search WHERE song_name = %s AND singer_name = %s AND album_name = %s"
        values = (song_name, singer_name, album_name)
        cursor.execute(query, values)
        result_hash = cursor.fetchone()
        if result_hash:
            hash = result_hash[0]
            s_query = f"SELECT lyrics FROM api_key WHERE hash = %s"
            s_value = (hash,)
            cursor.execute(s_query, s_value)
            result_lrc = cursor.fetchone()
            cursor.close()
            conn_r.close()
            if result_lrc:
                return result_lrc[0]
            else:
                return ""
        cursor.close()
        conn_r.close()
        app.logger.info("No matching record found.")


# 通过网络接口搜索
@cache.memoize(timeout=36000)
def get_lyrics_from_net(title, artist, album, r):
    if title is None and artist is None:
        return None
    title = "" if title is None else title
    artist = "" if artist is None else artist
    album = "" if album is None else album
    if r:
        searcher = title + " " + artist
    else:
        searcher = title

    # 从数据库查询
    sql_search = sql_key_search(title, artist, album)
    if sql_search:
        sql_lrc = base64.b64decode(sql_search).decode('utf-8')
        return "[from:LrcAPI/db]\n" + sql_lrc
    else:
        # 使用歌曲名和作者名查询歌曲
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36', }
        # 第一层Json，要求获得Hash值
        response = requests.get(
            f'http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword={searcher}&page=1&pagesize=2&showtype=1',
            headers=headers)
        if response.status_code == 200:
            song_info = response.json()
            try:
                songhash = song_info["data"]["info"][0]["hash"]
                songname = song_info["data"]["info"][0]["songname"]
                singername = song_info["data"]["info"][0].get("singername", "")
                album_name = song_info["data"]["info"][0].get("album_name", "")
            except:
                return None

            # 第二层Json，要求获取歌词ID和AccessKey
            response2 = requests.get(
                f"https://krcs.kugou.com/search?ver=1&man=yes&client=mobi&keyword=&duration=&hash={songhash}&album_audio_id=",
                headers=headers)
            lyrics_info = response2.json()
            lyrics_id = lyrics_info["candidates"][0]["id"]
            lyrics_key = lyrics_info["candidates"][0]["accesskey"]
            # 第三层Json，要求获得并解码Base64
            response3 = requests.get(
                f"http://lyrics.kugou.com/download?ver=1&client=pc&id={lyrics_id}&accesskey={lyrics_key}&fmt=lrc&charset=utf8",
                headers=headers)
            lyrics_data = response3.json()
            lyrics_encode = lyrics_data["content"]  # 这里是Base64编码的
            lrc_text = base64.b64decode(lyrics_encode).decode('utf-8')  # 这里解码

            conn_t = connectsql.connect_to_database()
            cursor = conn_t.cursor()
            # 检查hash是否存在
            check_hash = f"SELECT * FROM api_key WHERE hash = %s"
            check_value = (songhash,)
            cursor.execute(check_hash, check_value)
            result_hash = cursor.fetchone()
            if not result_hash:
                # hash不存在，将hash插入主表
                sql_insert = "INSERT INTO api_key (song_name, singer_name, album_name, hash, lyrics) VALUES (%s, %s, %s, %s, %s)"
                sql_insert_value = (songname, singername, album_name, songhash, lyrics_encode)
                cursor.execute(sql_insert, sql_insert_value)
            # 检查查询词是否存在
            cursor = conn_t.cursor()
            query = "SELECT hash FROM search WHERE song_name = %s AND singer_name = %s AND album_name = %s"
            values = (title, artist, album)
            cursor.execute(query, values)
            result_hash_check = cursor.fetchone()
            if not result_hash_check:
                # 插入search
                sql_search_insert = "INSERT INTO search (song_name, singer_name, album_name, hash) VALUES (%s, %s, %s, %s)"
                sql_search_insert_value = (title, artist, album, songhash)
                cursor.execute(sql_search_insert, sql_search_insert_value)
            conn_t.commit()
            cursor.close()
            conn_t.close()
            return "[from:LrcAPI/200]\n" + lrc_text

    return None


@app.route('/lyrics', methods=['GET'])
def lyrics():
    require_auth()
    # 通过request参数获取文件路径
    try:
        # 通过request参数获取音乐Tag
        title = unquote_plus(request.args.get('title'))
        artist = unquote_plus(request.args.get('artist'))
        album = unquote_plus(request.args.get('album'))
    except Exception as e:
        app.logger.error("Unable to get song tags." + str(e))
        title, artist, album = None, None, None

    try:
        # 查询外部API
        lyrics_os = get_lyrics_from_net(title, artist, album, True)
        if lyrics_os is None:
            lyrics_os = get_lyrics_from_net(title, artist, album, False)
    except Exception as e:
        app.logger.error("Unable to get lyrics." + str(e))
        lyrics_os = None
    if lyrics_os is not None:
        return lyrics_os

    return "Lyrics not found.", 404


@app.route('/')
def redirect_to_welcome():
    return redirect('/src')


@app.route('/src')
def return_index():
    return send_from_directory('src', 'index.html')


@app.route('/db')
def show_data():
    conn_d = connectsql.connect_to_database()
    cursor = conn_d.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    table_data = {}

    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        record_count = cursor.fetchone()[0]
        table_data[table_name] = record_count
    cursor.close()
    conn_d.close()

    return table_data


@app.route('/src/<path:filename>')
def serve_file(filename):
    try:
        return send_from_directory('src', filename)
    except FileNotFoundError:
        abort(404)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('')
    warning_handler = WarningHandler()
    logger.addHandler(warning_handler)
    serve(app, host='0.0.0.0', port=args.port)
    # app.run(host='0.0.0.0', port=args.port)
