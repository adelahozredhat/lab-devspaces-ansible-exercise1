#!/usr/bin/python
# -*- coding: utf-8 -*-

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: get_servers

short_description: Module to get a server list owned by one or more technical group

version_added: "1.0.0"

description:
    - "Module to get a server list with their hostvars owned by one or more technical group"

options:
    username:
        description:
            - The user to connect to haiinv
        required: True
        type: str
    password:
        description:
            - The password to connect to haiinv
        required: True
        type: str
    url:
        description:
            - The url base of haiinv API
        required: True
        type: str
    proxy:
        description:
            - Definition of proxy if it is needed
        required: False
        type: str
    techgroups:
        description:
            - List of techgroups or teams in ITNow
        required: True
        type: list
        elements: str
    environment:
        description:
            - The server environment to retrieve
        required: False
        type: str
        choices: ['production', 'previous']

author:
  - Alejandro de la Hoz (@adelahoz)
'''

EXAMPLES = '''
# Pass in a message
- name: Get server from techgroup AAA-BBB-111
  namespace_example.collection_example.get_servers:
    username: haiinvUser
    password: mypassword
    url: http://domain.com/haiinv
    proxy: proxy.com:8080
    techgroups:
      - I-SSO-ES-TS-FACTORY-FABRIC
      - I-SSO-ES-TS-TSBASE-FACTORY
  register: result
'''

RETURN = '''
hosts:
    description: Dictionary with hostname as key and list of hostvars as value
    returned: always
    type: dict
    sample:
        hosts:
            "host6.test.es":
                "system_code": "SYSTEM_1"
                "system_description": "System description"
                "host_environment": "pre"
                "environment_description": "Preroduccio Tests"
                "center": "c2"
                "security_zone": "mz"
                "business_group": "TTS"
                "ansible_connection": "winrm"
            "host7.test.es":
                "system_code": "SYSTEM_2"
                "system_description": "System description"
                "host_environment": "pre"
                "environment_description": "Produccio Tests"
                "center": "c1"
                "security_zone": "dmz"
                "business_group": "TTS"
                "ansible_connection": "winrm"
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.haiinv import Haiinv
from ..module_utils.exceptions import ValidationRequestException

try:
    from requests import RequestException
except ImportError:
    def run_module():
        pass


def run_module():
    """
    Method include all execution functions when run from ansible module
    """
    module_args = dict(
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        url=dict(type='str', required=True),
        proxy=dict(type='str', required=False, default=None),
        techgroups=dict(type='list', elements='str', required=True),
        environment=dict(type='str', choices=['production', 'previous'], default=None)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False,
        hosts={}
    )

    if module.check_mode:
        module.exit_json(**result)

    warnings = []
    list_ttss = module.params['techgroups']
    environment = module.params['environment']
    haiinv = Haiinv(
        module.params['url'],
        module.params['username'],
        module.params['password'],
        module.params['proxy']
    )

    for ttss in list_ttss:
        try:
            haiinv_result = haiinv.get_servers(ttss=ttss, env=environment)
            result['hosts'].update(dict({}) if haiinv_result is None else haiinv_result)
        except ValidationRequestException as exception:
            warnings.append(str(exception))
        except RequestException as exception:
            module.fail_json(msg=str(exception), changed=False)

    if warnings:
        result['warnings'] = warnings

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    """
    Method main of class execution
    """
    run_module()


if __name__ == '__main__':
    main()  # pragma: no cover
