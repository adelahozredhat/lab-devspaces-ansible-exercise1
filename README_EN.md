# lab-devspaces-ansible-exercise1

Hands-on course on Ansible playbook development. The reference file `deploy-wildfly.yaml` shows the target result; this document is a guide to build it, refactor it, and validate it with quality tools.

---

## Environment setup

```bash
chmod 600 ssh_tests_connections/id_fedora_new
ansible-galaxy collection install community.general
```

**Final result of this block (setup):** SSH key with restrictive permissions so SSH and Ansible accept it; `community.general` collection available in the controller Ansible environment for extra modules if the playbook uses them.

---

## 1. Context: what `deploy-wildfly.yaml` does

The playbook automates a **WildFly 39** installation aligned with the official product documentation. In a single run against the `servers` inventory group (with elevated privileges):

1. **Defines variables** for version, install paths, service user and group, and the official tarball download URL.
2. **Prepares the operating system** by installing Java 21 (required for WildFly 39) and utilities needed to unpack the package.
3. **Creates a service identity**: dedicated system group and user, with home in the install directory and a restrictive shell.
4. **Downloads and installs** WildFly from GitHub under `/opt`, skipping extraction again if the expected install marker already exists.
5. **Normalizes the working path** with a symbolic link from `/opt/wildfly-<version>` to `/opt/wildfly`, so scripts and services point at a stable path.
6. **Adjusts `standalone.xml`** so the public interface listens on `0.0.0.0` instead of only `127.0.0.1`, allowing network access to the application server.
7. **Integrates systemd**: copies `launch.sh`, the `wildfly.service` unit, and `wildfly.conf` from the examples included in the distribution, creates `/etc/wildfly`, and starts and enables the service with a systemd daemon reload.
8. **Deploys a sample application** by packaging a local `index.html` as a WAR on the controller and copying it to WildFly’s `standalone/deployments` directory to verify the deployment pipeline.

In the reference file there are commented **firewalld** tasks; you can enable them in your version if the environment requires it.

**Final result of this block (§1 — overview):** after running the reference playbook against `servers`, the node has WildFly installed under `/opt`, a `wildfly` service managed by systemd, network listen (public interface `0.0.0.0`), and a sample application reachable over HTTP at the `/sample/` context (default port 8080), unless the firewall blocks external access.

---

## Inventory: Fedora VM host on OpenShift

Before **section 2 (step-by-step guide for the monolithic playbook)**, you must adapt the `inventory` file in **the same folder as this README**. The play targets the `[servers]` group; that is where you define which machine Ansible will run against and which SSH user and key it will use.

The host details for your **Fedora virtual machine** deployed in the lab environment (name or address reachable from OpenShift Dev Spaces, SSH user if it differs from the template, and so on) are in the **lab access data and general information Excel** you were given. Replace the `ansible_host` value (and, if the document or instructor says so, `ansible_user` or the host alias in the first column) with those assigned to you. Keep the `ansible_ssh_private_key_file` path aligned with the key you prepared in “Environment setup” (for example `ssh_tests_connections/id_fedora_new`).

Reference file template:

```ini
[servers]
fedora-user1 ansible_host=<host_or_IP_from_Excel> ansible_user=user1 ansible_ssh_private_key_file=ssh_tests_connections/id_fedora_new
```

Without a correct inventory, `ansible-playbook -i inventory …` will not be able to reach your VM. Check SSH connectivity from the workspace before continuing with the guide.

**Final result of this block (inventory):** `inventory` file with `ansible_host` (and other fields if applicable) consistent with the lab Excel; the `servers` group resolves to your Fedora VM for later playbook runs.

---

## 2. Step-by-step guide (first monolithic playbook)

Goal: obtain a playbook equivalent to the reference one, understanding the **logical order** and **purpose** of each block. This guide does not repeat the documentation of every Ansible module; consult the official module documentation the first time you use it.

After each step, the **concrete YAML** taken from `deploy-wildfly.yaml` is shown. At the end of each **logical block**, the **resulting state** on the node is summarized (files, services, or no on-disk changes).

### Step 1 — Play header

Define a descriptive play name, the hosts pattern (`servers` or another group from your inventory), and `become: true` if you need to install packages and write under `/opt` and `/etc`.

```yaml
- name: Instalación de WildFly 39 siguiendo la Guía Oficial
  hosts: servers
  become: true
```

### Step 2 — Play variables (`vars`)

Declare at least: WildFly version, logical install directory (`/opt/wildfly`), service user and group, and the `.tar.gz` download URL (you can interpolate the version in the string).

```yaml
  vars:
    wf_version: "39.0.1.Final"
    wf_install_dir: "/opt/wildfly"
    wf_user: "wildfly"
    wf_group: "wildfly"
    wf_url: "https://github.com/wildfly/wildfly/releases/download/{{ wf_version }}/wildfly-{{ wf_version }}.tar.gz"
```

**Result on the node (files / state):** steps 1 and 2 write nothing on the target; they only set the play scope and in-memory variables during execution.

**Final result of this block (steps 1–2 — header and variables):** inventory and play ready to run tasks; no persistent change on the host until the first task under `tasks:`.

### Step 3 — System dependencies

First task: install the appropriate JDK on the target node (Java 21 for WildFly 39), plus tools required to handle the compressed archive (for example `tar` and `gzip`).

```yaml
  tasks:
    - name: Instalar dependencias (Java 17+ es requerido para WF 39)
      ansible.builtin.dnf:
        name:
          - java-21-openjdk-devel
          - tar
          - gzip
        state: present
```

**Result on the node:** RPM packages installed (`java-21-openjdk-devel`, `tar`, `gzip`); binaries available on the system PATH (`java`, `tar`, `gzip`).

**Final result of this block (step 3 — OS dependencies):** system ready to download and unpack WildFly and to run the required JVM.

### Step 4 — System group for WildFly

Create the service group as a system group, present on the node.

```yaml
    - name: Crear grupo de sistema para WildFly
      ansible.builtin.group:
        name: "{{ wf_group }}"
        system: true
        state: present
```

**Final result of this block (step 4 — group only):** `/etc/group` contains the `wildfly` system group line (GID assigned by the system).

### Step 5 — System user for WildFly

Create the service user associated with that group, with home in the install directory, a non-login shell, and marked as a system account.

```yaml
    - name: Crear usuario de sistema para WildFly
      ansible.builtin.user:
        name: "{{ wf_user }}"
        group: "{{ wf_group }}"
        home: "{{ wf_install_dir }}"
        shell: /sbin/nologin
        system: true
        state: present
```

**Result on the node:** `/etc/group` entry for `wildfly`; `/etc/passwd` (and shadow) entry for `wildfly` with the previous group’s GID, home declared as `/opt/wildfly`, and shell `/sbin/nologin`. The home directory may not yet exist as a full tree until the install under `/opt` is created.

**Final result of this block (steps 4–5 — service identity):** system account ready to run WildFly: `wildfly` group and user created; there is still no product tree under `/opt/wildfly` until installation is complete.

### Step 6 — Download and install the product

Download the archive from the URL and unpack it under `/opt`, assigning owner and group to the WildFly user. Use an idempotent mechanism (for example checking that a key install file already exists) so extraction is not repeated unnecessarily.

```yaml
    - name: Descargar y extraer WildFly 39
      ansible.builtin.unarchive:
        src: "{{ wf_url }}"
        dest: "/opt"
        remote_src: yes
        owner: "{{ wf_user }}"
        group: "{{ wf_group }}"
        creates: "{{ wf_install_dir }}/bin/standalone.sh"
```

**Final result of this block (step 6 — extraction):** `/opt/wildfly-{{ wf_version }}/` exists (e.g. `/opt/wildfly-39.0.1.Final/`) with the tarball contents, UID/GID `wildfly`. The canonical path `/opt/wildfly` may not exist yet if this is the first install and the link is created in later steps.

### Step 7 — Clean the destination link or directory (if applicable)

If your design always reuses the same canonical path (`/opt/wildfly`), include a conditional task that removes that destination when you are not in check mode, consistent with how you want to manage upgrades or reinstalls.

```yaml
    - name: Eliminar directorio destino si ya existe y no es link (Limpieza)
      ansible.builtin.file:
        path: "{{ wf_install_dir }}"
        state: absent
      when: not ansible_check_mode
```

**Final result of this block (step 7 — destination cleanup):** if `/opt/wildfly` existed (link or directory), it has been removed; the versioned directory `/opt/wildfly-{{ wf_version }}/` remains. In `--check` mode the task does not apply the change (`when: not ansible_check_mode`).

### Step 8 — Symbolic link to the specific version

Create the link from the versioned directory under `/opt` to the stable working path, with the same owner and group as the service.

```yaml
    - name: Crear enlace simbólico a la versión instalada
      ansible.builtin.file:
        src: "/opt/wildfly-{{ wf_version }}"
        dest: "{{ wf_install_dir }}"
        state: link
        owner: "{{ wf_user }}"
        group: "{{ wf_group }}"
```

**Result on the node:** versioned directory `/opt/wildfly-39.0.1.Final/` with the full server tree (for example `bin/standalone.sh`, `standalone/configuration/standalone.xml`, `docs/contrib/scripts/systemd/`, etc.), owner `wildfly`. Symbolic link `/opt/wildfly` → `/opt/wildfly-39.0.1.Final`. After step 7, if a previous link or path existed at `/opt/wildfly`, it was removed before recreating the link.

**Final result of this block (steps 6–8 — install and stable path):** WildFly product in `/opt/wildfly-<version>/` and also reachable as `/opt/wildfly` (symlink); ready for configuration and service setup.

### Step 9 — Listen on all interfaces

Modify the corresponding line in `standalone.xml` of the already installed WildFly (via the link path) so the `public` interface uses `0.0.0.0` by default instead of `127.0.0.1`. Make sure the regular expression and the replacement line match the real XML format of the file.

```yaml
    - name: Configurar WildFly para que escuche en todas las IPs (0.0.0.0)
      ansible.builtin.lineinfile:
        path: "{{ wf_install_dir }}/standalone/configuration/standalone.xml"
        regexp: '<interface name="public">(\s*)<inet-address value="\$ \{jboss\.bind\.address:127\.0\.0\.1\}"/>'
        line: '        <interface name="public"><inet-address value="${jboss.bind.address:0.0.0.0}"/></interface>'
        backrefs: yes
```

**Result on the node:** in `/opt/wildfly/standalone/configuration/standalone.xml` (via the link), the `public` interface fragment has default `inet-address` `0.0.0.0` instead of `127.0.0.1`, so the server can listen on all network interfaces.

**Final result of this block (step 9 — network / bind):** persistent configuration in `standalone.xml` to expose the `public` interface on all IPs; full effect after the next WildFly process start (or service restart).

### Step 10 — Startup script for systemd

Copy the `launch.sh` script from the documentation included in the installation into the WildFly `bin` tree, keeping execute permissions.

```yaml
    - name: Instalar el archivo de servicio Systemd (Siguiendo la guía de WF)
      ansible.builtin.copy:
        src: "{{ wf_install_dir }}/docs/contrib/scripts/systemd/launch.sh"
        dest: "{{ wf_install_dir }}/bin/launch.sh"
        remote_src: yes
        mode: '0755'
```

### Step 11 — systemd unit

Copy the `wildfly.service` unit file to the system systemd units directory.

```yaml
    - name: Instalar el archivo de servicio Systemd (Siguiendo la guía de WF)
      ansible.builtin.copy:
        src: "{{ wf_install_dir }}/docs/contrib/scripts/systemd/wildfly.service"
        dest: "/etc/systemd/system/wildfly.service"
        remote_src: yes
```

### Step 12 — Service configuration directory and file

Create `/etc/wildfly` and copy the sample `wildfly.conf` from the installation there.

```yaml
    - name: Crear directorio de configuración para el servicio
      ansible.builtin.file:
        path: /etc/wildfly
        state: directory

    - name: Copiar configuración por defecto del servicio
      ansible.builtin.copy:
        src: "{{ wf_install_dir }}/docs/contrib/scripts/systemd/wildfly.conf"
        dest: "/etc/wildfly/wildfly.conf"
        remote_src: yes
```

**Final result of this block (steps 10–12 — service files on disk):** `/opt/wildfly/bin/launch.sh` with executable mode; `/etc/systemd/system/wildfly.service`; `/etc/wildfly/` directory with `wildfly.conf`. The daemon **may still not be** active until the step 13 task.

### Step 13 — Start and enable the service

Reload systemd configuration, ensure the `wildfly` service is started and enabled at boot.

```yaml
    - name: Recargar systemd y arrancar WildFly
      ansible.builtin.systemd:
        name: wildfly
        state: started
        enabled: true
        daemon_reload: true
```

**Result on the node:** `/opt/wildfly/bin/launch.sh` executable; `/etc/systemd/system/wildfly.service`; `/etc/wildfly/` directory with `wildfly.conf`. After the systemd task: unit reloaded, `wildfly` service active (`systemctl is-active wildfly`) and enabled at boot; process listening (among others) on the default HTTP application port (8080).

**Final result of this block (steps 10–13 — systemd integration and runtime):** unit installed, configuration in `/etc/wildfly`, `wildfly` service **running** and **enabled**, with JVM listening on 8080 (and other default `standalone` ports).

### Step 14 — (Optional) Firewall

If your lab uses `firewalld`, uncomment or add opening of the application server HTTP port (for example 8080/tcp) permanently and immediately. Requires the appropriate collection in the project.

```yaml
    # - name: Abrir puerto 8080 en firewalld
    #   ansible.posix.firewalld:
    #     port: 8080/tcp
    #     permanent: true
    #     state: enabled
    #     immediate: true
```

**Result on the node (if you uncomment and run):** permanent and effective `firewalld` rule for `8080/tcp`; external access to the port according to the host network policy.

**Final result of this block (step 14 — firewall, optional):** if the task is active, `firewall-cmd --list-ports` (or equivalent) shows `8080/tcp` in runtime and in permanent configuration.

### Step 15 — Sample application

Wrap this in a clear flow: on the controller, generate a WAR from `index.html` (packaged as a zip archive with `.war` extension); copy that artifact to WildFly’s `standalone/deployments` directory with the correct owner. If the WAR is built on localhost, use delegation and disable `become` in that part so you do not require privileges on the machine from which you run Ansible.

```yaml
    - name: Crear y desplegar la aplicación de ejemplo
      block:
        - name: Empaquetar WAR localmente
          community.general.archive:
            path: index.html
            dest: /tmp/sample.war
            format: zip
          delegate_to: localhost
          become: false

        - name: Copiar WAR al directorio de despliegue
          ansible.builtin.copy:
            src: /tmp/sample.war
            dest: "{{ wf_install_dir }}/standalone/deployments/sample.war"
            owner: "{{ wf_user }}"
            group: "{{ wf_group }}"
```

**Result on the node:** on the control machine: `/tmp/sample.war` file (ZIP with `index.html` inside). On the target: `/opt/wildfly/standalone/deployments/sample.war` owned by `wildfly`; WildFly may generate `sample.war.deployed` (and other markers) when deployment completes. Expected HTTP response to check the context, for example `curl http://<host>:8080/sample/`.

**Final result of this block (step 15 — sample application):** `sample.war` artifact deployed; `/sample/` context serves the `index.html` content; typical check `curl -sSf http://localhost:8080/sample/` from the server or against the node IP.

Run the playbook and validate with `curl` or a browser against the sample application URL.

**Final result of this block (§2 — complete monolithic playbook):** accumulation of all previous sub-blocks: Java and utility RPMs; `wildfly` user/group; `/opt/wildfly` → installed version; `standalone.xml` with bind `0.0.0.0`; systemd + active service; optionally firewalld; sample WAR and HTTP 200 on `/sample/`.

---

## 3. Second part: refactoring with `tags` and `block`

Starting from the monolithic playbook, improve operability without changing functional behavior.

### 3.1 Tags (`tags`)

Assign coherent tags to task groups so you can run only fragments of the play, for example:

- `deps` — system packages.
- `wildfly_user` — group and user.
- `wildfly_install` — download, destination cleanup, and symbolic link.
- `wildfly_config` — `standalone.xml` modification.
- `wildfly_service` — systemd files, `/etc/wildfly`, service start.
- `app` — packaging and copy of the sample WAR.
- `firewall` — firewall rules, if you have them.

Usage example:

```bash
ansible-playbook -i inventory deploy-wildfly.yaml --tags wildfly_service
ansible-playbook -i inventory deploy-wildfly.yaml --skip-tags app
```

Concrete example (fragment over existing tasks):

```yaml
    - name: Instalar dependencias (Java 17+ es requerido para WF 39)
      ansible.builtin.dnf:
        name:
          - java-21-openjdk-devel
          - tar
          - gzip
        state: present
      tags: [deps]

    - name: Crear grupo de sistema para WildFly
      ansible.builtin.group:
        name: "{{ wf_group }}"
        system: true
        state: present
      tags: [wildfly_user]
```

**Result on the node:** identical to the playbook without tags; `tags` only change **which tasks run** when you invoke `--tags` / `--skip-tags`, not the final system state when you run the full play.

### 3.2 Blocks (`block`)

Group related tasks in `block` for:

- **Readability**: one “binary install” block, another “systemd integration”, another “sample application”.
- **Optional rescue** (`rescue`) or **always** (`always`): for example, if copying the service fails, log a message or try diagnostics; in `always`, cleanup or state-logging tasks.

You do not have to add `rescue`/`always` if you only want visual grouping; `block` plus comments in the playbook is enough.

Concrete example (same block as step 15, already present in the reference playbook):

```yaml
    - name: Crear y desplegar la aplicación de ejemplo
      block:
        - name: Empaquetar WAR localmente
          community.general.archive:
            path: index.html
            dest: /tmp/sample.war
            format: zip
          delegate_to: localhost
          become: false

        - name: Copiar WAR al directorio de despliegue
          ansible.builtin.copy:
            src: /tmp/sample.war
            dest: "{{ wf_install_dir }}/standalone/deployments/sample.war"
            owner: "{{ wf_user }}"
            group: "{{ wf_group }}"
```

**Result on the node:** the same as without `block`: `/tmp/sample.war` on the controller and `sample.war` under `standalone/deployments/` on the target. The `block` groups the flow for reading and so you can add `rescue` / `always` without changing the on-disk result.

**Final result of this block (§3 — tags and block):** the **target node state** after a full `ansible-playbook` without `--tags` matches the monolith (§2). In the **repository**, the playbook is more operable: you can limit execution by tags and structure tasks in `block` without changing the on-disk result unless you omit tasks with `--skip-tags`.

---

## 4. Third part: roles, variables, and handlers

Extract the previous blocks into **roles** inside the same playbook project (for example a `roles/` directory next to the playbook). The main playbook stays short: a list of roles and, if needed, `vars` or `vars_files` that override each role’s defaults.

### 4.1 Suggested role layout


| Role                 | Typical contents                                                          |
| -------------------- | ------------------------------------------------------------------------- |
| `wildfly_os_deps`    | Package installation (Java, tar, gzip).                                   |
| `wildfly_account`    | System group and user.                                                    |
| `wildfly_install`    | Download, extraction, conditional destination cleanup, symbolic link.     |
| `wildfly_bind`       | `standalone.xml` adjustment for `0.0.0.0`.                                |
| `wildfly_systemd`    | `launch.sh`, `wildfly.service`, `/etc/wildfly`, start and enable.         |
| `wildfly_sample_app` | Local packaging block and WAR copy.                                       |


You can merge roles if you prefer less granularity; what matters is that each role has a clear responsibility.

**Result in the project (files):** indicative tree after creating the roles (file names follow Ansible convention):

```text
roles/
  wildfly_os_deps/tasks/main.yml
  wildfly_account/tasks/main.yml
  wildfly_install/tasks/main.yml
  wildfly_bind/tasks/main.yml
  wildfly_systemd/tasks/main.yml
  wildfly_sample_app/tasks/main.yml
deploy-wildfly.yaml   # or site.yml that imports roles
```

### 4.2 Variables

Define in each role a `defaults/main.yml` with default values (version, paths, user/group names, URL). The playbook can pass variables with `vars:` or with a `group_vars/servers.yml` file so you do not hardcode secrets or IPs.

Concrete example (`roles/wildfly_install/defaults/main.yml`):

```yaml
wf_version: "39.0.1.Final"
wf_install_dir: "/opt/wildfly"
wf_user: "wildfly"
wf_group: "wildfly"
wf_url: "https://github.com/wildfly/wildfly/releases/download/{{ wf_version }}/wildfly-{{ wf_version }}.tar.gz"
```

**Result on the node:** the same as in the monolithic guide; variables only change **where** they are defined (role vs play). If the playbook or `group_vars` override `wf_version`, the tree under `/opt` will use the new version in paths and URL.

### 4.3 Handlers

Replace or complement tasks that currently mix “change a file” and “restart a service” with the `**notify`** pattern:

- Handler `**reload systemd**`: reloads the daemon when units under `/etc/systemd/system` change.
- Handler `**restart wildfly**`: restarts the service when `wildfly.conf`, `launch.sh`, or files under `standalone/configuration` that require a restart change.

On `copy` or `template` tasks that modify those files, add `notify` with the handler name. Keep consistency: if a task already forces `daemon_reload` and `state: started`, when introducing handlers review that you do not duplicate unnecessary restarts on the first run.

Concrete example (`roles/wildfly_systemd/handlers/main.yml`):

```yaml
---
- name: recargar systemd
  ansible.builtin.systemd:
    daemon_reload: true

- name: reiniciar wildfly
  ansible.builtin.service:
    name: wildfly
    state: restarted
```

Task that notifies (fragment):

```yaml
    - name: Copiar unidad wildfly.service
      ansible.builtin.copy:
        src: "{{ wf_install_dir }}/docs/contrib/scripts/systemd/wildfly.service"
        dest: "/etc/systemd/system/wildfly.service"
        remote_src: yes
      notify:
        - recargar systemd
        - reiniciar wildfly
```

**Result on the node:** after a change that fires the handlers, systemd reloads units and the `wildfly` service restarts; on disk the same files persist as in the monolithic playbook (`/etc/systemd/system/wildfly.service`, etc.), with application order governed by Ansible at the end of the play (handlers).

### 4.4 Playbook that calls the roles

Example structure (illustrative):

```yaml
---
- name: Instalación de WildFly con roles
  hosts: servers
  become: true
  roles:
    - role: wildfly_os_deps
    - role: wildfly_account
    - role: wildfly_install
    - role: wildfly_bind
    - role: wildfly_systemd
    - role: wildfly_sample_app
      tags: [app]
```

You can define tags at role level in the playbook or inside each role on the tasks.

**Result on the node:** equivalent to running the full monolithic playbook; the difference is the **repository layout** (reusable roles) and the ability to override variables per environment without editing the tasks.

**Final result of this block (§4 — roles):** on the target disk, the same result as **Final result of this block (§2)** if the roles replicate the same tasks and variables. In the **project**: `roles/` directory with `tasks/main.yml`, `defaults/main.yml`, and, if applicable, `handlers/main.yml`; a short playbook that only orders roles and optionally `group_vars` / `vars`.

---

## 5. Quality: yamllint, ansible-lint, and Molecule

### 5.1 yamllint

Checks YAML syntax and style (indentation, long lines, multiple documents).

Installation (pip example):

```bash
pip install yamllint
```

Typical run over the project:

```bash
yamllint .
```

Optional: add a `.yamllint` file at the root to relax or tighten rules according to the course standard.

**Final result of this block (5.1 — yamllint):** output with no errors (exit code `0`) or a list of files/lines to fix according to your `.yamllint`; the project YAML meets the style rules agreed in the course.

### 5.2 ansible-lint

Analyzes playbooks and roles against Ansible best practices (names, `fqcn`, use of `become`, idempotence, etc.).

Installation:

```bash
pip install ansible-lint
```

Execution:

```bash
ansible-lint deploy-wildfly.yaml
# or, if you already have roles:
ansible-lint .
```

Fix the warnings the instructor marks as mandatory to pass the exercise.

**Final result of this block (5.2 — ansible-lint):** run with exit code `0` (or only warnings accepted by the instructor); playbooks and roles pass the configured quality rules (FQCN, task names, idempotence, etc.).

### 5.3 Molecule (playbook test)

Molecule runs the playbook against an ephemeral environment (container, VM, or delegated to a provider) and a verification playbook.

This repository has a scenario under `molecule/default/` with **delegated** driver and `create`, `converge`, `verify`, and `destroy` steps. To align it with **this** WildFly exercise you must, at minimum:

1. `**converge.yml`**: import or include your real playbook (for example `deploy-wildfly.yaml` or the role-based playbook), not a placeholder name.
2. **Inventory / hosts**: the playbook group or host name must match what is defined in `molecule.yml` and in `host_vars` (for example if the play uses `hosts: servers`, the Molecule inventory must declare that group with the test platform hostname).
3. `**verify.yml`**: check the `**wildfly**` service (not another unit name), wait for port **8080**, and validate the sample application URL (`**/sample/`** or the path that matches your WAR), with reasonable retries.

Typical installation:

```bash
pip install molecule molecule-plugins ansible
```

Default scenario execution:

```bash
cd /path/to/the/project
molecule test
```

Manual sequence (debugging):

```bash
molecule create
molecule converge
molecule verify
molecule destroy
```

Adjust `create.yml` and credentials in group variables if your lab environment uses OpenShift/KubeVirt or another backend; without a node reachable over SSH, `converge` cannot apply the playbook.

**Final result of this block (5.3 — Molecule):** `molecule test` completes the sequence `destroy` → `create` → `converge` → `verify` → `destroy` with exit code `0`; the playbook is applied in the test environment and `verify.yml` confirms service, port, and application URL. If a step fails, the output indicates which scenario (`converge` / `verify`) to fix.

**Final result of this block (§5 — quality):** repeatable local pipeline: valid and consistent YAML (yamllint), Ansible best practices (ansible-lint), and end-to-end test (Molecule) aligned with WildFly and `/sample/`.

---

## 6. Signing the project with `ansible-sign`

[ansible-sign](https://ansible.readthedocs.io/projects/sign/en/latest/) generates a checksum manifest (SHA-256) of the project files you choose and signs that manifest with GPG. That way you can prove the signed content has not been altered. In this course we use a **shared GPG passphrase** so all participants use the same criterion when creating the signing key and when signing.

### Lab password (GPG passphrase)

When generating your GPG key pair and when `ansible-sign` or GnuPG asks for the private key password, use **exactly** this passphrase (the same for all lab attendees):

```text
CorreosAnsibleSign-Lab2026
```

This is the password of the **GPG key container** (passphrase), not a system user. Keep it only for the exercise; in real environments each signer would use their own confidential passphrase.

### 6.1 Requirements and installation

You need GnuPG (`gpg`) on the system and the ansible-sign CLI; in this lab it is already installed inside the image used in Dev Spaces and is not required:

```bash
pip install ansible-sign
ansible-sign --version
```

Check whether you already have a secret key (optional; if not, the next section creates it):

```bash
gpg --list-secret-keys
```

### 6.2 GPG key pair for signing

If you do not have a suitable key for signing, create one (default type and validity are usually enough). When it asks for a **passphrase**, enter `CorreosAnsibleSign-Lab2026`.

```bash
gpg --full-generate-key
```

Note the key **identifier** (fingerprint or associated e-mail) in case you later use `ansible-sign project gpg-sign --fingerprint <ID> .`.

To **verify** a signature made by someone else you need their **public key** in your keyring. The signer can export it:

```bash
gpg --armor --export you@lab.email > lab-ansible-sign-pub.asc
```

The verifier imports it:

```bash
gpg --import lab-ansible-sign-pub.asc
```

If you sign and verify the same project yourself on the same machine, your public key is already in your keyring and you do not need to import anything.

### 6.3 `MANIFEST.in`: which files go into the signature

At the **project root** (same level as `deploy-wildfly.yaml`), create a `MANIFEST.in` file following the [manifest syntax](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html) that ansible-sign uses. Include the playbook and the rest of the automation artifacts you want to protect; **exclude** `inventory` if it contains data specific to your VM (it changes between students and would break collective verification unless everyone shares the same content).

Indicative example for this repository:

```text
include deploy-wildfly.yaml
include index.html
recursive-include molecule *.yml
exclude inventory
```

If you add roles or other playbooks, extend the manifest with `recursive-include roles *.yml` or other `include` directives consistent with your tree.

### 6.4 Sign the project

From the project root:

```bash
ansible-sign project gpg-sign --prompt-passphrase .
```

If the graphical GPG dialog does not appear, `--prompt-passphrase` makes the passphrase prompt in the terminal; enter `CorreosAnsibleSign-Lab2026`.

In automated environments the `ANSIBLE_SIGN_GPG_PASSPHRASE` variable with the same phrase is also accepted (useful in CI; in the course prioritize the interactive practice).

Expected output (summarized): creation or update of `.ansible-sign/sha256sum.txt` and the signature `.ansible-sign/sha256sum.txt.sig`.

### 6.5 Verify the signature

With the same project (and the signer’s public key imported if you are not the one who signed):

```bash
ansible-sign project gpg-verify .
```

You should get confirmation that the **GPG signature** is valid and that the **checksums** match the current files. If you modify a file listed in `MANIFEST.in` without signing again, verification will fail (desired behavior).

More detail on errors: `ansible-sign --debug project gpg-verify .`

**Final result of this block (§6 — signing):** `MANIFEST.in` defined; project signed with `ansible-sign project gpg-sign`; successful verification with `ansible-sign project gpg-verify`; lab passphrase used uniformly when generating the key and when signing.

---

## Summary

1. Configure the `inventory` file in this folder with the host of your Fedora VM on OpenShift according to the lab access data and general information Excel (see the **Inventory** section before section 2).
2. Build the monolithic playbook following the steps in section 2.
3. Refactor with `tags` and `block` (section 3).
4. Extract to roles, centralize variables, and add handlers (section 4).
5. Validate with yamllint, ansible-lint, and Molecule (section 5).
6. Sign the project with `ansible-sign` and check the signature with `ansible-sign project gpg-verify` (section 6), using the shared lab passphrase.

The `deploy-wildfly.yaml` file in the repository is the result reference; the practice is to reproduce it, improve it structurally, and demonstrate quality with the tools above.

---

## Auxiliary commands

The inventory must already be configured as in the section **Inventory: Fedora VM host on OpenShift** (host and SSH identity matching the lab Excel).

```bash
ansible-playbook -i inventory deploy-wildfly.yaml
```

Manual checks after deployment (example):

```bash
ssh user1@10.234.2.26 -i ssh_tests_connections/id_fedora_new
curl localhost:8080/sample/
```

**Final result of this block (auxiliary commands):** playbook executed against the adjusted inventory; SSH session to the node possible with the indicated key; `curl` returns the sample app HTML (HTTP 200) if WildFly and the `/sample/` deployment are correct.
