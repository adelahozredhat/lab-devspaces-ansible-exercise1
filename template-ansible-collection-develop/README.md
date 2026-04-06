# Ansible Collection - space.template_ansible_collection

Documentation for the collection.


This is a template collection for new modules with hellow world example

To execute life cycle testing, made a few commands to garantice correct development and it is possible agregate to life cicle software.

The first step is execute sanity of project

ansible-test sanity

This command incluse sintaxis tests, format, dependencies and others. It is need to garantice qualite of module

Example:

ansible-test sanity -v --python 3.8 --requirements

If it need exclude output tests information include this:
ansible-test sanity -v --python 3.8 --requirements --exclude tests/output/


ansible-test units

This command include unit python testing for plugins. In this repo include examples and config for this testings in ansible_collections/namespace_example/collection_example/tests/unit.


Example

ansible-test units --python 3.8 --requirements --coverage

If it need html inform coverage

ansible-test coverage html --python 3.8 --requirements



ansible-test integration

This command include integration testing in a roles for plugins. In this repo include examples and config for this testings in ansible_collections/namespace_example/collection_example/tests/intetgration.

Example

sudo ansible-test integration --python 3.8 --requirements

Not included coverage information



antsibull-changelog release --version 

This command agregate info change log


