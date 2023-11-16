from songapi import netease, kugou


def search_content(title, artist, album):
    result = kugou.search(title, artist, album)
    if not result:
        result = netease.search(title, artist, album)
    return result
