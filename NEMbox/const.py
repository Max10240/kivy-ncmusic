# encoding: UTF-8
from __future__ import print_function, unicode_literals, division, absolute_import
import os


class Constant(object):
    conf_dir = os.path.join('NEMbox', ".netease-musicbox")
    download_dir = os.path.join(conf_dir, "cached")
    config_path = os.path.join(conf_dir, "config.json")
    storage_path = os.path.join(conf_dir, "database.json")
    user_detail_info = os.path.join(conf_dir, 'user_info.json')
    cookie_path = os.path.join(conf_dir, "cookie")
    log_path = os.path.join(conf_dir, "musicbox.log")
##    cache_path = os.path.join(conf_dir, "nemcache")
