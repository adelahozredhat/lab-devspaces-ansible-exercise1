
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest


@pytest.fixture(scope='session', autouse=True)
def setup_and_teardown_package():
    try:
        print("setting up")
        yield
    finally:
        print("setting down")
