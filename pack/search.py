from pack import connectsql
import hashlib
import logging
from pack import textcompare

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# hash计算器
def calculate_md5(string):
    # 创建一个 md5 对象
    md5_hash = hashlib.md5()
    # 将字符串转换为字节流并进行 MD5 计算
    md5_hash.update(string.encode('utf-8'))
    # 获取计算结果的十六进制表示，并去掉开头的 "0x"
    md5_hex = md5_hash.hexdigest()
    md5_hex = md5_hex.lstrip("0x")
    return md5_hex


# 将值插入SQL，包括base64编码的歌词文本；歌曲名；歌手名；专辑名
def write_sql(lyrics_encode: str, song_name: str, singer_name: str, album_name: str):
    new = False
    with connectsql.connect_to_database() as conn_t:
        # 使用查询字符串的md5
        song_info = f"title:{song_name}&singer:{singer_name}&album:{album_name}"
        info_hash = calculate_md5(song_info)
        # 检查hash是否存在
        check_hash = "SELECT * FROM api_key WHERE hash = %s"
        check_value = (info_hash,)
        with conn_t.cursor() as cursor:
            cursor.execute(check_hash, check_value)
            result_hash = cursor.fetchone()
            if not result_hash:
                new = True
                # hash不存在，将歌词插入主表
                sql_insert = "INSERT INTO api_key (song_name, singer_name, album_name, hash, lyrics) VALUES (" \
                             "%s, %s, %s, %s, %s) "
                sql_insert_value = (song_name, singer_name, album_name, info_hash, lyrics_encode)
                cursor.execute(sql_insert, sql_insert_value)
        conn_t.commit()
    return new


def in_sql(title="", artist="", album=""):
    info_hash = calculate_md5(f"title:{title}&singer:{artist}&album:{album}")
    print(info_hash)
    check_hash = "SELECT * FROM api_key WHERE hash = %s"
    check_value = (info_hash,)
    with connectsql.connect_to_database() as conn_t:
        with conn_t.cursor() as cursor:
            cursor.execute(check_hash, check_value)
            result_hash = cursor.fetchone()
            if not result_hash:
                return False
            else:
                return True


# 在key索引中进行搜索
# 搜索次序为关键词搜索主表-关键词搜索副表hash查主表-API搜索后写入
def sql_key_search(song_name, singer_name, album_name):
    title_0 = "%" + textcompare.zero_item(song_name) + "%" if song_name else "%"
    singer_0 = "%" + textcompare.zero_item(singer_name) + "%" if singer_name else "%"
    logging.info("从数据库查找")
    with connectsql.connect_to_database() as conn_r:
        with conn_r.cursor() as cursor:
            # 一定程度上缩小查询范围
            query = "SELECT * FROM api_key WHERE song_name LIKE %s AND singer_name LIKE %s"
            values = (title_0, singer_0)
            cursor.execute(query, values)
            result_all = cursor.fetchall()
            if result_all:
                item_list = []
                for item in result_all:
                    item_dict = {
                        "id": item[0],
                        "song_name": item[1],
                        "singer_name": item[2],
                        "album_name": item[3],
                        "lyrics": item[5]
                    }
                    item_title = item_dict["song_name"]
                    item_artist = item_dict["singer_name"]
                    item_album = item_dict["album_name"]
                    ti_ratio = textcompare.association(song_name, item_title)
                    ar_ratio = textcompare.assoc_artists(singer_name, item_artist)
                    al_ratio = textcompare.association(album_name, item_album)
                    conform_ratio = ((ti_ratio * ar_ratio * (0.01 * al_ratio + 0.99)) ** 0.5)
                    # print(song_name, item_title, ti_ratio, singer_name, item_artist, ar_ratio, conform_ratio)
                    if conform_ratio >= 0.3 and ti_ratio > 0.3 and ar_ratio > 0.3:
                        item_list.append({
                            "lyrics": item_dict["lyrics"],
                            "song_name": item_title,
                            "singer_name": item_artist,
                            "ratio": conform_ratio
                        })
                # 以键“ratio”为准，进行排序
                sort_list = sorted(item_list, key=lambda x: 1 - x["ratio"])
                return sort_list
            else:
                logging.info("No matching record found.")
                return ""


def sql_img_search(title: str, artist: str, album: str, mod=0):
    """
        mod->
        0: 歌曲cover
        1：专辑cover
        2：艺术家cover
    """
    title_0 = "%" + textcompare.zero_item(title) + "%" if title else "%"
    singer_0 = "%" + textcompare.zero_item(artist) + "%" if artist else "%"
    album_0 = "%" + textcompare.zero_item(artist) + "%" if artist else "%"
    logging.info("从数据库查找")
    with connectsql.connect_to_database() as conn_r:
        with conn_r.cursor() as cursor:
            match mod:
                case 0:
                    query = "SELECT * FROM api_img WHERE music LIKE %s AND artist LIKE %s"
                    values = (title_0, singer_0)
                case 1:
                    query = "SELECT * FROM api_img WHERE album LIKE %s AND artist LIKE %s"
                    values = (album_0, singer_0)
                case 2:
                    query = "SELECT * FROM api_img WHERE artist LIKE %s"
                    values = (singer_0,)
                case _:
                    raise ValueError("错误的模式，只允许0,1,2")
            cursor.execute(query, values)
            result_all = cursor.fetchall()
    if result_all:
        item_list = []
        for item in result_all:
            item_dict = {
                "id": item[0],
                "music": item[1],
                "artist": item[2],
                "album": item[3],
                "mu_id": item[5],
                "mu_url": item[6],
                "al_id": item[7],
                "al_url": item[8],
                "ar_id": item[9],
                "ar_url": item[10]
            }
            item_title = item_dict["music"]
            item_artist = item_dict["artist"]
            item_album = item_dict["album"]
            match mod:
                # 判断好请求的类型
                # 同时计算相似度
                # key为元组，同时包含ID和URL
                case 0:
                    key = (item_dict["mu_id"], item_dict["mu_url"])
                    ti_ratio = textcompare.association(title, item_title)
                    ar_ratio = textcompare.assoc_artists(artist, item_artist)
                    al_ratio = textcompare.association(album, item_album)
                    conform_ratio = (lambda x: x if x >= 0.3 else 0)((ti_ratio * ar_ratio * (0.01 * al_ratio + 0.99)) ** 0.5)
                case 1:
                    key = (item_dict["al_id"], item_dict["al_url"])
                    ar_ratio = textcompare.assoc_artists(artist, item_artist)
                    al_ratio = textcompare.association(album, item_album)
                    conform_ratio = (lambda x: x if x >= 0.3 else 0)((ar_ratio * (0.01 * al_ratio + 0.99)) ** 0.5)
                case 2:
                    key = (item_dict["ar_id"], item_dict["ar_url"])
                    conform_ratio = (lambda x: x if x >= 0.5 else 0)(textcompare.assoc_artists(artist, item_artist))
                case _:
                    raise ValueError("错误的模式，只允许0,1,2")
            item_list.append({
                "item": key,
                "ratio": conform_ratio
            })
            sort_list = sorted(item_list, key=lambda x: 1 - x["ratio"])
            return sort_list
    else:
        logging.info("No matching record found.")
        return ""


def write_img(title: str, artist: str, album: str, mu_id, mu_url, al_id, al_url, ar_id, ar_url):
    new = False
    with connectsql.connect_to_database() as conn_t:
        # 使用查询字符串的md5
        song_info = f"title:{title}&singer:{artist}&album:{album}"
        info_hash = calculate_md5(song_info)
        # 检查hash是否存在
        check_hash = "SELECT * FROM api_img WHERE hash = %s"
        check_value = (info_hash,)
        with conn_t.cursor() as cursor:
            cursor.execute(check_hash, check_value)
            result_hash = cursor.fetchone()
            # 不存在此内容，插入数据
            if not result_hash:
                new = True
                sql_insert = "INSERT INTO api_img (music, artist, album, hash, mu_id, mu_url, al_id, al_url, ar_id, " \
                             "ar_url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                sql_insert_value = (title, artist, album, info_hash, mu_id, mu_url, al_id, al_url, ar_id, ar_url)
                cursor.execute(sql_insert, sql_insert_value)
        conn_t.commit()
    return new


if __name__ == "__main__":
    print(sql_img_search("", "谢安琪", "", mod=2))
