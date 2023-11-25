import base64
import requests
from fake_useragent import UserAgent
from pack import textcompare
from pack.search import write_sql

ua = UserAgent().chrome


def search(title, artist, album, limit=5):
    result_list = []
    headers = {'User-Agent': ua, }
    api_url = "http://127.0.0.1:3373"
    # api_url = "https://ne.eh.cx"
    response = requests.get(f"{api_url}/search?keywords={title} {artist} {album}", headers=headers)
    result = response.json()
    if result == {"result": {"songCount": 0}, "code": 200}:
        return None
    info_list = result["result"]["songs"]
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
