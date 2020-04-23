#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import inspect
from importlib import import_module
from pkgutil import iter_modules

from hello_proxy_server.collector.base_collector import BaseProxyCollector
from hello_proxy_server.settings import PROXY_COLLECTOR_LIST


def get_collector_classes():
    collector_cls_list = []
    package_path = 'hello_proxy_server.collector'
    package = import_module(package_path)
    for _, sub_path, is_pkg in iter_modules(package.__path__):
        full_path = package_path + '.' + sub_path
        module = import_module(full_path)
        if inspect.ismodule(module):
            for obj in vars(module).values():
                if inspect.isclass(obj) and issubclass(obj, BaseProxyCollector) \
                        and getattr(obj, 'source', None) in PROXY_COLLECTOR_LIST:
                    collector_cls_list.append(obj)
    return collector_cls_list


def calc_str_md5(strings: str, encoding='utf-8'):
    md5_obj = hashlib.md5()
    md5_obj.update(strings.encode(encoding=encoding))
    return md5_obj.hexdigest()
