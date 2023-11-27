"""
此模块综合各个歌词搜索API，
单线程次序调用搜索，直到成功即返回。
不负责任何结果筛选和数据库维护。
传入标题、艺术家、专辑参数皆为字符串
接收并返回各个API模块search()方法返回的LRC原始文本字符串
返回值为等价False（None或空str）代表所有API都没有获取到
"""
from pack.api import kugou, netease
from pack import textcompare
import logging

logger = logging.getLogger(__name__)


def search_content(title: str, artist: str, album: str) -> list:
    api_list = {
        "kugou": kugou,
        "netease": netease
    }
    for name, func in api_list.items():
        try:
            result = func.search(title, artist, album)
        except Exception as e:
            logger.info(f"{name} requests failed with error: {str(e)}")
            result = None
        if result:
            logger.info(f"{name} returns the lyrics successfully.")
            return result
        else:
            try:
                result = func.search(textcompare.text_convert(title), artist, album)
            except Exception as e:
                logger.info(f"{name} requests failed with error: {str(e)}")
                result = None
            if result:
                return result

    return []


def search_cover(title: str, artist: str, album: str, mod: int) -> str:
    result = netease.cover(title=title, artist=artist, album=album, mod=mod)
    return result
