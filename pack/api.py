import base64
import requests
from fake_useragent import UserAgent

ua = UserAgent().chrome


def kugou(searcher):
    headers = {
        'User-Agent': ua, }
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
        return lrc_text, lyrics_encode, songname, singername, album_name


def netease_api(searcher):
    headers = {
        'User-Agent': ua, }
    api_url = "http://127.0.0.1:3373"
    response = requests.get(f"{api_url}/search?keywords={searcher}", headers=headers)
    result = response.json()
    if result == {"result": {"songCount": 0}, "code": 200}:
        return None

    song_name = result["result"]["songs"][0]["name"]
    singer_list = [x["name"] for x in result["result"]["songs"][0]["artists"]]
    singer_name = "&".join(singer_list)
    album_name = result["result"]["songs"][0]["album"]["name"]
    song_id = result["result"]["songs"][0]["id"]
    lyrics_request = requests.get(f"{api_url}/lyric?id={song_id}", headers=headers).json()
    lrc_text = lyrics_request["lrc"]["lyric"]
    lrc_encode = base64.b64encode(lrc_text.encode('utf-8')).decode('utf-8')
    return lrc_text, lrc_encode, song_name, singer_name, album_name


def search_content(title, artist, album):
    search_text = f"{title} {artist} {album}"
    result = kugou(search_text)
    if not result:
        result = netease_api(f"{title} {artist}")
    return result
