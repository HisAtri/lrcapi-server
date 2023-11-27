from webdav4.client import Client
from pack.read_config import cfg

w_cfg = cfg.fss.WebDav
client = Client(w_cfg.host, auth=(w_cfg.username, w_cfg.password))
