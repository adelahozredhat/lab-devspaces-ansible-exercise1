#!/usr/bin/env python

from __future__ import absolute_import, division, print_function
__metaclass__ = type

try:
    from requests import RequestException

    class ValidationRequestException(RequestException):
        """
        Exception made for incorrect requests
        """
except ImportError:
    class ValidationRequestException(BaseException):
        pass
