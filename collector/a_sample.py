#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

from .base_collector import BaseProxyCollector
from hello_proxy_server.proxy import Proxy


class SomeProxyCollector(BaseProxyCollector):
    # if you want to collect these proxies, put this source in settings
    source = 'foo'
    url = 'https://xxxxxxxxxxxxxxxxxxxxxxxxxx'
    fetch_proxy_interval = 10

    async def _get_proxy(self, session, **kwargs):
        try:
            async with session.get(self.url, timeout=self.request_timeout) as response:
                resp: str = await response.text()
                for line in resp.splitlines():
                    line = line.strip()
                    if line and line.replace(':', '').replace('.', '').isdigit():
                        ip, port = line.split(':')
                        proxy = Proxy(ip, port, int(time.time()), self.source,
                                      protocol='https', anonymous=True)
                        self.proxy_queue.put(proxy)
        except Exception:
            self.logger.warning(f'fetching [{self.source}] [{self.url}] failed!')
