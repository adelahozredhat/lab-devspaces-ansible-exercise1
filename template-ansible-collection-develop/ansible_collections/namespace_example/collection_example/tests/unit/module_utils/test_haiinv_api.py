
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import mock
import pytest
import requests
from requests import Response

from ....plugins.module_utils.haiinv import Haiinv


def get_inventory():
    return {"all": {
        "vars": {
            "ansible_winrm_cert_pem": "/var/lib/awx/connection_keys/winrm/Patower1/Patower1_cert.pem",
            "ansible_winrm_cert_key_pem": "/var/lib/awx/connection_keys/winrm/Patower1/Patower1_key.pem",
            "ansible_winrm_server_cert_validation": "ignore",
            "ansible_winrm_read_timeout_sec": 120,
            "ansible_winrm_transport": "certificate",
            "ansible_ssh_private_key_file": "/var/lib/awx/connection_keys/ssh/Patower1/id_rsa"
        },
        "groups": {
            "I-SSO-ES-TS-TSBASE-FACTORY": {
                "previous": {
                    "ARQOP": {
                        "pre": {
                            "hosts": [
                                "arqopasr16.test.es",
                                "arqopasr19.test.es"
                            ]
                        },
                        "default": {
                            "hosts": [
                                "arqopasr16.test.es",
                                "arqopasr19.test.es"
                            ]
                        }
                    },
                    "PAQFA": {
                        "lab_inv_puppet_rebellion_ruben": {
                            "hosts": [
                                "arqopasr21.test.es",
                                "arqopfst01.test.es"
                            ]
                        },
                        "tst": {
                            "hosts": [
                                "arqopasr21.test.es",
                                "arqopasr29.test.es",
                                "arqopasr31.test.es",
                                "arqopast06.test.glc.es",
                                "arqopast13.test.es",
                                "arqopast15.testpre.glcpre.es",
                                "arqopast17.test.es",
                                "arqopast19.test.es",
                                "arqopast21.testpre.glcpre.es",
                                "arqopast23.testpre.glcpre.es",
                                "arqopast31.test.es",
                                "arqopast41.testpre.glcpre.es",
                                "arqopast43.testpre.glcpre.es",
                                "arqopast55.testpre.glcpre.es",
                                "arqopfst01.test.es",
                                "arqopwst02.test.es",
                                "arqopwst13.test.es",
                                "arqowasr04.testpre.glcpre.es",
                                "arqowast03.testpre.glcpre.es",
                                "arqowast13.testpre.glcpre.es",
                                "arqowast15.testpre.glcpre.es",
                                "arqowast17.testpre.glcpre.es",
                                "arqowast19.testpre.glcpre.es",
                                "arqowast21.testpre.glcpre.es",
                                "arqowast23.testpre.glcpre.es",
                                "paqfaast01.servicios.loc",
                                "paqfaast02.ppmcf.ppgbpi.loc",
                                "paqfaast03.ppscentrais.ppgbpi.loc",
                                "paqfaast04.servicios.loc",
                                "paqfaast05.netgbpi.ext",
                                "paqfaast06.pe.pr.geos.loc",
                                "paqfaast07.test.es",
                                "paqfaast08.scentrais.gbpi.loc",
                                "paqfaast09.test.es",
                                "paqfaast10.test.es",
                                "paqfaast11.scentrais.gbpi.loc",
                                "paqfaast12.test.es",
                                "paqfaast14.scentrais.gbpi.loc",
                                "paqfaast16.scentrais.gbpi.loc",
                                "paqfaast50.test.es",
                                "paqfaast51.test.es",
                                "paqfaast52.test.es",
                                "paqfaast53.test.es",
                                "paqfaast54.test.glc.es",
                                "paqfaast55.test.es",
                                "paqfaast57.test.es",
                                "paqfaast58.test.es",
                                "paqfaast59.test.es",
                                "paqfaast60.test.es",
                                "paqfaast61.test.es",
                                "paqfaast62.test.es",
                                "paqfaast63.test.es",
                                "paqfaast64.test.es",
                                "paqfaast65.test.es",
                                "paqfaast66.test.es",
                                "paqfaast67.test.es",
                                "paqfaast68.dacfi.es",
                                "paqfaast69.dacfi.es",
                                "paqfaast70.dacfi.es",
                                "paqfaast71.dacfi.es",
                                "paqfaast72.dacfi.es",
                                "paqfaast73.dacfi.es",
                                "paqfaast74.dacfi.es",
                                "paqfaast75.dacfi.es",
                                "paqfaast76.dacfi.es",
                                "paqfaast77.dacfi.es",
                                "paqfaast78.dacfi.es",
                                "paqfaast79.dacfi.es"
                            ]
                        },
                        "default": {
                            "hosts": [
                                "arqopasr21.test.es",
                                "arqopasr29.test.es",
                                "arqopasr31.test.es",
                                "arqopast06.test.glc.es",
                                "arqopast13.test.es",
                                "arqopast15.testpre.glcpre.es",
                                "arqopast17.test.es",
                                "arqopast19.test.es",
                                "arqopast21.testpre.glcpre.es",
                                "arqopast23.testpre.glcpre.es",
                                "arqopast31.test.es",
                                "arqopast41.testpre.glcpre.es",
                                "arqopast43.testpre.glcpre.es",
                                "arqopast55.testpre.glcpre.es",
                                "arqopfst01.test.es",
                                "arqopwst02.test.es",
                                "arqopwst13.test.es",
                                "arqowasr04.testpre.glcpre.es",
                                "arqowast03.testpre.glcpre.es",
                                "arqowast13.testpre.glcpre.es",
                                "arqowast15.testpre.glcpre.es",
                                "arqowast17.testpre.glcpre.es",
                                "arqowast19.testpre.glcpre.es",
                                "arqowast21.testpre.glcpre.es",
                                "arqowast23.testpre.glcpre.es",
                                "paqfaast01.servicios.loc",
                                "paqfaast02.ppmcf.ppgbpi.loc",
                                "paqfaast03.ppscentrais.ppgbpi.loc",
                                "paqfaast04.servicios.loc",
                                "paqfaast05.netgbpi.ext",
                                "paqfaast06.pe.pr.geos.loc",
                                "paqfaast07.test.es",
                                "paqfaast08.scentrais.gbpi.loc",
                                "paqfaast09.test.es",
                                "paqfaast10.test.es",
                                "paqfaast11.scentrais.gbpi.loc",
                                "paqfaast12.test.es",
                                "paqfaast14.scentrais.gbpi.loc",
                                "paqfaast16.scentrais.gbpi.loc",
                                "paqfaast50.test.es",
                                "paqfaast51.test.es",
                                "paqfaast52.test.es",
                                "paqfaast53.test.es",
                                "paqfaast54.test.glc.es",
                                "paqfaast55.test.es",
                                "paqfaast57.test.es",
                                "paqfaast58.test.es",
                                "paqfaast59.test.es",
                                "paqfaast60.test.es",
                                "paqfaast61.test.es",
                                "paqfaast62.test.es",
                                "paqfaast63.test.es",
                                "paqfaast64.test.es",
                                "paqfaast65.test.es",
                                "paqfaast66.test.es",
                                "paqfaast67.test.es",
                                "paqfaast68.dacfi.es",
                                "paqfaast69.dacfi.es",
                                "paqfaast70.dacfi.es",
                                "paqfaast71.dacfi.es",
                                "paqfaast72.dacfi.es",
                                "paqfaast73.dacfi.es",
                                "paqfaast74.dacfi.es",
                                "paqfaast75.dacfi.es",
                                "paqfaast76.dacfi.es",
                                "paqfaast77.dacfi.es",
                                "paqfaast78.dacfi.es",
                                "paqfaast79.dacfi.es"
                            ]
                        },
                        "lab_inv_tests_factory_custom_group": {
                            "hosts": [
                                "arqopast13.test.es",
                                "arqopast41.testpre.glcpre.es"
                            ]
                        },
                        "lab_test_rh_1": {
                            "hosts": [
                                "arqopast17.test.es"
                            ]
                        },
                        "lab_inv_fenix_sergio": {
                            "hosts": [
                                "arqopast19.test.es"
                            ]
                        },
                        "lab_demoday": {
                            "hosts": [
                                "arqopast43.testpre.glcpre.es",
                                "arqopwst13.test.es"
                            ]
                        },
                        "lab_test_ferran": {
                            "hosts": [
                                "paqfaast50.test.es"
                            ]
                        },
                        "lab_paqfa_puppet_rebellion": {
                            "hosts": [
                                "paqfaast51.test.es"
                            ]
                        }
                    },
                    "TBASE": {
                        "tst": {
                            "hosts": [
                                "arqopast39.test.es",
                                "arqowasr06.testpre.glcpre.es",
                                "tbaseast05.test.es",
                                "tbaseast02.dacfi.es",
                                "tbaseast03.test.es",
                                "tbaseast04.dacfi.es",
                                "tbaseast01.test.es",
                                "tbaseast06.dacfi.es"
                            ]
                        },
                        "default": {
                            "hosts": [
                                "arqopast39.test.es",
                                "arqowasr06.testpre.glcpre.es",
                                "tbaseast05.test.es",
                                "tbaseast02.dacfi.es",
                                "tbaseast03.test.es",
                                "tbaseast04.dacfi.es",
                                "tbaseast01.test.es",
                                "tbaseast06.dacfi.es"
                            ]
                        }
                    },
                    "PAQBI": {
                        "tst": {
                            "hosts": [
                                "paqbiast01.scentrais.gbpi.loc",
                                "paqbiast02.mcf.gbpi.loc",
                                "paqbiast03.mcf.gbpi.loc",
                                "paqbiast04.scentrais.gbpi.loc",
                                "paqbiast05.servicios.loc",
                                "paqbiast06.servicios.loc",
                                "paqbiast07.servicios.loc",
                                "paqbiast08.servicios.loc"
                            ]
                        },
                        "default": {
                            "hosts": [
                                "paqbiast01.scentrais.gbpi.loc",
                                "paqbiast02.mcf.gbpi.loc",
                                "paqbiast03.mcf.gbpi.loc",
                                "paqbiast04.scentrais.gbpi.loc",
                                "paqbiast05.servicios.loc",
                                "paqbiast06.servicios.loc",
                                "paqbiast07.servicios.loc",
                                "paqbiast08.servicios.loc"
                            ]
                        }
                    },
                    "PAQCX": {
                        "tst": {
                            "hosts": [
                                "paqcxast01.test.es",
                                "paqcxast02.test.es",
                                "paqcxast03.test.es",
                                "paqcxast04.test.es",
                                "paqcxast05.test.glc.es",
                                "paqcxast06.test.glc.es",
                                "paqcxast07.test.glc.es",
                                "paqcxast08.test.glc.es"
                            ]
                        },
                        "default": {
                            "hosts": [
                                "paqcxast01.test.es",
                                "paqcxast02.test.es",
                                "paqcxast03.test.es",
                                "paqcxast04.test.es",
                                "paqcxast05.test.glc.es",
                                "paqcxast06.test.glc.es",
                                "paqcxast07.test.glc.es",
                                "paqcxast08.test.glc.es"
                            ]
                        }
                    },
                    "PAQFI": {
                        "tst": {
                            "hosts": [
                                "paqfiast09.dacfi.es",
                                "paqfiast10.dacfi.es",
                                "paqfiast11.dacfi.es",
                                "paqfiast12.dacfi.es",
                                "paqfiast13.dacfi.es",
                                "paqfiast14.dacfi.es",
                                "paqfiast17.dacfi.es",
                                "paqfiast18.dacfi.es"
                            ]
                        },
                        "default": {
                            "hosts": [
                                "paqfiast09.dacfi.es",
                                "paqfiast10.dacfi.es",
                                "paqfiast11.dacfi.es",
                                "paqfiast12.dacfi.es",
                                "paqfiast13.dacfi.es",
                                "paqfiast14.dacfi.es",
                                "paqfiast17.dacfi.es",
                                "paqfiast18.dacfi.es"
                            ]
                        }
                    },
                    "AAAAB": {
                        "tst": {
                            "hosts": [
                                "pepipto4.test.es",
                                "host30.test.es",
                                "pepipto12.test.es",
                                "pepipto12.test.es",
                                "pepipto4.test.es",
                                "pepipto12.test.es"
                            ]
                        },
                        "default": {
                            "hosts": [
                                "pepipto4.test.es",
                                "host30.test.es",
                                "pepipto12.test.es"
                            ]
                        }
                    },
                    "ABCDE": {
                        "tst": {
                            "hosts": [
                                "host00.test.es",
                                "host002.test.es"
                            ]
                        },
                        "default": {
                            "hosts": [
                                "host00.test.es",
                                "host002.test.es"
                            ]
                        }
                    }
                }
            }
        },
        "_meta": {
            "hostvars": {
                "arqopasr16.test.es": {
                    "system_code": "ARQOP",
                    "system_description": "ARQUITECTURA OPERACIO",
                    "host_environment": "pre",
                    "environment_description": "Preproduccio",
                    "center": "c2",
                    "security_zone": "mz",
                    "business_group": "TTS",
                    "ansible_connection": "ssh",
                    "step": 1,
                    "affiliate": "TESTS",
                    "ansible_user": "Patower1@arqopasr16.test.es",
                    "ansible_host": "sgsinasp-b1.svb.test.es"
                },
                "arqopasr19.test.es": {
                    "system_code": "ARQOP",
                    "system_description": "ARQUITECTURA OPERACIO",
                    "host_environment": "pre",
                    "environment_description": "Preproduccio",
                    "center": "c1",
                    "security_zone": "mz",
                    "business_group": "TTS",
                    "ansible_connection": "ssh",
                    "step": 1,
                    "affiliate": "TESTS",
                    "ansible_user": "Patower1@arqopasr19.test.es",
                    "ansible_host": "sgsinasp-b1.svb.test.es"
                },
                "arqopasr21.test.es": {
                    "system_code": "PAQFA",
                    "system_description": "SERVIDORES PAQUETIZACION FACTORY",
                    "host_environment": "dsv",
                    "environment_description": "Desenvolupament / Test",
                    "center": "c1",
                    "security_zone": "mz",
                    "business_group": "TTS",
                    "ansible_connection": "ssh",
                    "step": 1,
                    "affiliate": "TESTS",
                    "ansible_user": "Patower1@arqopasr21.test.es",
                    "ansible_host": "sgsinasp-b1.svb.test.es"
                }
            }
        }
    }
    }


def get_inventory_with_data_response_mock(cls, *args, **kwargs):
    return get_inventory()


def get_inventory_empty():
    return {
        "all": {
            "vars": {
                "ansible_winrm_cert_pem": "/var/lib/awx/connection_keys/winrm/Patower1/Patower1_cert.pem",
                "ansible_winrm_cert_key_pem": "/var/lib/awx/connection_keys/winrm/Patower1/Patower1_key.pem",
                "ansible_winrm_server_cert_validation": "ignore",
                "ansible_winrm_read_timeout_sec": 120,
                "ansible_winrm_transport": "certificate",
                "ansible_ssh_private_key_file": "/var/lib/awx/connection_keys/ssh/Patower1/id_rsa"
            },
            "groups": {},
            "_meta": {}
        }
    }


def get_inventory_empty_response_mock(cls, *args, **kwargs):
    return get_inventory_empty()


def request_json_response_mock(self, request, **kwargs):
    return Response()


def test_init():
    haiinv = Haiinv(
        base_url='localhost',
        username='AAAA',
        password='BBBB',
        proxy=''
    )

    assert haiinv.session.headers == {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    assert haiinv.session.auth.username == 'AAAA'
    assert haiinv.session.auth.password == 'BBBB'
    assert haiinv.base_url == 'localhost'
    assert haiinv.proxy == ''


def test_get_servers():
    haiinv = Haiinv(
        base_url='localhost',
        username='AAAA',
        password='BBBB',
        proxy=''
    )
    with mock.patch.object(
            Haiinv, '_Haiinv__request', get_inventory_with_data_response_mock):
        response = haiinv.get_servers('lab_test_rh_1', 'I-SSO-ES-TS-TSBASE-FACTORY')

    assert response == {
        'arqopasr16.test.es': {
            'system_code': 'ARQOP', 'system_description': 'ARQUITECTURA OPERACIO',
            'host_environment': 'pre', 'environment_description': 'Preproduccio',
            'center': 'c2', 'security_zone': 'mz', 'business_group': 'TTS',
            'ansible_connection': 'ssh', 'step': 1, 'affiliate': 'TESTS',
            'ansible_user': 'Patower1@arqopasr16.test.es', 'ansible_host':
            'sgsinasp-b1.svb.test.es'},
        'arqopasr19.test.es': {
            'system_code': 'ARQOP', 'system_description': 'ARQUITECTURA OPERACIO',
            'host_environment': 'pre', 'environment_description': 'Preproduccio',
            'center': 'c1', 'security_zone': 'mz', 'business_group': 'TTS',
            'ansible_connection': 'ssh', 'step': 1, 'affiliate': 'TESTS',
            'ansible_user': 'Patower1@arqopasr19.test.es', 'ansible_host':
            'sgsinasp-b1.svb.test.es'},
        'arqopasr21.test.es': {
            'system_code': 'PAQFA',
            'system_description': 'SERVIDORES PAQUETIZACION FACTORY',
            'host_environment': 'dsv',
            'environment_description': 'Desenvolupament / Test', 'center': 'c1',
            'security_zone': 'mz', 'business_group': 'TTS',
            'ansible_connection': 'ssh', 'step': 1, 'affiliate': 'TESTS',
            'ansible_user': 'Patower1@arqopasr21.test.es',
            'ansible_host': 'sgsinasp-b1.svb.test.es'}}


def test_get_servers_empty():
    haiinv = Haiinv(
        base_url='localhost',
        username='AAAA',
        password='BBBB',
        proxy=''
    )
    with mock.patch.object(
            Haiinv, '_Haiinv__request', get_inventory_empty_response_mock):
        response = haiinv.get_servers('lab_test_rh_1', 'I-SSO-ES-TS-TSBASE-FACTORY')

    assert response is None


def test_get_inventory_with_date():
    haiinv = Haiinv(
        base_url='localhost',
        username='AAAA',
        password='BBBB',
        proxy=''
    )
    with mock.patch.object(
            Haiinv, '_Haiinv__request', get_inventory_with_data_response_mock):
        response = haiinv.get_inventory('lab_test_rh_1', 'I-SSO-ES-TS-TSBASE-FACTORY')

    assert response == get_inventory()


class SessionDummySuccess:
    def prepare_request(self, request):
        pass

    @staticmethod
    def send(request, **kwargs):
        return ResponseDummySuccess()


class SessionDummyError:
    def prepare_request(self, request):
        pass

    @staticmethod
    def send(request, **kwargs):
        return ResponseDummyError()


class SessionDummyException:
    def prepare_request(self, request):
        pass

    @staticmethod
    def send(request, **kwargs):
        return ResponseDummyJsonException()


class SessionDummyException2:
    def prepare_request(self, request):
        pass

    @staticmethod
    def send(request, **kwargs):
        return ResponseDummyError3()


class ResponseDummyError:
    @staticmethod
    def json():
        return {'status': 'fail'}

    status_code = 400
    text = 'Error'


class ResponseDummyError2:
    @staticmethod
    def json():
        return {'status': 'fail'}

    status_code = 200
    text = 'Error'


class ResponseDummyError3:
    @staticmethod
    def json():
        return {'status': 'fail'}

    status_code = 422
    text = 'Error'


class ResponseDummyJsonException:
    @staticmethod
    def json():
        raise ValueError

    status_code = 400
    text = 'Error'


class ResponseDummySuccess:
    @staticmethod
    def json():
        return {'status': 'success',
                'data': 'respond'}

    status_code = 200
    text = 'Correct'


def test__request_success():

    request = requests.Request(
        Haiinv.VERB_POST,
        url='%s/api/v2/groups/%d/devices' % ("localhost", 1),
        json={
            'hosts': ['prueba.test.es']
        }
    )

    def __init__(self):
        self.session = SessionDummySuccess()
        self.proxy = ''

    with mock.patch.object(Haiinv, '__init__', __init__):
        haiinv = Haiinv()
        response = haiinv._Haiinv__request(request)

    assert response == 'respond'


def test__request_error():

    request = requests.Request(
        Haiinv.VERB_POST,
        url='%s/api/v2/groups/%d/devices' % ("localhost", 1),
        json={
            'hosts': ['prueba.test.es']
        }
    )

    def __init__(self):
        self.session = SessionDummyError()
        self.proxy = ''

    with mock.patch.object(Haiinv, '__init__', __init__):
        haiinv = Haiinv()
        with pytest.raises(IOError) as excinfo:
            haiinv._Haiinv__request(request)

    assert excinfo.value.args[0] == 'http error (400): Error'


def test__request_exception():

    request = requests.Request(
        Haiinv.VERB_POST,
        url='%s/api/v2/groups/%d/devices' % ("localhost", 1),
        json={
            'hosts': ['prueba.test.es']
        }
    )

    def __init__(self):
        self.session = SessionDummyException()
        self.proxy = ''

    with mock.patch.object(Haiinv, '__init__', __init__):
        haiinv = Haiinv()
        with pytest.raises(IOError) as excinfo:
            haiinv._Haiinv__request(request)

    assert excinfo.value.args[0] == 'http error (400): Error'


def test__request_exception2():

    request = requests.Request(
        Haiinv.VERB_POST,
        url='%s/api/v2/groups/%d/devices' % ("localhost", 1),
        json={
            'hosts': ['prueba.test.es']
        }
    )

    def __init__(self):
        self.session = SessionDummyException2()
        self.proxy = ''

    with mock.patch.object(Haiinv, '__init__', __init__):
        haiinv = Haiinv()
        with pytest.raises(IOError) as excinfo:
            haiinv._Haiinv__request(request)

    assert excinfo.value.args[0] == 'http error (422): Error'


def test__has_error_false():
    haiinv = Haiinv(
        base_url='localhost',
        username='AAAA',
        password='BBBB',
        proxy=''
    )
    response = haiinv._Haiinv__has_error(ResponseDummySuccess())

    assert not response


def test__safe_get():
    haiinv = Haiinv(
        base_url='localhost',
        username='AAAA',
        password='BBBB',
        proxy=''
    )
    response = haiinv._Haiinv__safe_get(get_inventory(), 'all', '_meta', 'hostvars')

    assert response == {
        'arqopasr16.test.es': {
            'system_code': 'ARQOP', 'system_description': 'ARQUITECTURA OPERACIO',
            'host_environment': 'pre', 'environment_description': 'Preproduccio',
            'center': 'c2', 'security_zone': 'mz', 'business_group': 'TTS',
            'ansible_connection': 'ssh', 'step': 1, 'affiliate': 'TESTS',
            'ansible_user': 'Patower1@arqopasr16.test.es', 'ansible_host':
            'sgsinasp-b1.svb.test.es'},
        'arqopasr19.test.es': {
            'system_code': 'ARQOP', 'system_description': 'ARQUITECTURA OPERACIO',
            'host_environment': 'pre', 'environment_description': 'Preproduccio',
            'center': 'c1', 'security_zone': 'mz', 'business_group': 'TTS',
            'ansible_connection': 'ssh', 'step': 1, 'affiliate': 'TESTS',
            'ansible_user': 'Patower1@arqopasr19.test.es', 'ansible_host':
            'sgsinasp-b1.svb.test.es'},
        'arqopasr21.test.es': {
            'system_code': 'PAQFA',
            'system_description': 'SERVIDORES PAQUETIZACION FACTORY',
            'host_environment': 'dsv',
            'environment_description': 'Desenvolupament / Test', 'center': 'c1',
            'security_zone': 'mz', 'business_group': 'TTS',
            'ansible_connection': 'ssh', 'step': 1, 'affiliate': 'TESTS',
            'ansible_user': 'Patower1@arqopasr21.test.es',
            'ansible_host': 'sgsinasp-b1.svb.test.es'}}


def test__safe_get2():
    haiinv = Haiinv(
        base_url='localhost',
        username='AAAA',
        password='BBBB',
        proxy=''
    )
    response = haiinv._Haiinv__safe_get(get_inventory_empty(), 'all', '_meta', 'hostvars')

    assert response is None
