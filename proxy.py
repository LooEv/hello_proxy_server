#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import attr


@attr.s(cmp=False)
class Proxy:
    ip = attr.ib()
    port = attr.ib()
    create_time = attr.ib()
    source = attr.ib()
    state = attr.ib(default=200)
    user = attr.ib(default=None)
    pwd = attr.ib(default=None)
    used_times = attr.ib(default=0)
    expired_time = attr.ib(default=None)
    validate_time = attr.ib(default=None)
    protocol = attr.ib(default='http')
    anonymous = attr.ib(default=False)

    def to_dict(self):
        return self.__dict__

    @property
    def proxy_url(self):
        if self.user:
            return f'{self.protocol}://{self.user}:{self.pwd}@{self.ip}:{self.port}'
        else:
            return f'{self.protocol}://{self.ip}:{self.port}'

    def __hash__(self):
        return hash(self.ip)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.ip == other.ip
        return False
