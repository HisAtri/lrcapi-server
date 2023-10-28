import json
import os
import time
import requests
from functools import wraps

_dir = os.getcwd()
json_dir = os.path.join(_dir, "data/index.json")


# 缓存装饰器
def cache_function_result(duration):
    def decorator(func):
        cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (func.__name__, args, frozenset(kwargs.items()))
            # 检查缓存是否存在并且未过期
            if key in cache and time.time() - cache[key][0] < duration:
                return cache[key][1]

            # 调用函数并缓存结果
            result = func(*args, **kwargs)
            cache[key] = (time.time(), result)
            return result
        return wrapper
    return decorator


# 加载JSON
def load_json():
    with open(json_dir, "r+") as json_file:
        data = json.load(json_file)
        return data


# 加载JSON.DATA
def load_data():
    json_d = load_json()
    data = json_d["data"]
    return {int(key): int(value) for key, value in data.items()}


# 写入JSON.DATA
def append_data(data):
    json_d = load_json()
    json_d["data"] = {str(key): int(value) for key, value in data.items()}
    with open(json_dir, "w+") as json_file:
        json.dump(json_d, json_file)


@cache_function_result(duration=600)
def get_github_repo():
    api_url = "https://api.github.com/repos/HisAtri/LrcApi"
    repo_re = requests.get(api_url)
    if repo_re.status_code == 200:
        re_json = repo_re.json()
        repo_info = {
            "stars": re_json["stargazers_count"],
            "forks": re_json["forks_count"]
        }
        return repo_info

