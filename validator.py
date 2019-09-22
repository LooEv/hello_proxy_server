#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import copy
import json
import logging
import requests
import time

import aiohttp

from queue import Queue, Empty as QueueEmptyError

from aiohttp import ClientSession
from hello_proxy_server.proxy import Proxy
from hello_proxy_server.settings import *

__CURRENT_IP__ = None

logger = logging.getLogger(__name__)


def get_current_ip():
    global __CURRENT_IP__
    if __CURRENT_IP__:
        return __CURRENT_IP__
    else:
        r = requests.get(IP_CHECKER_API).json()
        __CURRENT_IP__ = r['ip']
        return __CURRENT_IP__


class Validator:
    def __init__(self, task_queue: Queue, proxy_set: set):
        self.task_queue = task_queue
        self.proxy_set = proxy_set
        self.running = True
        self.client_session = None
        self.time = int(time.time())

    def stop(self):
        self.running = False

    async def run(self):
        self.client_session = self.gen_session()
        async with self.client_session as session:
            while self.running:
                now = int(time.time())
                if now - self.time > 45:
                    for proxy in copy.deepcopy(self.proxy_set):
                        if now - proxy.validate_time > 45:
                            logger.info('re_validate ' + proxy.ip)
                            self.proxy_set.remove(proxy)
                            self.task_queue.put(proxy)
                    self.time = int(time.time())

                if self.task_queue.empty():
                    await asyncio.sleep(2)
                    continue
                proxy_list = []
                for i in range(DEFAULT_CONCURRENT_VALIDATE):
                    try:
                        proxy_list.append(self.task_queue.get_nowait())
                    except QueueEmptyError:
                        break
                task_list = [self.validate_proxy(session, p) for p in proxy_list]
                await asyncio.gather(*task_list)

    @staticmethod
    def gen_session():
        return ClientSession()

    @staticmethod
    def gen_proxy(proxy: Proxy):
        proxy_url = proxy.proxy_url.replace('https', 'http')
        user, pwd = proxy.user, proxy.pwd
        proxy_auth = aiohttp.BasicAuth(user, pwd) if user and pwd else None

        return proxy_url, proxy_auth

    async def validate_proxy(self, session: ClientSession, proxy: Proxy):
        proxy_url, proxy_auth = self.gen_proxy(proxy)
        try:
            async with session.get(IP_CHECKER_API, proxy=proxy_url,
                                   proxy_auth=proxy_auth, timeout=10) as response:
                body = await response.read()
                if response.status == 200:
                    if json.loads(body)['ip'] != get_current_ip():
                        proxy.anonymous = True
                    if proxy.used_times >= 100:  # 防止一个ip长期有效的情况下使用次数无限增长
                        proxy.used_times = 0
                    proxy.validate_time = int(time.time())
                    self.proxy_set.add(proxy)
                    logger.info(f'[{proxy.source}]>{proxy_url} validate successfully')
        except Exception:
            logger.warning(f'[{proxy.source}]>{proxy_url} validate invalidly')
