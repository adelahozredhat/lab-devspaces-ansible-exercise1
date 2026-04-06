
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from .commun_test import set_module_args


def common_args():
    set_module_args({
        'username': 'AAAA',
        'password': 'BBBB',
        'url': 'localhost',
        'proxy': '',
        'name': 'lab_test_rh_1',
        'ttss': 'I-SSO-ES-TS-TSBASE-FACTORY'
    })


def common_args_with_hosts():
    set_module_args({
        'username': 'AAAA',
        'password': 'BBBB',
        'url': 'localhost',
        'proxy': '',
        'name': 'lab_test_rh_1',
        'ttss': 'I-SSO-ES-TS-TSBASE-FACTORY',
        'hosts': ['arqopast19.test.es']
    })
