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
2. **Prepares the operating system** by installing a JDK 17 or newer (required by WildFly 39) and utilities needed to unpack the package. On the lab Fedora 44 VMs the package is `java-25-openjdk-devel` (`java-21-openjdk-devel` is no longer in the repos).
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
    wf_java_package: java-25-openjdk-devel
```

**Result on the node (files / state):** steps 1 and 2 write nothing on the target; they only set the play scope and in-memory variables during execution.

**Final result of this block (steps 1–2 — header and variables):** inventory and play ready to run tasks; no persistent change on the host until the first task under `tasks:`.

### Step 3 — System dependencies

First task: install the appropriate JDK on the target node (Java 17+ for WildFly 39; on Fedora 44 use `java-25-openjdk-devel`), plus tools required to handle the compressed archive (for example `tar` and `gzip`).

```yaml
  tasks:
    - name: Instalar dependencias (Java 17+ es requerido para WF 39)
      ansible.builtin.dnf:
        name:
          - "{{ wf_java_package }}"
          - tar
          - gzip
        state: present
```

**Result on the node:** RPM packages installed (`java-25-openjdk-devel` on Fedora 44, `tar`, `gzip`); binaries available on the system PATH (`java`, `tar`, `gzip`).

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
        creates: "/opt/wildfly-{{ wf_version }}/bin/standalone.sh"
```

**Final result of this block (step 6 — extraction):** `/opt/wildfly-{{ wf_version }}/` exists (e.g. `/opt/wildfly-39.0.1.Final/`) with the tarball contents, UID/GID `wildfly`. The canonical path `/opt/wildfly` may not exist yet if this is the first install and the link is created in later steps.

### Step 7 — Clean the destination link or directory (if applicable)

If your design always reuses the same canonical path (`/opt/wildfly`), include a conditional task that removes that destination when you are not in check mode, consistent with how you want to manage upgrades or reinstalls.

```yaml
    - name: Comprobar si el destino de instalación existe
      ansible.builtin.stat:
        path: "{{ wf_install_dir }}"
      register: wildfly_install_dest_stat

    - name: Eliminar directorio destino si ya existe y no es link (Limpieza)
      ansible.builtin.file:
        path: "{{ wf_install_dir }}"
        state: absent
      when:
        - not ansible_check_mode
        - wildfly_install_dest_stat.stat.exists | default(false)
        - not (wildfly_install_dest_stat.stat.islnk | default(false))
```

**Final result of this block (step 7 — destination cleanup):** if `/opt/wildfly` existed as a **real directory** (not a symbolic link), it has been removed; the versioned directory `/opt/wildfly-{{ wf_version }}/` remains. If it was already a symlink, the task does not delete it (so reruns stay idempotent and do not disrupt the service). In `--check` mode the change is not applied either.

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

**Result on the node:** versioned directory `/opt/wildfly-39.0.1.Final/` with the full server tree (for example `bin/standalone.sh`, `standalone/configuration/standalone.xml`, `docs/contrib/scripts/systemd/`, etc.), owner `wildfly`. Symbolic link `/opt/wildfly` → `/opt/wildfly-39.0.1.Final`. After step 7, `/opt/wildfly` is only removed if it was a directory (not a symlink) before ensuring the link.

**Final result of this block (steps 6–8 — install and stable path):** WildFly product in `/opt/wildfly-<version>/` and also reachable as `/opt/wildfly` (symlink); ready for configuration and service setup.

### Step 9 — Listen on all interfaces

Modify `standalone.xml` of the already installed WildFly (via the link path) so the `public` interface uses `0.0.0.0` by default instead of `127.0.0.1`. In WildFly 39 that fragment spans **several lines**; a single-line `lineinfile` will not match. Use `replace` with a pattern that covers the real block:

```yaml
    - name: Configurar WildFly para que escuche en todas las IPs (0.0.0.0)
      ansible.builtin.replace:
        path: "{{ wf_install_dir }}/standalone/configuration/standalone.xml"
        regexp: '<interface name="public">\s*<inet-address value="\$\{jboss\.bind\.address:127\.0\.0\.1\}"/>\s*</interface>'
        replace: '        <interface name="public"><inet-address value="${jboss.bind.address:0.0.0.0}"/></interface>'
```

**Result on the node:** in `/opt/wildfly/standalone/configuration/standalone.xml` (via the link), the `public` interface fragment has default `inet-address` `0.0.0.0` instead of `127.0.0.1`, so the server can listen on all network interfaces.

**Final result of this block (step 9 — network / bind):** persistent configuration in `standalone.xml` to expose the `public` interface on all IPs; full effect after the next WildFly process start (or service restart).

### Step 10 — Startup script for systemd

Copy the `launch.sh` script from the documentation included in the installation into the WildFly `bin` tree, keeping execute permissions.

```yaml
    - name: Copiar script launch.sh para systemd
      ansible.builtin.copy:
        src: "{{ wf_install_dir }}/docs/contrib/scripts/systemd/launch.sh"
        dest: "{{ wf_install_dir }}/bin/launch.sh"
        remote_src: yes
        mode: '0755'
```

### Step 11 — systemd unit

Copy the `wildfly.service` unit file to the system systemd units directory.

```yaml
    - name: Instalar el archivo de servicio systemd
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
          - "{{ wf_java_package }}"
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

Optional: add a `.yamllint` file at the root to relax or tighten rules according to the course standard. The examples in this guide include style nits (see **Intentional nits** below).

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

Fix the warnings the instructor marks as mandatory to pass the exercise. This course includes **intentional nits** (see the box below): the playbook can deploy successfully and still fail lint.

**Final result of this block (5.2 — ansible-lint):** run with exit code `0` (or only warnings accepted by the instructor); playbooks and roles pass the configured quality rules (FQCN, task names, idempotence, etc.).

### Intentional nits (yamllint and ansible-lint)

The example YAML in sections 2–4 includes **deliberate style errors**. They do not break execution in Dev Spaces; `yamllint` and `ansible-lint` must flag them. Find and fix them until you get exit code `0`.

| Nit | Where to copy / look | Tool and rule |
| --- | -------------------- | ------------- |
| `remote_src: yes` (truthy `yes`/`no` instead of `true`/`false`) | `unarchive` and `copy` with `remote_src` | yamllint `truthy` / ansible-lint `yaml[truthy]` |
| Handler names that do not start with an uppercase letter (`recargar systemd`, `reiniciar wildfly`) | `roles/wildfly_systemd/handlers/main.yml` | ansible-lint `name[casing]` |
| `copy` / `file` tasks without `mode` | `wildfly.service` unit, `/etc/wildfly` directory, `wildfly.conf` | ansible-lint `risky-file-permissions` |
| Role YAML without a `---` header | e.g. `roles/wildfly_install/defaults/main.yml` | yamllint `document-start` |
| Trailing whitespace on a line | `group_vars/servers.yml` (`wf_url` line) | yamllint `trailing-spaces` |

Fix those warnings in playbooks, roles, and `group_vars` **before** running Molecule. The scenario runs `yamllint` and `ansible-lint` in the `prepare` step; if the nits remain, `molecule test` will fail there. You do not need to change the Molecule YAML files to clear them.

### 5.3 Molecule (playbook test)

Molecule runs the playbook against a test environment and a verification playbook. In this exercise **you** create the `molecule/` tree (it is not shipped in the repository). There are two scenarios:

| Scenario | Use in the lab |
| -------- | -------------- |
| `default` | **delegated** driver: `create.yml` provisions a Fedora VM on OpenShift/KubeVirt, `converge` applies the playbook, and `destroy` removes the VM. |
| `with_existin_machine` | Reuses the Fedora VM already assigned to you (the one in `inventory`). `create`/`destroy` do not create or delete the machine. This is the scenario you should run in class. |

The `molecule test` sequence is: `destroy` → `create` → **`prepare`** (`yamllint` and `ansible-lint`) → `converge` → `verify` → `destroy`.

Installation (usually already in the Dev Spaces image; if not):

```bash
pip install molecule molecule-plugins ansible
```

Create the directories for both scenarios:

```bash
mkdir -p molecule/default molecule/with_existin_machine
```

Keep three things aligned in every scenario: `converge.yml` must import `deploy-wildfly.yaml` (or the role-based playbook); the Molecule inventory must declare the `servers` group; `verify.yml` checks the `wildfly` service, port **8080**, and the `/sample/` URL.

#### 5.3.1 Scenario `default` — test VM on OpenShift

##### Step 1 — `molecule/default/molecule.yml`

Define the delegated driver, platform, `servers` group inventory, and the test sequence including `prepare` (lint).

```yaml
---
dependency:
  name: galaxy
driver:
  name: delegated
platforms:
  - name: fedora-chocolate-smelt-74
provisioner:
  name: ansible
  inventory:
    hosts:
      all:
        children:
          servers:
            hosts:
              fedora-chocolate-smelt-74: {}
    host_vars:
      fedora-chocolate-smelt-74:
        ansible_user: fedora
        ansible_ssh_common_args: "-o StrictHostKeyChecking=no"
verifier:
  name: ansible
scenario:
  test_sequence:
    - destroy
    - create
    - prepare
    - converge
    - verify
    - destroy
```

**Result in the project:** Molecule recognizes the `default` scenario; the play `hosts: servers` resolves to the test host.

##### Step 2 — `molecule/default/molecule_vars.yml`

OpenShift credentials for `create.yml` / `destroy.yml`. Replace URL, user, and password with those from your assignment (lab Excel). **Do not** push real secrets to a public remote.

```yaml
---
ocp_url: "https://api.tu-cluster.com:6443"
ocp_user: "admin"
ocp_pass: "mi_password_secreto"
```

**Result in the project:** `ocp_*` variables available for the creation playbook.

##### Step 3 — `molecule/default/create.yml`

Creates the Fedora VM with KubeVirt and waits for SSH. Requires authenticated `oc` and the `kubevirt.core` / `kubernetes.core` collections.

```yaml
---
- name: Create VM in OpenShift
  hosts: localhost
  gather_facts: false
  vars_files:
    - molecule_vars.yml
  vars:
    password: "{{ ocp_pass | default(omit) }}"
  tasks:
    - name: Log in to OpenShift
      ansible.builtin.command:
        cmd: oc login --insecure-skip-tls-verify -u {{ ocp_user }} -p {{ password }} {{ ocp_url }}
      changed_when: false

    - name: Get OpenShift API token
      ansible.builtin.command:
        cmd: oc whoami --show-token
      register: token
      changed_when: false

    - name: Create Fedora VM using KubeVirt
      kubevirt.core.kubevirt_vm:
        host: "{{ ocp_url }}"
        api_key: "{{ token.stdout }}"
        state: present
        namespace: my-namespace
        name: "{{ item.name }}"
        spec:
          running: true
          template:
            spec:
              domain:
                devices:
                  interfaces:
                    - name: default
                      masquerade: {}
                  disks:
                    - name: containerdisk
                      disk: {bus: virtio}
                resources:
                  requests:
                    memory: 2Gi
              volumes:
                - name: containerdisk
                  containerDisk:
                    image: quay.io/containerdisks/fedora:latest
      loop: "{{ molecule_yml.platforms }}"

    - name: Wait for SSH to be ready
      ansible.builtin.wait_for:
        host: "{{ item.address | default('localhost') }}"
        port: 22
        timeout: 300
      loop: "{{ molecule_yml.platforms }}"
```

Adjust `namespace`, `ansible_user`, and the real VM IP/DNS when the lab provides them. Without a node reachable over SSH, `converge` cannot apply the playbook.

**Result on OpenShift:** VM `fedora-chocolate-smelt-74` present in the namespace; SSH on port 22.

##### Step 4 — `molecule/default/destroy.yml`

Removes the VM and, optionally, an associated Service.

```yaml
---
- name: Destroy VM in OpenShift
  hosts: localhost
  gather_facts: false
  vars_files:
    - molecule_vars.yml
  tasks:
    - name: Remove Fedora VM from OpenShift
      kubevirt.core.kubevirt_vm:
        host: "{{ ocp_url }}"
        state: absent
        namespace: my-namespace
        name: "{{ item.name }}"
        wait: true
        wait_timeout: 300
      loop: "{{ molecule_yml.platforms }}"
      ignore_errors: true

    - name: Clean up associated resources
      kubernetes.core.k8s:
        host: "{{ ocp_url }}"
        state: absent
        namespace: my-namespace
        kind: "{{ item.kind }}"
        name: "{{ item.name }}"
      loop:
        - {kind: Service, name: "svc-{{ molecule_yml.platforms[0].name }}"}
      ignore_errors: true
```

**Result on OpenShift:** the test VM (and the Service if it existed) are gone; `ignore_errors` keeps the scenario from failing if the VM was never created.

##### Step 5 — `molecule/default/prepare.yml` (yamllint and ansible-lint)

This playbook is Molecule’s hook **after `create` and before `converge`**. It runs the same checks as sections 5.1 and 5.2, so `molecule test` does not continue if YAML or Ansible practices fail.

```yaml
---
- name: Lint YAML and Ansible before converge
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    project_dir: "{{ lookup('env', 'MOLECULE_PROJECT_DIRECTORY') }}"
  tasks:
    - name: Run yamllint on the project
      ansible.builtin.command:
        cmd: yamllint .
        chdir: "{{ project_dir }}"
      changed_when: false

    - name: Run ansible-lint on the project
      ansible.builtin.command:
        cmd: ansible-lint .
        chdir: "{{ project_dir }}"
      changed_when: false
```

If `yamllint .` complains about Molecule’s cache (`.cache/`), add a `.yamllint` at the project root that `ignore`s `.cache/` and `.ansible-sign/` (see 5.1).

**Result in the project:** `molecule prepare` (and the `prepare` step of `molecule test`) exits `0` only if yamllint and ansible-lint pass.

##### Step 6 — `molecule/default/converge.yml`

Apply the real exercise playbook, not a placeholder.

```yaml
---
- name: Converge
  ansible.builtin.import_playbook: ../../deploy-wildfly.yaml
```

**Result on the test node:** the same state as running `ansible-playbook -i inventory deploy-wildfly.yaml` (WildFly, service, and sample WAR).

##### Step 7 — `molecule/default/verify.yml`

Check service, port, and sample application.

```yaml
---
- name: Verify WildFly deployment
  hosts: servers
  become: true
  gather_facts: false
  tasks:
    - name: Check if WildFly service is running
      ansible.builtin.systemd:
        name: wildfly
        state: started
      check_mode: true
      register: service_status
      failed_when: service_status.changed

    - name: Wait for WildFly to listen on port 8080
      ansible.builtin.wait_for:
        port: 8080
        timeout: 60

    - name: Verify application sample.war is accessible
      ansible.builtin.uri:
        url: http://localhost:8080/sample/
        status_code: 200
      register: app_check
      retries: 5
      delay: 10
      until: app_check.status == 200
```

**Result on the node:** `wildfly` active, port 8080 listening, and HTTP 200 on `/sample/`.

**Final result of this block (5.3.1 — `default` scenario):** `molecule/default/` tree with `molecule.yml`, `molecule_vars.yml`, `create.yml`, `destroy.yml`, `prepare.yml`, `converge.yml`, and `verify.yml`.

#### 5.3.2 Scenario `with_existin_machine` — lab VM

Uses the Fedora VM you already configured under **Inventory**. Copy `prepare.yml` and `verify.yml` from the `default` scenario (same lint and same assertions). `converge.yml` is identical (imports `deploy-wildfly.yaml`).

##### Step 8 — `molecule/with_existin_machine/molecule.yml`

Driver `default` with `managed: false`: Molecule does not provision an instance. `ansible_host` must match the `inventory` file (lab Excel). If you use a local SSH tunnel in Dev Spaces, keep `127.0.0.1` and the forwarded port.

```yaml
---
dependency:
  name: galaxy
driver:
  name: default
  options:
    managed: false
platforms:
  - name: fedora-user1
provisioner:
  name: ansible
  config_options:
    defaults:
      roles_path: ${MOLECULE_PROJECT_DIRECTORY}/roles
      host_key_checking: false
      interpreter_python: auto_silent
  inventory:
    hosts:
      all:
        children:
          servers:
            hosts:
              fedora-user1: {}
    host_vars:
      fedora-user1:
        ansible_user: user1
        ansible_host: 127.0.0.1
        ansible_port: 2222
        ansible_ssh_private_key_file: "{{ lookup('env', 'MOLECULE_PROJECT_DIRECTORY') }}/ssh_tests_connections/id_fedora_new"
        ansible_ssh_common_args: "-o StrictHostKeyChecking=no"
verifier:
  name: ansible
scenario:
  test_sequence:
    - destroy
    - create
    - prepare
    - converge
    - verify
    - destroy
```

**Result in the project:** the `servers` group points to `fedora-user1` with the same SSH identity as the course inventory.

##### Step 9 — `molecule/with_existin_machine/create.yml`

```yaml
---
- name: Create (delegated — the lab VM already exists)
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Confirm that a new VM is not created
      ansible.builtin.debug:
        msg: >-
          Default (delegated) driver with managed=false.
          Reusing lab instance {{ molecule_yml.platforms[0].name }}.
```

**Result on the node:** none; only a message. The lab VM is unchanged.

##### Step 10 — `molecule/with_existin_machine/destroy.yml`

```yaml
---
- name: Destroy (delegated — the lab VM is not deleted)
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Keep the exercise Fedora VM
      ansible.builtin.debug:
        msg: >-
          Not destroying {{ molecule_yml.platforms[0].name }}.
          The instance belongs to the lab and is managed outside Molecule.
```

**Result on the node:** none; the student’s Fedora VM is **not** powered off or deleted.

##### Step 11 — Remaining scenario files

Create:

- `molecule/with_existin_machine/prepare.yml` — same content as **step 5**.
- `molecule/with_existin_machine/converge.yml` — same content as **step 6**.
- `molecule/with_existin_machine/verify.yml` — same content as **step 7**.

**Final result of this block (5.3.2 — `with_existin_machine` scenario):** `molecule/with_existin_machine/` tree with `molecule.yml`, `create.yml`, `destroy.yml`, `prepare.yml`, `converge.yml`, and `verify.yml`; lint and functional checks identical to `default`, without creating or destroying the classroom VM.

#### 5.3.3 Run the Molecule tests

From the **project root** (next to `deploy-wildfly.yaml`).

Default scenario (`default`, creates/destroys an OpenShift VM; only if the instructor asks and you have credentials):

```bash
molecule test
```

Classroom scenario (existing VM; the one you should use in the lab):

```bash
molecule test -s with_existin_machine
```

Manual sequence (debugging), same `-s` if it is not `default`:

```bash
molecule create -s with_existin_machine
molecule prepare -s with_existin_machine
molecule converge -s with_existin_machine
molecule verify -s with_existin_machine
molecule destroy -s with_existin_machine
```

`molecule prepare` is the step that runs **yamllint** and **ansible-lint**. If it fails, fix the nits from 5.1/5.2 (or `.yamllint`) before `converge`.

**Final result of this block (5.3 — Molecule):** both scenarios created on disk; `molecule test -s with_existin_machine` completes `destroy` → `create` → `prepare` (lint) → `converge` → `verify` → `destroy` with exit code `0`; the playbook is applied on the lab VM and `verify.yml` confirms service, port, and URL. If you use `default`, the OpenShift VM is also created and then removed.

**Final result of this block (§5 — quality):** repeatable local pipeline: valid YAML (yamllint), Ansible best practices (ansible-lint) — first by hand (5.1–5.2) and again **inside** Molecule (`prepare`) — and an end-to-end test aligned with WildFly and `/sample/`.

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
