import random
import re
import subprocess

import iso3166

from spoffline.cacher import Cacher
from spoffline.helpers.binaries import Binaries
from spoffline.helpers.enums.protocol import Protocol
from spoffline.helpers.exceptions import HolaProxyException
from spoffline.proxies.default import DefaultProxy


class HolaProxy:
    cache = Cacher('proxies.hola')

    @staticmethod
    def get_countries():
        cached_countries = HolaProxy.cache.get('countries')
        if cached_countries:
            return cached_countries

        p = subprocess.check_output([
            Binaries.get('hola-proxy'),
            '-list-countries'
        ], stderr=subprocess.DEVNULL).decode('utf8')

        countries_list = []

        for code, _ in [c.split('-', maxsplit=1) for c in p.splitlines()]:
            try:
                # TODO: Better way because some countries can be ignored
                country = iso3166.countries.get(code.strip())
            except KeyError:
                continue

            countries_list.append(country)

        HolaProxy.cache.set('countries', countries_list, 3600)

        return countries_list

    @staticmethod
    def get_proxy(location, force_new=False):
        if type(location) != iso3166.Country:
            try:
                location = iso3166.countries.get(location)
            except KeyError:
                raise ValueError('Invalid location')

        if location.alpha2 not in [loc.alpha2 for loc in HolaProxy.get_countries()]:
            raise ValueError(f'{location.name} not available on hola-proxy')

        cached_proxy = HolaProxy.cache.get(f'proxy:{location.alpha2}')
        if cached_proxy and not force_new:
            return cached_proxy

        p = subprocess.check_output([
            Binaries.get('hola-proxy'),
            '-country', location.alpha2,
            '-list-proxies'
        ], stderr=subprocess.STDOUT).decode()

        if 'Transaction error: temporary ban detected.' in p:
            raise HolaProxyException("Hola banned your IP temporarily from it's services.")

        username, password, proxy_authorization = re.search(
            r'Login: (.*)\nPassword: (.*)\nProxy-Authorization: (.*)', p
        ).groups()

        proxy = random.choice([
            DefaultProxy(
                proto=Protocol.HTTP,
                hostname=host,
                port=int(peer),
                username=username,
                password=password,
                location=location
            )
            for host, ip_address, direct, peer, hola, trial, trial_peer, vendor in [
                s.split(',') for s in re.findall(r'(zagent.*)', p)
            ]
        ])

        HolaProxy.cache.set(f'proxy:{location.alpha2}', proxy, 3600)

        return proxy
