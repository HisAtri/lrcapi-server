import base64
import requests
from fake_useragent import UserAgent
from pack import textcompare

from pack.search import write_sql

ua = UserAgent().chrome


def search(title, artist, album):
    headers = {'User-Agent': ua, }
    result_list = []
    limit = 5
    # 第一层Json，要求获得Hash值
    response = requests.get(
        f'http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword={title} {artist} {album}&page=1&pagesize=2&showtype=1',
        headers=headers)
    if response.status_code == 200:
        song_info = response.json()["data"]["info"]
        if len(song_info) >= 1:
            for song_item in song_info:
                song_name = song_item["songname"]
                singer_name = song_item.get("singername", "")
                song_hash = song_item["hash"]
                album_name = song_item.get("album_name", "")
                title_conform_ratio = textcompare.association(title, song_name)
                artist_conform_ratio = textcompare.association(artist, singer_name)
                # 计算两个指标的几何平均值；区间范围(0,1]
                ratio = (title_conform_ratio * artist_conform_ratio) ** 0.5
                if ratio >= 0.2:
                    response2 = requests.get(
                        f"https://krcs.kugou.com/search?ver=1&man=yes&client=mobi&keyword=&duration=&hash={song_hash}&album_audio_id=",
                        headers=headers)
                    lyrics_info = response2.json()
                    lyrics_id = lyrics_info["candidates"][0]["id"]
                    lyrics_key = lyrics_info["candidates"][0]["accesskey"]
                    # 第三层Json，要求获得并解码Base64
                    response3 = requests.get(
                        f"http://lyrics.kugou.com/download?ver=1&client=pc&id={lyrics_id}&accesskey={lyrics_key}&fmt=lrc&charset=utf8",
                        headers=headers)
                    lyrics_data = response3.json()
                    lyrics_encode = lyrics_data["content"]                          # 这里是Base64编码的数据
                    lrc_text = base64.b64decode(lyrics_encode).decode('utf-8')      # 这里解码
                    write_sql(lyrics_encode, song_name, singer_name, album_name)    # 写入数据库(不传入歌词原文，传入Base64编码)
                    result_list.append({
                        "lrc_text": lrc_text,
                        "lrc_encode": lyrics_encode,
                        "song_name": song_name,
                        "singer_name": singer_name,
                        "album_name": album_name
                    })
                    if len(result_list) > limit:
                        break
        else:
            return None
        return result_list
