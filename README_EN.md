# lab-devspaces-ansible-exercise1

Hands-on course on Ansible playbook development. **This exercise is designed to be completed inside OpenShift Dev Spaces**. The classroom Fedora VM is reachable over SSH from that workspace.

Image versions (check with `python3 --version`, `ansible --version`, `molecule --version`, `yamllint --version`, `ansible-lint --version`):

| Tool | Version in Dev Spaces |
| ---- | --------------------- |
| Python | **3.12** |
| ansible-core | **2.21.x** |
| yamllint | **1.38.x** |
| ansible-lint | **26.x** (e.g. 26.6.0) |
| Molecule | **26.x** (e.g. 26.6.0); driver **`default`** (`delegated` does not exist) |
| ansible-sign, `oc` | Included in the image |

You do not need to install these tools by hand in the workspace. The `pip install yamllint` / `ansible-lint` / `molecule` commands below apply only if one of them is missing.

**The repository does not include `deploy-wildfly.yaml`.** You must **create it yourself** at the project root (same level as this README) by copying and assembling the YAML snippets from the sections below. This document is the guide to build it, refactor it, and validate it with quality tools.

---

## Environment setup

```bash
chmod 600 ssh_tests_connections/id_fedora_new
ansible-galaxy collection install community.general
```

Run `chmod 600` **again every time you reopen the workspace**: Git and the project volume restore the key as mode `664`/`644`, and SSH/Ansible will reject it. The collection is installed under `~/.ansible/collections` in the pod; if the workspace is recreated from scratch, install it again.

Also create an `ansible.cfg` at the project root. On the lab Fedora 44 VMs Ansible discovers `/usr/bin/python3.14` and warns on every task; `auto_silent` quiets that. `host_key_checking = False` avoids the first-connection host-key prompt from Dev Spaces:

```ini
[defaults]
host_key_checking = False
interpreter_python = auto_silent
roles_path = ./roles
retry_files_enabled = False
```

In the Dev Spaces (Che/VS Code) terminal you will often see `WARNING: Module invocation had junk after the JSON data` plus an OSC `]3008;…` sequence. That is terminal-integration noise, not a playbook failure; ignore it.

**Final result of this block (setup):** SSH key with restrictive permissions so SSH and Ansible accept it (re-applied after a workspace restart); `community.general` collection available on the controller; `ansible.cfg` ready for Python 3.14 and the first SSH.

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

In the examples in this guide there are commented **firewalld** tasks; you can enable them in your version if the environment requires it.

**Final result of this block (§1 — overview):** after running the playbook you have been building against `servers`, the node has WildFly installed under `/opt`, a `wildfly` service managed by systemd, network listen (public interface `0.0.0.0`), and a sample application reachable over HTTP at the `/sample/` context (default port 8080), unless the firewall blocks external access.

---

## Inventory: Fedora VM host on OpenShift

Before **section 2 (step-by-step guide for the monolithic playbook)**, you must adapt the `inventory` file in **the same folder as this README**. The play targets the `[servers]` group; that is where you define which machine Ansible will run against and which SSH user and key it will use.

The host details for your **Fedora virtual machine** (name, IP or address reachable from OpenShift Dev Spaces, SSH user if it differs from the template, and so on) are in **your lab user access data** (Excel or handout you were given). Host and IP values in this guide are **examples only**: do not copy them as-is. Replace `ansible_host` (and, if the document or instructor says so, `ansible_user` or the host alias in the first column) with **your** assignment. Keep the `ansible_ssh_private_key_file` path aligned with the key you prepared in “Environment setup” (for example `ssh_tests_connections/id_fedora_new`).

Reference file template (`fedora-user1` and the IP placeholder are examples):

```ini
[servers]
fedora-user1 ansible_host=<IP_from_your_lab_access_data> ansible_user=user1 ansible_ssh_private_key_file=ssh_tests_connections/id_fedora_new
```

Without a correct inventory, `ansible-playbook -i inventory …` will not be able to reach your VM. Check SSH connectivity from the workspace before continuing with the guide.

In this lab the Fedora VM is reachable **directly** from Dev Spaces (the IP from your access data, port **22**). Do not use `127.0.0.1` or port `2222` unless the instructor asked for an explicit SSH tunnel: those values make Ansible and Molecule fail.

**Final result of this block (inventory):** `inventory` file with `ansible_host` (and other fields if applicable) consistent with **your lab user access data**; the `servers` group resolves to your Fedora VM for later playbook runs.

---

## 2. Step-by-step guide (first monolithic playbook)

Goal: build `deploy-wildfly.yaml` at the project root (the file **is not** in the repository), understanding the **logical order** and **purpose** of each block. This guide does not repeat the documentation of every Ansible module; consult the official module documentation the first time you use it.

After each step, the **concrete YAML** you must copy and accumulate into `deploy-wildfly.yaml` is shown. At the end of each **logical block**, the **resulting state** on the node is summarized (files, services, or no on-disk changes).

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

**Result on the node:** `/etc/group` entry for `wildfly`; `/etc/passwd` (and shadow) entry for `wildfly` with the previous group’s GID, home declared as `/opt/wildfly`, and shell `/sbin/nologin`. The `user` module with `home: "{{ wf_install_dir }}"` **creates `/opt/wildfly` as a real directory** (not a link). That is why step 7 cleanup removes it on the **first** run: not a bug, it is the intended order (identity → versioned extract → remove the home directory → symlink).

**Final result of this block (steps 4–5 — service identity):** system account ready to run WildFly: `wildfly` group and user created; `/opt/wildfly` may already exist as an empty home directory until step 7.

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

**Final result of this block (step 7 — destination cleanup):** if `/opt/wildfly` existed as a **real directory** (not a symbolic link), it has been removed; the versioned directory `/opt/wildfly-{{ wf_version }}/` remains. On the first run this almost always happens, because step 5 just created that path as the user home. If it was already a symlink, the task does not delete it (so reruns stay idempotent and do not disrupt the service). In `--check` mode the change is not applied either.

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

**Result on the node:** versioned directory `/opt/wildfly-39.0.1.Final/` with the full server tree (for example `bin/standalone.sh`, `standalone/configuration/standalone.xml`, `docs/contrib/scripts/systemd/`, etc.), owner `wildfly`. Symbolic link `/opt/wildfly` → `/opt/wildfly-39.0.1.Final`. The **link** itself may stay `root:root` even if you set `owner`/`group` on the task (`state: link` does not always apply UID/GID to the symlink); the versioned tree should still be `wildfly`. That does not stop the service. After step 7, `/opt/wildfly` is only removed if it was a directory (not a symlink) before ensuring the link.

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

`community.general.archive` is **not idempotent**: each run rebuilds the ZIP (different metadata/checksum) and the copy to the node usually reports `changed` even if the HTML did not change. That is expected; it does not mean deployment failed.

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

Concrete example (same block as step 15, already present in the playbook you are building):

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
| `wildfly_systemd`    | `launch.sh`, `wildfly.service`, `wildfly.conf.j2` template, start/enable. |
| `wildfly_sample_app` | `files/index.html`, local WAR packaging and copy to deployments.          |


You can merge roles if you prefer less granularity; what matters is that each role has a clear responsibility.

**Result in the project (files):** indicative tree after creating the roles (file names follow Ansible convention):

```text
roles/
  wildfly_os_deps/tasks/main.yml
  wildfly_account/tasks/main.yml
  wildfly_install/tasks/main.yml
  wildfly_bind/tasks/main.yml
  wildfly_systemd/tasks/main.yml
  wildfly_systemd/templates/wildfly.conf.j2
  wildfly_sample_app/tasks/main.yml
  wildfly_sample_app/files/index.html
deploy-wildfly.yaml   # or site.yml that imports roles
```

### 4.2 Variables

`ansible-lint` 26.x (`var-naming[no-role-prefix]`) **requires** variables defined **inside** a role to use that role’s prefix (`wildfly_install_…`, `wildfly_systemd_…`, and so on). If you copy `wf_version` / `wf_user` into `roles/*/defaults/main.yml`, lint **fails** even when the playbook deploys correctly.

In this exercise the practical approach is:

1. Keep **shared** variables (`wf_version`, `wf_install_dir`, `wf_user`, `wf_group`, `wf_url`, `wf_java_package`) in `group_vars/servers.yml` (the role-prefix rule does not apply there).
2. In a role’s `defaults/main.yml`, only **role-owned** variables that already have the prefix (for example `wildfly_systemd_bind` in `wildfly_systemd`).

Concrete example (`group_vars/servers.yml`):

```yaml
---
wf_version: "39.0.1.Final"
wf_install_dir: "/opt/wildfly"
wf_user: "wildfly"
wf_group: "wildfly"
wf_url: "https://github.com/wildfly/wildfly/releases/download/{{ wf_version }}/wildfly-{{ wf_version }}.tar.gz"
wf_java_package: java-25-openjdk-devel
```

If you prefer per-role defaults, rename each key with the role prefix and update the tasks. Do not leave bare `wf_*` names in `roles/*/defaults/main.yml`.

**Result on the node:** the same as in the monolithic guide; variables only change **where** they are defined (group_vars vs role vs play). If `group_vars` overrides `wf_version`, the tree under `/opt` will use the new version in paths and URL.

### 4.3 Handlers

Replace or complement tasks that currently mix “change a file” and “restart a service” with the `notify` pattern:

- Handler `reload systemd`: reloads the daemon when units under `/etc/systemd/system` change.
- Handler `restart wildfly`: restarts the service when `wildfly.conf`, `launch.sh`, or files under `standalone/configuration` that require a restart change.

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

### 4.5 Static files (`files/`) and Jinja2 templates (`templates/`)

Once the playbook is split into roles, stop treating `index.html` and `wildfly.conf` as loose paths at the project root. Ansible looks up static files in the role’s `files/` directory and Jinja2 templates in `templates/`. The `copy` module with a `src` that has no directory resolves the file inside `files/`; `template` does the same with `templates/` and also interpolates variables.

#### Step 1 — `index.html` in `files/` of the `wildfly_sample_app` role

Move `index.html` from the project root to `roles/wildfly_sample_app/files/index.html` (same HTML content as step 15). In the sample-application block, first copy that file to the controller (`delegate_to: localhost`, `become: false`) and then package it as a WAR, as in the monolith.

```yaml
    - name: Crear y desplegar la aplicación de ejemplo
      tags: [app]
      block:
        - name: Copiar index.html desde files/ del rol
          ansible.builtin.copy:
            src: index.html
            dest: /tmp/index.html
            mode: "0644"
          delegate_to: localhost
          become: false

        - name: Empaquetar WAR localmente
          community.general.archive:
            path: /tmp/index.html
            dest: /tmp/sample.war
            format: zip
            mode: "0644"
          delegate_to: localhost
          become: false

        - name: Copiar WAR al directorio de despliegue
          ansible.builtin.copy:
            src: /tmp/sample.war
            dest: "{{ wf_install_dir }}/standalone/deployments/sample.war"
            owner: "{{ wf_user }}"
            group: "{{ wf_group }}"
            mode: "0644"
```

You do not need to put `roles/wildfly_sample_app/files/` in `src`: Ansible finds the file because the task lives in that role.

**Result on the node:** on the controller, `/tmp/index.html` (copy of the role file) and `/tmp/sample.war`. On the target, `/opt/wildfly/standalone/deployments/sample.war` owned by `wildfly`; the `/sample/` context still serves the same HTML.

**Final result of this block (4.5 step 1 — `files/`):** the sample HTML lives in `roles/wildfly_sample_app/files/index.html`; the WAR is built as in step 15, but the source is no longer the repository root.

#### Step 2 — `wildfly.conf` as a Jinja2 template in `wildfly_systemd`

Replace the `remote_src` copy of the distribution’s `wildfly.conf` with a `template` rendered from `roles/wildfly_systemd/templates/wildfly.conf.j2`. Paths, the service user, and the bind address come from role variables (`defaults/main.yml` or `group_vars`).

Contents of `roles/wildfly_systemd/templates/wildfly.conf.j2`:

```jinja
# {{ ansible_managed }}
JBOSS_HOME={{ wildfly_systemd_install_dir }}
JBOSS_USER={{ wildfly_systemd_user }}
WILDFLY_CONFIG={{ wildfly_systemd_config }}
WILDFLY_MODE={{ wildfly_systemd_mode }}
WILDFLY_BIND={{ wildfly_systemd_bind }}
```

Typical defaults in `roles/wildfly_systemd/defaults/main.yml` (the `wildfly_systemd_` prefix is **required** for `var-naming[no-role-prefix]`; do not mix `wf_install_dir` / `wf_user` here):

```yaml
---
wildfly_systemd_install_dir: "/opt/wildfly"
wildfly_systemd_user: "wildfly"
wildfly_systemd_config: standalone.xml
wildfly_systemd_mode: standalone
wildfly_systemd_bind: "0.0.0.0"
```

Task that renders the file and notifies handlers (replaces the remote `copy` of `wildfly.conf`):

```yaml
    - name: Desplegar wildfly.conf desde plantilla Jinja2
      ansible.builtin.template:
        src: wildfly.conf.j2
        dest: /etc/wildfly/wildfly.conf
        mode: "0644"
        owner: root
        group: root
      notify:
        - recargar systemd
        - reiniciar wildfly
```

`src: wildfly.conf.j2` resolves under the role’s `templates/`. If you change `wildfly_systemd_bind` (or another template variable) and run the play again, the file changes and the handlers reload systemd and restart WildFly.

**Result on the node:** `/etc/wildfly/wildfly.conf` generated from the template (`ansible_managed` comment, `JBOSS_HOME=/opt/wildfly`, `JBOSS_USER=wildfly`, `WILDFLY_BIND=0.0.0.0`, and so on). The `wildfly` service uses that `EnvironmentFile`; a template change triggers a restart via handlers.

**Final result of this block (4.5 step 2 — `templates/`):** service configuration is no longer copied from the tarball; it is a repository artifact parameterized by variables.

**Final result of this block (§4 — roles):** on the target disk, the same result as **Final result of this block (§2)** if the roles replicate the same tasks and variables, with `/etc/wildfly/wildfly.conf` rendered by Jinja2 and the WAR built from `files/index.html`. In the **project**: `roles/` directory with `tasks/main.yml`, `defaults/main.yml`, and, if applicable, `handlers/main.yml`, `files/`, and `templates/`; a short playbook that only orders roles and optionally `group_vars` / `vars`.

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

Optional but **recommended**: add a `.yamllint` at the root. A plain `extends: default` **is not compatible** with ansible-lint 26.x: it requires specific rules (`comments.min-spaces-from-content: 1`, `comments-indentation: false`, `braces.max-spaces-inside: 1`, `octal-values.forbid-implicit-octal` / `forbid-explicit-octal: true`). Without them, ansible-lint warns about an «incompatible custom yamllint configuration» and will not offer `fix`. Use a template like this (relax `line-length` for URLs and the `standalone.xml` regexp; ignore files you did not author):

```yaml
---
extends: default

ignore: |
  .cache/
  .ansible-sign/
  devfile.yaml
  ssh_tests_connections/

rules:
  comments:
    min-spaces-from-content: 1
  comments-indentation: false
  braces:
    max-spaces-inside: 1
  octal-values:
    forbid-implicit-octal: true
    forbid-explicit-octal: true
  line-length:
    max: 160
    allow-non-breakable-words: true
  truthy:
    allowed-values: ["true", "false"]
```

The examples in this guide include style nits (see **Intentional nits** below).

**Final result of this block (5.1 — yamllint):** output with no errors (exit code `0`) or a list of files/lines to fix according to your `.yamllint`; the project YAML meets the course style rules and is compatible with ansible-lint.

### 5.2 ansible-lint

Analyzes playbooks and roles against Ansible best practices (names, `fqcn`, use of `become`, idempotence, etc.).

Installation:

```bash
pip install ansible-lint
```

Execution (covers the **whole project**: playbook, roles, and `group_vars`; `ansible-lint .` may skip roles and variables and report a false 0):

```bash
# After the monolithic playbook (no roles yet):
ansible-lint deploy-wildfly.yaml

# With roles and group_vars (full exercise validation):
ansible-lint deploy-wildfly.yaml roles group_vars
```

Fix the warnings the instructor marks as mandatory to pass the exercise. This course includes **intentional nits** (see the box below): the playbook can deploy successfully and still fail lint.

**Final result of this block (5.2 — ansible-lint):** run with exit code `0` (or only warnings accepted by the instructor); playbooks and roles pass the configured quality rules (FQCN, task names, idempotence, etc.).

### Intentional nits (yamllint and ansible-lint)

The example YAML in sections 2–4 includes **deliberate style errors**. They do not break execution in Dev Spaces; `yamllint` and `ansible-lint` must flag them.

The table below is **only an example** of common warnings. **It is not a closed list**: the tools may report more rules (`var-naming`, `line-length`, `key-order`, permissions on other `copy`/`file` tasks, the repo `devfile.yaml`, and so on). Review **the full output**, find each failure in your tree, and fix it until you get exit code `0`.

| Nit (example) | Where to copy / look | Tool and rule |
| ------------- | -------------------- | ------------- |
| `remote_src: yes` (truthy `yes`/`no` instead of `true`/`false`) | `unarchive` and `copy` with `remote_src` | yamllint `truthy` / ansible-lint `yaml[truthy]` |
| Handler names that do not start with an uppercase letter (`recargar systemd`, `reiniciar wildfly`) | `roles/wildfly_systemd/handlers/main.yml` | ansible-lint `name[casing]` |
| `copy` / `file` tasks without `mode` | `wildfly.service` unit, `/etc/wildfly` directory, `wildfly.conf`, WAR packaging | ansible-lint `risky-file-permissions` |
| Role YAML without a `---` header | e.g. a `defaults/main.yml` copied without `---` | yamllint `document-start` |
| Trailing whitespace on a line | `group_vars/servers.yml` (`wf_url` line) | yamllint `trailing-spaces` |
| `wf_version` / `wf_user` / etc. in `roles/*/defaults/main.yml` | each role’s defaults (the old `wildfly_install` example) | ansible-lint `var-naming[no-role-prefix]` |
| URL lines or the `standalone.xml` `regexp` longer than 80 characters | `vars`, `group_vars`, `replace` task | yamllint `line-length` (relax it in `.yamllint` or wrap the line) |

Fix **all** warnings (those in the table and any others that appear) in playbooks, roles, and `group_vars` **before** running Molecule. The scenario runs `yamllint` and `ansible-lint` in the `prepare` step; if failures remain, `molecule test` will fail there. You do not need to change the Molecule YAML files to clear playbook nits.

### 5.3 Molecule (playbook test)

Molecule runs the playbook against a test environment and a verification playbook. In this exercise **you** create the `molecule/` tree (it is not shipped in the repository).

The Dev Spaces image includes **Molecule 26.x** (e.g. 26.6.0) with ansible-core **2.21**. The driver is named `default` (the old name `delegated` **no longer exists**; if you use it, `molecule` fails when loading scenarios).

You can **define both scenarios** in the project. They differ in where the machine comes from:

| Scenario | Test machine | What `create` / `destroy` do | Where to run it |
| -------- | ------------ | ---------------------------- | --------------- |
| `default` | Fedora VM **created inside OpenShift** (KubeVirt), `fedora-mol-<user>` | `create.yml` provisions the VM (cloud-init and SSH key); `destroy.yml` removes it at the end. | **Only from Dev Spaces**, after you replace the API URL, user, password, and namespace `virtualization-test-<user>` (see 5.3.1). |
| `with_existing_machine` | **Pre-started** lab Fedora VM (the one in `inventory`) | Does not create or delete the machine; reuses the instance already running. | From Dev Spaces, against the inventory Fedora. **This is the scenario you must complete** in class. |

The `molecule test` sequence is: `destroy` → `create` → **`prepare`** (`yamllint` and `ansible-lint`) → `converge` → `verify` → `destroy`.

Installation (usually already in the Dev Spaces image; if not):

```bash
pip install molecule molecule-plugins ansible
```

Create the directories for both scenarios:

```bash
mkdir -p molecule/default molecule/with_existing_machine
```

Keep three things aligned in every scenario: `converge.yml` must import `deploy-wildfly.yaml` (or the role-based playbook); the Molecule inventory must declare the `servers` group; `verify.yml` checks the `wildfly` service, port **8080**, and the `/sample/` URL.

#### 5.3.1 Scenario `default` — test VM on OpenShift

This scenario runs **only from Dev Spaces**. It creates a new Fedora VM with KubeVirt, injects the lab public key through cloud-init, waits for the VMI IP, and applies the playbook over SSH. The YAML in the steps below is what makes the VM reachable: replace only the placeholders in the table.

| Placeholder | Where | Value to put |
| ----------- | ----- | ------------ |
| `<user>` | Platform name in `molecule.yml` (all three places) and the path `/tmp/molecule-default-<user>.ip` in `molecule.yml` and `create.yml` | Your lab username, **the same** in every place. If you are `user2`, the VM is `fedora-mol-user2` and the file is `/tmp/molecule-default-user2.ip`. |
| `ocp_url` | `molecule_vars.yml` | API URL, in the form `https://api.tu-cluster.com:6443` |
| `ocp_user` | `molecule_vars.yml` | `<lab_username>` (the same user as `<user>`) |
| `ocp_pass` | `molecule_vars.yml` | `<lab_password>` |
| `ocp_namespace` | `molecule_vars.yml` | `virtualization-test-<lab_username>` |

The first step of `molecule test` is `destroy`, so `molecule_vars.yml` must be filled in before any command of this scenario. That file holds the OpenShift username and password: **do not** push it to Gitea or any public remote. Exclude it from `MANIFEST.in`.

Cloud-init installs `ssh_tests_connections/id_fedora_new.pub` (it ships in the repository). The SSH user of this VM is `fedora`, the user of the `quay.io/containerdisks/fedora` image. The platform is named `fedora-mol-<user>` and lives in `virtualization-test-<user>`, the same project as the inventory Fedora (`fedora-<user>`). `destroy` removes only `fedora-mol-<user>`.

##### Step 1 — `molecule/default/molecule.yml`

Define the `default` driver (Molecule 26.x in the lab image), the platform, the `servers` group inventory, and the test sequence including `prepare` (lint). `ansible_host` reads the IP that `create.yml` writes.

```yaml
---
dependency:
  name: galaxy
  options:
    requirements-file: requirements.yml
driver:
  name: default
platforms:
  - name: fedora-mol-<user>
provisioner:
  name: ansible
  config_options:
    defaults:
      roles_path: ${MOLECULE_PROJECT_DIRECTORY}/roles
      collections_path: ~/.ansible/collections
      host_key_checking: false
      interpreter_python: auto_silent
  inventory:
    hosts:
      all:
        children:
          servers:
            hosts:
              fedora-mol-<user>: {}
    host_vars:
      fedora-mol-<user>:
        ansible_user: fedora
        ansible_host: "{{ lookup('ansible.builtin.file', '/tmp/molecule-default-<user>.ip', errors='ignore') | default('127.0.0.1', true) | trim }}"
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

**Result in the project:** Molecule recognizes the `default` scenario; the play `hosts: servers` resolves to `fedora-mol-<user>`. `roles_path` and `collections_path` let `converge` find the project roles and the KubeVirt collections.

##### Step 2 — `molecule/default/molecule_vars.yml`

OpenShift credentials for `create.yml` and `destroy.yml`. Replace the four values with those from your assignment (lab Excel). **Do not** push real secrets to a public remote.

```yaml
---
ocp_url: "https://api.tu-cluster.com:6443"
ocp_user: "<lab_username>"
ocp_pass: "<lab_password>"
ocp_namespace: "virtualization-test-<lab_username>"
```

The namespace follows the form `virtualization-test-<lab_username>` (the project where your user can create VirtualMachines). **Do not** push this file to a public remote.

##### Collections — `molecule/default/requirements.yml`

Molecule installs this file in the `dependency` step (Galaxy), before `create`. It is required for `kubevirt.core.kubevirt_vm` and for deleting the Service in `destroy.yml`.

```yaml
---
collections:
  - name: kubevirt.core
  - name: kubernetes.core
  - name: community.general
```

**Result in the project:** `molecule test` installs the three collections under `~/.ansible/collections` (the path set in `molecule.yml`).

##### Step 3 — `molecule/default/create.yml`

Logs in to OpenShift, creates the VM with a Fedora disk and cloud-init (SSH key), waits until the VMI has an IP, saves it for `converge`, and waits for port 22.

```yaml
---
- name: Create VM in OpenShift
  hosts: localhost
  gather_facts: false
  vars_files:
    - molecule_vars.yml
  tasks:
    - name: Log in to OpenShift
      ansible.builtin.command:
        cmd: >-
          oc login --insecure-skip-tls-verify=false
          --username {{ ocp_user }}
          --password {{ ocp_pass }}
          {{ ocp_url }}
      changed_when: false
      no_log: true

    - name: Get OpenShift API token
      ansible.builtin.command:
        cmd: oc whoami --show-token
      register: token
      changed_when: false

    - name: Create Fedora VM using KubeVirt
      kubevirt.core.kubevirt_vm:
        host: "{{ ocp_url }}"
        api_key: "{{ token.stdout }}"
        validate_certs: true
        state: present
        run_strategy: Always
        wait: true
        wait_timeout: 600
        namespace: "{{ ocp_namespace }}"
        name: "{{ item.name }}"
        spec:
          domain:
            resources:
              requests:
                memory: 4Gi
            devices:
              interfaces:
                - name: default
                  masquerade: {}
              disks:
                - name: containerdisk
                  disk:
                    bus: virtio
                - name: cloudinit
                  disk:
                    bus: virtio
          networks:
            - name: default
              pod: {}
          volumes:
            - name: containerdisk
              containerDisk:
                image: quay.io/containerdisks/fedora:latest
            - name: cloudinit
              cloudInitNoCloud:
                userData: |
                  #cloud-config
                  ssh_authorized_keys:
                    - {{ lookup('ansible.builtin.file', playbook_dir + '/../../ssh_tests_connections/id_fedora_new.pub') | trim }}
      loop: "{{ molecule_yml.platforms }}"

    - name: Wait until the VMI has an IP
      ansible.builtin.command:
        cmd: >-
          oc get vmi {{ molecule_yml.platforms[0].name }}
          -n {{ ocp_namespace }}
          -o jsonpath={.status.interfaces[0].ipAddress}
      register: vmi_ip
      changed_when: false
      retries: 36
      delay: 10
      until: vmi_ip.stdout is match('([0-9]{1,3}\.){3}[0-9]{1,3}')

    - name: Save the VMI IP for converge
      ansible.builtin.copy:
        dest: /tmp/molecule-default-<user>.ip
        content: "{{ vmi_ip.stdout | trim }}\n"
        mode: "0644"

    - name: Wait for SSH on the VMI
      ansible.builtin.wait_for:
        host: "{{ vmi_ip.stdout | trim }}"
        port: 22
        timeout: 300
```

`create.yml` reads the IP with `oc get vmi` and writes it to `/tmp/molecule-default-<user>.ip`. That path must match the `ansible_host` lookup in `molecule.yml`. Memory is **4Gi**: with less, WildFly may never listen on port 8080. `no_log` keeps the `oc login` password out of the output.

**Result on OpenShift:** VM `fedora-mol-<user>` running in `virtualization-test-<lab_username>`, with `id_fedora_new.pub` installed for user `fedora` and SSH on port 22.

##### Step 4 — `molecule/default/destroy.yml`

Logs in again (Molecule runs `destroy` as a separate playbook) and removes the VM and the associated Service.

```yaml
---
- name: Destroy VM in OpenShift
  hosts: localhost
  gather_facts: false
  vars_files:
    - molecule_vars.yml
  tasks:
    - name: Log in to OpenShift
      ansible.builtin.command:
        cmd: >-
          oc login --insecure-skip-tls-verify=false
          --username {{ ocp_user }}
          --password {{ ocp_pass }}
          {{ ocp_url }}
      changed_when: false
      no_log: true

    - name: Get OpenShift API token
      ansible.builtin.command:
        cmd: oc whoami --show-token
      register: token
      changed_when: false

    - name: Remove Fedora VM from OpenShift
      kubevirt.core.kubevirt_vm:
        host: "{{ ocp_url }}"
        api_key: "{{ token.stdout }}"
        validate_certs: true
        state: absent
        wait: true
        wait_timeout: 300
        namespace: "{{ ocp_namespace }}"
        name: "{{ item.name }}"
      loop: "{{ molecule_yml.platforms }}"
      ignore_errors: true

    - name: Clean up associated Service
      kubernetes.core.k8s:
        host: "{{ ocp_url }}"
        api_key: "{{ token.stdout }}"
        validate_certs: true
        state: absent
        namespace: "{{ ocp_namespace }}"
        kind: Service
        name: "svc-{{ molecule_yml.platforms[0].name }}"
      ignore_errors: true
```

**Result on OpenShift:** the test VM and the Service `svc-fedora-mol-<user>`, if it existed, are gone. `ignore_errors` lets the scenario continue if the VM was never created.

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
        cmd: ansible-lint deploy-wildfly.yaml roles group_vars
        chdir: "{{ project_dir }}"
      changed_when: false
```

If `yamllint .` complains about Molecule’s cache (`.cache/`) or the repository `devfile.yaml`, add a `.yamllint` at the project root that `ignore`s `.cache/`, `.ansible-sign/`, and `devfile.yaml` (see 5.1).

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
        timeout: 120

    - name: Verify application sample.war is accessible
      ansible.builtin.uri:
        url: http://localhost:8080/sample/
        status_code: 200
      register: app_check
      retries: 8
      delay: 10
      until: app_check.status == 200
```

**Result on the node:** `wildfly` active, port 8080 listening, and HTTP 200 on `/sample/`. The wait is 120 s with up to 8 retries: on a freshly created VM, WildFly takes longer to publish `/sample/`.

**Final result of this block (5.3.1 — `default` scenario):** `molecule/default/` tree with `molecule.yml`, `molecule_vars.yml`, `requirements.yml`, `create.yml`, `destroy.yml`, `prepare.yml`, `converge.yml`, and `verify.yml`.

#### 5.3.2 Scenario `with_existing_machine` — lab VM

Uses the Fedora VM you already configured under **Inventory**. Copy `prepare.yml` and `verify.yml` from the `default` scenario (same lint and same assertions). `converge.yml` is identical (imports `deploy-wildfly.yaml`).

##### Step 8 — `molecule/with_existing_machine/molecule.yml`

Driver `default` with `managed: false`: Molecule does not provision an instance. `ansible_host` must be the IP from **your lab access data** (the same one as in `inventory`) and port **22**. In this classroom Dev Spaces reaches the Fedora VM **directly**; `127.0.0.1` and port `2222` only apply if the instructor asked for an **SSH tunnel**. If you copy those values as-is, Molecule will not connect.

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
        ansible_host: <IP_from_your_lab_access_data>
        ansible_port: 22
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

##### Step 9 — `molecule/with_existing_machine/create.yml`

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

##### Step 10 — `molecule/with_existing_machine/destroy.yml`

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

- `molecule/with_existing_machine/prepare.yml` — same content as **step 5**.
- `molecule/with_existing_machine/converge.yml` — same content as **step 6**.
- `molecule/with_existing_machine/verify.yml` — same content as **step 7**.
- `molecule/with_existing_machine/requirements.yml` — at least `community.general` (Molecule Galaxy installs it in `dependency`). The KubeVirt collections belong in `molecule/default/requirements.yml` (section 5.3.1), not at the project root.

**Final result of this block (5.3.2 — `with_existing_machine` scenario):** `molecule/with_existing_machine/` tree with `molecule.yml`, `create.yml`, `destroy.yml`, `prepare.yml`, `converge.yml`, and `verify.yml`; lint and functional checks identical to `default`, without creating or destroying the classroom VM.

#### 5.3.3 Run the Molecule tests

From the **project root** (next to `deploy-wildfly.yaml`), in **Dev Spaces**.

- `with_existing_machine` is the scenario you run against the lab Fedora (**required** in class).
- `default` runs **only from Dev Spaces** after you have replaced `<user>`, `ocp_url`, `ocp_user`, `ocp_pass`, and `ocp_namespace` (`molecule test` without `-s` uses `default`).

Default scenario (`default`, creates and destroys an OpenShift VM; **Dev Spaces only**). `molecule_vars.yml` must contain the API URL, user, password, and namespace `virtualization-test-<lab_username>`.

Full cycle:

```bash
molecule test
# equivalent:
molecule test -s default
```

Step by step (debugging):

```bash
molecule create -s default
molecule prepare -s default
molecule converge -s default
molecule verify -s default
molecule destroy -s default
```

After `create`, VM `fedora-mol-<user>` must exist in `virtualization-test-<lab_username>`. After `destroy`, that VM must be gone. The inventory Fedora stays in the same project.

Classroom scenario (existing VM; the one you should use in the lab):

```bash
molecule test -s with_existing_machine
```

Manual sequence (debugging), same `-s` if it is not `default`:

```bash
molecule create -s with_existing_machine
molecule prepare -s with_existing_machine
molecule converge -s with_existing_machine
molecule verify -s with_existing_machine
molecule destroy -s with_existing_machine
```

`molecule prepare` is the step that runs **yamllint** and **ansible-lint** on the project (playbook, roles, and `group_vars`). If it fails, fix all warnings from 5.1/5.2 (not only those in the example table) before `converge`.

**Final result of this block (5.3 — Molecule):** both scenarios are defined on disk. `molecule test -s with_existing_machine` completes `destroy` → `create` → `prepare` (lint) → `converge` → `verify` → `destroy` with exit code `0` on the classroom Fedora and leaves it running. `molecule test -s default` reaches exit code `0` after you replace `<user>`, the API URL, the user, the password, and the namespace `virtualization-test-<lab_username>`: it creates `fedora-mol-<user>`, deploys WildFly, and deletes that VM at the end.

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

If you do not have a suitable key for signing, create one. In Dev Spaces there is **no usable TTY** for the graphical pinentry dialog: `gpg --full-generate-key` hangs or never asks for the passphrase. Use **batch** generation (same lab passphrase):

```bash
gpg --batch --pinentry-mode loopback \
  --passphrase "CorreosAnsibleSign-Lab2026" \
  --quick-generate-key "Lab User <your-user@lab.local>" default default never
```

If you have a graphical terminal with pinentry, `gpg --full-generate-key` is also fine; when it asks for a **passphrase**, enter `CorreosAnsibleSign-Lab2026`.

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

**Before signing**, create a `MANIFEST.in` file at the **project root** (same level as `deploy-wildfly.yaml`). ansible-sign uses the [manifest syntax](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html).

Important behaviour: on **verify** (`gpg-verify`), ansible-sign prepends `global-include *` to the manifest. That means **any project file that is not excluded** is compared with the checksum. If you only `include` the playbook and leave out `.git`, `inventory`, or SSH keys, the GPG signature can be valid and checksum validation can **still fail**.

The manifest must therefore:

1. **Include** the playbook and the other automation artifacts you want to protect (`deploy-wildfly.yaml`, roles —including `files/` and `templates/`—, Molecule YAML, `group_vars`, `ansible.cfg`, `requirements.yml`, `index.html`, both READMEs, and so on).
2. **Exclude** data specific to your VM and secrets: `inventory`, the SSH private key, `molecule/default/molecule_vars.yml` (OpenShift credentials), and `devfile.yaml` if you do not want it signed.
3. **`prune`** directories that must not be signed: `.git`, `.cache` (Molecule), `.vscode` (Dev Spaces editor). ansible-sign already ignores `.ansible-sign`.

Example aligned with this exercise’s real tree (if `gpg-verify` lists files under `added`, add or exclude them and sign again):

```text
include deploy-wildfly.yaml
include README.md
include README_EN.md
include .yamllint
include .ansible-lint
include ansible.cfg
include requirements.yml
include index.html
recursive-include roles *.yml
recursive-include roles *.html
recursive-include roles *.j2
recursive-include molecule *.yml
recursive-include group_vars *.yml
recursive-include collections *.yml
prune .git
prune .cache
prune .vscode
exclude inventory
exclude devfile.yaml
exclude molecule/default/molecule_vars.yml
exclude ssh_tests_connections/id_fedora_new
exclude ssh_tests_connections/id_fedora_new.pub
global-exclude *.pyc
global-exclude *.retry
```

Create the file, check that the paths exist, and **then** run `gpg-sign`. Files that typically show up under `added` if you use a minimal manifest are `.vscode/*`, `README_EN.md`, `ansible.cfg`, `collections/requirements.yml`, `devfile.yaml`, `index.html`, and `requirements.yml`.

### 6.4 Sign the project

From the project root. In Dev Spaces the interactive GPG prompt usually fails (`Can not control echo on the terminal`); set the lab passphrase in the environment:

```bash
export ANSIBLE_SIGN_GPG_PASSPHRASE="CorreosAnsibleSign-Lab2026"
ansible-sign project gpg-sign .
```

If your terminal can prompt without echoing, this also works:

```bash
ansible-sign project gpg-sign --prompt-passphrase .
```

Enter `CorreosAnsibleSign-Lab2026` when asked.

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

1. This lab is done **in OpenShift Dev Spaces**. Configure the `inventory` file in this folder with the host of your Fedora VM using **your lab access data** (IP values in this guide are examples only; see the **Inventory** section before section 2).
2. **Create** `deploy-wildfly.yaml` by copying the snippets from section 2 (the file is not in the repository).
3. Refactor with `tags` and `block` (section 3).
4. Extract to roles, centralize variables, add handlers, and use `files/` and `templates/` (section 4).
5. Validate with yamllint, ansible-lint (playbook + roles + `group_vars`), and Molecule (section 5). Complete **`molecule test -s with_existing_machine`** against your Fedora. The `default` scenario creates another Fedora in `virtualization-test-<lab_username>`: replace `<user>`, `ocp_url`, `ocp_user`, `ocp_pass`, and `ocp_namespace` before **`molecule test -s default`**.
6. Create `MANIFEST.in` (section 6.3), sign the project with `ansible-sign`, and check the signature with `ansible-sign project gpg-verify` (section 6), using the shared lab passphrase.

The practice is to build the playbook, improve it structurally, and demonstrate quality with the tools above.

---

## Auxiliary commands

The inventory must already be configured as in the section **Inventory: Fedora VM host on OpenShift**. Use the IP from **your lab access data**; the address in the `ssh` command below is **an example only**.

```bash
ansible-playbook -i inventory deploy-wildfly.yaml
```

Manual checks after deployment:

```bash
ssh user1@<IP_from_your_lab_access_data> -i ssh_tests_connections/id_fedora_new
curl localhost:8080/sample/
```

**Final result of this block (auxiliary commands):** playbook executed against the adjusted inventory; SSH session to the node possible with the indicated key; `curl` returns the sample app HTML (HTTP 200) if WildFly and the `/sample/` deployment are correct.
