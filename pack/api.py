import base64
import requests


def kugou(searcher):
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
        return lrc_text, lyrics_encode, songname, singername, album_name


def search_content(title, artist, album):
    search_text = title+artist+album
    result = kugou(search_text)
    return result
