import base64
import logging

import requests
from fake_useragent import UserAgent
from pack import textcompare
from pack.search import write_sql, write_img
from pack.read_config import cfg

ua = UserAgent().chrome
conf = cfg.api.netease
headers = {'User-Agent': ua, }
api_url = conf.url


def info(title, artist, album):
    response = requests.get(f"{api_url}/search?keywords={title} {artist} {album}", headers=headers)
    result = response.json()
    if result == {"result": {"songCount": 0}, "code": 200}:
        return None
    return result["result"]["songs"]


def get_artist_img(ar_id):
    response = requests.get(f"{api_url}/artist/detail?id={ar_id}", headers=headers)
    result = response.json()
    return result["data"]["artist"]["avatar"]


def search(title, artist, album, limit=5):
    result_list = []
    info_list = info(title, artist, album)
    if not info_list:
        return None
    for song_info in info_list:
        song_name = song_info["name"]
        singer_list = [x["name"] for x in song_info["artists"]]
        singer_name = "&".join(singer_list)
        album_name = song_info["album"]["name"]
        song_id = song_info["id"]
        title_conform_ratio = textcompare.association(title, song_name)
        artist_conform_ratio = textcompare.assoc_artists(artist, singer_name)
        # 计算两个指标的几何平均值；区间范围(0,1]
        ratio = (title_conform_ratio * artist_conform_ratio) ** 0.5
        if ratio >= 0.2:
            lyrics_request = requests.get(f"{api_url}/lyric?id={song_id}", headers=headers).json()
            lrc_text = lyrics_request["lrc"]["lyric"]
            lrc_encode = base64.b64encode(lrc_text.encode('utf-8')).decode('utf-8')
            result_list.append({
                "lrc_text": lrc_text,
                "lrc_encode": lrc_encode,
                "song_name": song_name,
                "singer_name": singer_name,
                "album_name": album_name
            })
            write_sql(lrc_encode, song_name, singer_name, album_name)
        if len(result_list) > limit:
            break
    return result_list


def cover(title='', artist='', album='', mod=0, limit=3):
    """
    mod->
    0: 歌曲cover
    1：专辑cover
    2：艺术家cover
    """
    keywords = " ".join([item for item in [title, artist, album] if item])
    response = requests.get(f"{api_url}/cloudsearch?keywords={keywords}", headers=headers)
    result = response.json()
    if result == {"result": {"songCount": 0}, "code": 200}:
        return None
    info_list = result["result"]["songs"]
    if not info_list:
        return None
    result = {
        "url": "",
        "sim": 0.2
    }
    search_r = 0
    for song_info in info_list:
        search_r += 1
        if search_r > limit:
            break
        # 以下是获取歌曲、专辑、歌手封面图链接
        # 网易云接口似乎没有专辑封面和歌曲封面的区别
        song_name = song_info["name"]
        singer_list = [x["name"] for x in song_info["ar"]]
        singer_name = "&".join(singer_list)
        album_name = song_info["al"]["name"]
        song_id = song_info["id"]
        album_id = song_info["al"]["id"]
        album_url = song_url = song_info["al"]["picUrl"]
        artist_name = song_info["ar"][0]["name"]
        artist_id = song_info["ar"][0]["id"]
        artist_url = get_artist_img(artist_id)
        match mod:
            case 0:
                ti_ratio = textcompare.association(title, song_name)
                ar_ratio = textcompare.assoc_artists(artist, singer_name)
                al_ratio = textcompare.association(album, album_name)
                conform_ratio = (ti_ratio * ar_ratio * (0.01 * al_ratio + 0.99)) ** 0.5
                if conform_ratio > result["sim"]:
                    result["url"] = song_url
                    result["sim"] = conform_ratio
            case 1:
                ar_ratio = textcompare.assoc_artists(artist, singer_name)
                al_ratio = textcompare.association(album, album_name)
                conform_ratio = (ar_ratio * (0.01 * al_ratio + 0.99)) ** 0.5
                if conform_ratio > result["sim"]:
                    result["url"] = album_url
                    result["sim"] = conform_ratio
            case 2:
                conform_ratio = textcompare.association(artist, singer_name)
                if conform_ratio > result["sim"]:
                    result["url"] = artist_url
                    result["sim"] = conform_ratio
        # 插入数据库
        try:
            write_img(song_name, artist_name, album_name, song_id, song_url, album_id, album_url, artist_id, artist_url)
        except Exception as e:
            logging.warning(str(e))
    return result["url"]


if __name__ == "__main__":
    cover(artist="谢安琪", mod=2)
