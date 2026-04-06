# Ansible Collection - namespace_example.collection_example

Collection with modules to query endpoints from _HAIINV_.


Modules
-------

| Name                                | Purpose |
| :----                               | :------ |
| colection_example.get_servers              | Get a list servers with their hostvars using endpoint GET /inventory/ |

Installation
------------

The namespace_example.collection_example collection can be installed locally on the Tower control node by using the
following command:
    ansible-galaxy collection install <tarball_name> -p <path>

Where:

* _<tarball_name>_ = an extract of the collection taken from this repository (in compressed tar format)
* _<collections_path>_ = Directory where the collecion will be installed. (default: ~/.ansible/collections)

**Note**: It's recommended to use one of the values configured in Ansible setting _COLLECTIONS_PATHS_ when using the -p
option as this is where Ansible will expect to find collections.

Examples:

    ansible-galaxy collection namespace_example.collection_example -p ~/.ansible/collections

or

    ansible-galaxy collection namespace_example.collection_example -p /usr/share/ansible/collections

Further details on installing
collections [here](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html#installing-collections)

Using the collection
--------------------

To use the modules of this collection in playbooks you must reference them via their fully qualified collection name (
FQCN).

    namespace_example.collection_example.<module_name>

**Get Servers**

```YML
    ---
      - hosts: all
    tasks:
      - name: "Example get information"
        namespace_example.collection_example.get_servers:
            username: "{{ example_username }}"
            password: "{{ example_password }}"
            url: "{{ example_url }}"
            proxy: "{{ example_proxy }}"
            techgroups: "{{ example_techgroups }}"
            environment: "{{ example_environment }}"
```

Further details on using
collections [here](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html#using-collections-in-a-playbook)

Maintainers
-----------

* Alejandro de la Hoz (adelahoz@redhat.com)