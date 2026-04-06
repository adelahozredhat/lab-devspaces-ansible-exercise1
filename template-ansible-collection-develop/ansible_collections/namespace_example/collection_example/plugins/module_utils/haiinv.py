#!/usr/bin/env python

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import warnings
from ansible_collections.namespace_example.collection_example.plugins.module_utils.exceptions import ValidationRequestException

try:
    import requests
    from requests import Request, Response

    class Haiinv:
        """
        Module create connections to Haiinv service
        """
        VERB_GET = "GET"
        VERB_POST = "POST"
        VERB_DELETE = "DELETE"

        def __init__(self, base_url: str, username: str, password: str, proxy: str = None) -> None:
            """
            Init Haiinv module configuration connection
            """
            # requests session
            self.session = requests.Session()
            self.session.auth = requests.auth.HTTPBasicAuth(username, password)

            # request headers
            self.session.headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            self.base_url = base_url

            # proxy settings
            self.proxy = [] if proxy is None else proxy

            warnings.filterwarnings("ignore")

        def get_servers(self, env: str = None, ttss: str = None) -> dict:
            """
            Method to get servers info, is possible filter from env or ttss
            """
            response = self.get_inventory(env, ttss)

            return self.__safe_get(response, 'all', '_meta', 'hostvars')

        def get_inventory(self, env: str = None, ttss: str = None) -> dict:
            """
            Method to get inventories, is possible filter from env or ttss
            """
            request = requests.Request(
                self.VERB_GET,
                url=self.base_url + ttss + env
            )

            return self.__request(request)

        def __request(self, request: Request) -> dict:
            try:
                response = self.session.send(
                    self.session.prepare_request(request),
                    proxies={
                        'http': self.proxy,
                        'https': self.proxy
                    },
                    verify=False
                )
            except IOError as exc:
                raise requests.RequestException("http error: %s" % (str(exc)))

            try:
                json = response.json()
            except ValueError as exc:
                raise requests.RequestException("http error (%s): %s" % (response.status_code, response.text))

            if self.__has_error(response):
                message = "http error (%s): %s" % (response.status_code, response.text)
                if response.status_code == 422:
                    raise ValidationRequestException(message)
                raise requests.RequestException(message)

            return json.get('data')

        @staticmethod
        def __has_error(response: Response) -> bool:
            return response.status_code >= 300 or response.json().get('status') != 'success'

        @staticmethod
        def __safe_get(data: dict, *keys: str):

            for key in keys:
                try:
                    data = data[key]
                except KeyError:
                    return None

            return data

except ImportError:
    class Haiinv:
        pass
