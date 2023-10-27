import json
import os

_dir = os.getcwd()
json_dir = os.path.join(_dir, "data/index.json")


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
