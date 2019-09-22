#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import asyncio
from queue import Queue
from collections import defaultdict

from aiohttp import web

from hello_proxy_server.utils import get_collector_classes
from hello_proxy_server.validator import Validator
from hello_proxy_server.settings import *

TASK_QUEUE = Queue()
PROXY_SET = set()

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
        try:
            limit = int(request.query.get('limit', DEFAULT_FETCH_PROXY_LIMIT))
            limit = min(limit, MAX_FETCH_PROXY_LIMIT)
        except ValueError:
            limit = DEFAULT_FETCH_PROXY_LIMIT
        proxies = self._choice_proxy(https, anonymous, limit)
        return web.Response(text='\r\n'.join(proxies))

    @staticmethod
    def _choice_proxy(https, anonymous, limit=DEFAULT_FETCH_PROXY_LIMIT):
        if https == 'true':
            protocol_list = ['https']
        else:
            protocol_list = ['https', 'http']

        anonymous = True if anonymous == 'true' else False
        result = []
        proxy_source_count = defaultdict(int)
        for proxy in sorted(PROXY_SET, key=lambda p: p.used_times):
            if len(result) >= limit:
                break
            if proxy.protocol in protocol_list and anonymous == proxy.anonymous:
                proxy.used_times += 1
                # result.append(proxy.to_dict())
                result.append(f'{proxy.ip}:{proxy.port}')
                proxy_source_count[proxy.source] += 1
        logger.info(f'succeed to fetch {len(result)} proxies: {dict(proxy_source_count)}')
        return result


async def proxy_server(loop):
    collector_cls_list = get_collector_classes()
    for collector_cls in collector_cls_list:
        collector_inst = collector_cls(TASK_QUEUE)
        loop.create_task(collector_inst.get_proxy())
    validator = Validator(TASK_QUEUE, PROXY_SET)
    validate_task = loop.create_task(validator.run())
    web_server = WebServer(loop=loop)
    app_runner = web.AppRunner(web_server.app)
    await app_runner.setup()
    site = web.TCPSite(app_runner, host=SERVER_HOST, port=SERVER_PORT)
    logger.info(f"Serving up app on {SERVER_HOST}:{SERVER_PORT}")
    await site.start()
    await validate_task


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(proxy_server(loop))


if __name__ == '__main__':
    main()
