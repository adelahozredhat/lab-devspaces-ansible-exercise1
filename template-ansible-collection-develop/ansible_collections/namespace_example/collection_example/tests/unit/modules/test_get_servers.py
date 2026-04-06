
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
import mock

from ....plugins.modules import get_servers as my_module
from ....plugins.module_utils.haiinv import Haiinv
from ....plugins.module_utils.exceptions import ValidationRequestException
from .commun_test import AnsibleExitJson, \
    set_module_args, AnsibleFailJson, module_mock  # noqa # pylint: disable=unused-import
from ansible.module_utils.basic import AnsibleModule


def common_args():
    set_module_args({
        'username': 'AAAA',
        'password': 'BBBB',
        'url': 'localhost',
        'proxy': '',
        'techgroups': 'lab_test_rh_1',
        'environment': 'previous'
    })


def get_servers_mock(cls, **kwargs):
    return {
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
        }
    }


def get_servers_empty(cls, **kwargs):
    return {
    }


def get_servers_raise_validation_exception(cls, **kwargs):
    raise ValidationRequestException('test Error')


def test_module_args_validation_enviroment(module_mock):
    set_module_args({
        'username': 'AAAA',
        'password': 'BBBB',
        'url': 'localhost',
        'proxy': '',
        'techgroups': 'lab_test_rh_1',
        'environment': 'I-SSO-ES-TS-TSBASE-FACTORY'
    })
    with mock.patch.object(
            Haiinv, 'get_servers', new=get_servers_mock):
        with pytest.raises(AnsibleFailJson) as result:
            my_module.main()

    assert result.value.args[0]['failed'] is True
    assert result.value.args[0]['msg'] == 'value of environment must be one of: production, previous, got: ' \
                                          'I-SSO-ES-TS-TSBASE-FACTORY'


def test_correct_execution_with_data(module_mock):
    common_args()
    with mock.patch.object(
            Haiinv, 'get_servers', new=get_servers_mock):
        with pytest.raises(AnsibleExitJson) as result:
            my_module.main()

    assert result.value.args[0]['changed'] is False
    assert result.value.args[0]['hosts'] == {
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
        }
    }


def test_correct_execution_empty(module_mock):
    common_args()
    with mock.patch.object(
            Haiinv, 'get_servers', new=get_servers_empty):
        with pytest.raises(AnsibleExitJson) as result:
            my_module.main()

    assert result.value.args[0]['changed'] is False
    assert result.value.args[0]['hosts'] == {}


def test_exception_execution(module_mock):
    common_args()
    with mock.patch.object(
            Haiinv, 'get_servers', new=get_servers_raise_validation_exception):
        with pytest.raises(AnsibleExitJson) as result:
            my_module.main()

    assert result.value.args[0]['changed'] is False
    assert result.value.args[0]['hosts'] == {}
    assert result.value.args[0]['warnings'][0] == 'test Error'


def test_error_execution(module_mock):
    common_args()
    with pytest.raises(AnsibleFailJson) as result:
        my_module.main()

    assert result.value.args[0]['changed'] is False
    assert result.value.args[0]['failed'] is True


def test_correct_execution_with_error(module_mock):
    common_args()

    def __init__(self, argument_spec,
                 supports_check_mode=False):
        self.argument_spec = argument_spec
        self.supports_check_mode = supports_check_mode
        self.check_mode = True

    with mock.patch.object(AnsibleModule, '__init__', __init__):
        with pytest.raises(AnsibleExitJson) as result:
            my_module.main()

    assert result.value.args[0]['changed'] is False
    assert result.value.args[0]['hosts'] == {}
