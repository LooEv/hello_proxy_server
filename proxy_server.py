#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import json
import time

from queue import Queue
from collections import defaultdict
from random import shuffle
from aiohttp import web

from hello_proxy_server.utils import get_collector_classes
from hello_proxy_server.utils import calc_str_md5
from hello_proxy_server.validator import Validator
from hello_proxy_server.settings import *

TASK_QUEUE = Queue()
PROXY_DICT = {}  # key: ip, value: proxy object
SPIDER_NAME_PROXY_DICT = {}  # key: spider_name, value: defaultdict(int)[ip:used_times]
SPIDER_NAME_TIME_DICT = {}  # key: spider_name, value: last time when spider use proxy

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(formatter_str))
logging.getLogger().addHandler(stream_handler)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


class WebServer:
    def __init__(self, loop):
        self.app = web.Application(loop=loop)
        self.app.router.add_get('/proxy', self.get_proxy)

    def get_proxy(self, request):
        https = request.query.get('https', 'false')
        anonymous = request.query.get('anonymous', 'true')
        limit = min(10, int(request.query.get('limit', FETCH_PROXY_LIMIT)))
        if 'name' not in request.query:
            raise web.HTTPBadRequest(body="parameter 'name' is required!")
        if ENCRYPT_API:
            if 'token' not in request.query or 'timestamp' not in request.query:
                raise web.HTTPUnauthorized()
            timestamp = self._validate_timestamp(request)
            self._validate_token(request.query['token'], timestamp)
        name = request.query['name']
        try:
            feedback_proxies = json.loads(request.query.get('proxies', "[]"))
        except json.decoder.JSONDecodeError:
            feedback_proxies = []
        proxies = self._choice_proxy(name, https, anonymous, feedback_proxies, limit)
        return web.Response(text='\r\n'.join(proxies))

    @staticmethod
    def _validate_token(token, timestamp):
        if calc_str_md5(SECRET_KEY + str(timestamp)) != token:
            raise web.HTTPUnauthorized()

    @staticmethod
    def _validate_timestamp(request):
        timestamp = request.query['timestamp']
        try:
            timestamp = int(timestamp)
        except (ValueError, TypeError):
            raise web.HTTPUnauthorized()
        if time.time() - timestamp > 5:
            raise web.HTTPUnauthorized()
        return timestamp

    @staticmethod
    def _choice_proxy(name, https, anonymous, feedback_proxies, limit):
        if not SPIDER_NAME_PROXY_DICT.get(name):
            SPIDER_NAME_PROXY_DICT[name] = defaultdict(int)
            for ip in list(PROXY_DICT.keys()):
                SPIDER_NAME_PROXY_DICT[name][ip] = 0
        SPIDER_NAME_TIME_DICT[name] = time.time()
        if https == 'true':
            protocol_list = ['https']
        else:
            protocol_list = ['https', 'http']
        if feedback_proxies:
            for ip in list(SPIDER_NAME_PROXY_DICT[name].keys()):
                if ip in feedback_proxies:
                    logger.warning(f'spider[{name}] removing {ip}')
                    SPIDER_NAME_PROXY_DICT[name].pop(ip, '')
        anonymous = True if anonymous == 'true' else False
        result = []
        proxy_source_count = defaultdict(int)
        ip_list = list(SPIDER_NAME_PROXY_DICT[name].keys())
        shuffle(ip_list)
        for ip in ip_list:
            if len(result) >= limit:
                break
            if ip not in PROXY_DICT:
                continue
            proxy = PROXY_DICT[ip]
            if proxy.protocol in protocol_list and anonymous == proxy.anonymous:
                if SPIDER_NAME_PROXY_DICT[name][ip] > 20:
                    logger.warning(f'spider[{name}] {ip} used_times > 20, remove it!')
                    SPIDER_NAME_PROXY_DICT[name].pop(ip, '')
                else:
                    SPIDER_NAME_PROXY_DICT[name][ip] += 1
                    result.append(f'{proxy.ip}:{proxy.port}')
                    proxy_source_count[proxy.source] += 1
        logger.info(f'succeed to fetch {len(result)} proxies: {dict(proxy_source_count)}')
        return result


async def update_proxy_dict():
    log_msg = 'spider[{}] is offline more than 5 minutes, remove its proxies'
    while 1:
        await asyncio.sleep(20)
        for spider_name in list(SPIDER_NAME_PROXY_DICT.keys()):
            if spider_name not in SPIDER_NAME_TIME_DICT \
                    or time.time() - SPIDER_NAME_TIME_DICT[spider_name] > 60 * 5:
                SPIDER_NAME_TIME_DICT.pop(spider_name, '')
                SPIDER_NAME_PROXY_DICT.pop(spider_name, '')
                logger.warning(log_msg.format(spider_name))
            else:
                logger.info(f'spider[{spider_name}] is using proxy')


async def proxy_server(loop):
    collector_cls_list = get_collector_classes()
    for collector_cls in collector_cls_list:
        collector_inst = collector_cls(TASK_QUEUE)
        loop.create_task(collector_inst.get_proxy())
    validator = Validator(TASK_QUEUE, PROXY_DICT, SPIDER_NAME_PROXY_DICT)
    validate_task = loop.create_task(validator.run())
    web_server = WebServer(loop=loop)
    app_runner = web.AppRunner(web_server.app)
    await app_runner.setup()
    site = web.TCPSite(app_runner, host=SERVER_HOST, port=SERVER_PORT)
    logger.info(f"Serving up app on {SERVER_HOST}:{SERVER_PORT}")
    await site.start()
    loop.create_task(update_proxy_dict())
    await validate_task


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(proxy_server(loop))


if __name__ == '__main__':
    main()
