#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging

from aiohttp import ClientSession

logger = logging.getLogger('proxy_collector')


class BaseProxyCollector:
    source = 'base'
    fetch_proxy_interval = 10  # default 10 seconds
    request_timeout = 5  # default 5 seconds

    def __init__(self, proxy_queue):
        self.running = True
        self.proxy_queue = proxy_queue
        self.logger = logger

    def stop(self):
        self.running = False

    async def get_proxy(self):
        client_session = ClientSession()
        async with client_session as session:
            while self.running:
                self.logger.info(f'Fetching [{self.source}] proxy ...')
                await self._get_proxy(session)
                await asyncio.sleep(self.fetch_proxy_interval)

    async def _get_proxy(self, session, **kwargs):
        """fetch proxies and assemble everyone to Proxy object"""
        raise NotImplementedError
