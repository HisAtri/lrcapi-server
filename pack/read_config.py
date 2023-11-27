"""
用于读取配置文件。
如果没有会默认创建。
初始化后其他模块直接import pack.config as cfg
调用cfg.config_data对象
"""
import os
import json
import logging

logger = logging.getLogger(__name__)


class AnyClass:
    def __bool__(self):
        return False

    def __getattr__(self, name):
        return AnyClass()


def load_config():
    config_file = './config/conf.json'

    # 检查目录和文件是否存在，如果不存在则创建
    config_dir = os.path.dirname(config_file)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    if not os.path.exists(config_file):
        logger.info("未找到配置文件，正在创建默认配置")
        # 文件不存在，写入默认配置
        config_default = {
            "db": "MySQL",
            "MySQL": {
                "host": "127.0.0.1",
                "port": 3306,
                "name": "lrc",
                "user": "lrc",
                "password": "password"
            },
            "api": {
                "netease": {
                    "type": "netease_cloudmusic_api",
                    "url": "http://127.0.0.1"
                }
            },
            "fss": {
                "type": "WebDav",
                "WebDav": {
                    "url": "https://web.dav/dav/",
                    "username": "username",
                    "password": "password"
                },
                "Local": {
                    "path": "/disk1/storage/api/"
                }
            }
        }

        with open(config_file, 'w') as f:
            json.dump(config_default, f, indent=4)  # indent格式化为可读性更好的JSON
        return config_default
    else:
        # 文件存在，读取并解析JSON
        with open(config_file, 'r') as f:
            config_r = json.load(f)
        return config_r


class DictWrapper:
    def __init__(self, dictionary):
        self.dictionary = dictionary

    def __getattr__(self, key):
        value = self.dictionary.get(key, AnyClass())
        if isinstance(value, dict):
            return DictWrapper(value)
        else:
            return value


# 全局变量，存储配置信息，可以保证一次初始化后不再重复读取
config = AnyClass()


def initialize():
    global config
    config = DictWrapper(load_config())


def config_load():
    global config
    if config:
        return config
    else:
        initialize()
    return config


cfg = config_load()
