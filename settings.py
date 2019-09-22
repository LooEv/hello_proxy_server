#!/usr/bin/env python3
# -*- coding: utf-8 -*-


PROXY_COLLECTOR_LIST = [
    'foo',
]

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5124

DEFAULT_FETCH_PROXY_LIMIT = 10
MAX_FETCH_PROXY_LIMIT = 20

# log
formatter_str = '%(asctime)s||%(levelname)s||%(filename)s->%(funcName)s %(lineno)-3d||%(message)s'

IP_CHECKER_API = 'http://api.ipify.org/?format=json'
IP_CHECKER_API_SSL = 'https://api.ipify.org/?format=json'

DEFAULT_CONCURRENT_VALIDATE = 50
