from songapi import netease, kugou
import logging

logger = logging.getLogger(__name__)


def search_content(title, artist, album):
    api_list = {
        "kugou": kugou,
        "netease": netease
    }
    for name, func in api_list.items():
        try:
            result = func.search(title, artist, album)
        except Exception as e:
            logger.info(f"{name} requests failed with error", str(e))
            result = None
        if result:
            return result
    return None
