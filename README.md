# lab-devspaces-ansible-exercise1

Curso práctico de desarrollo de playbooks Ansible. **Este ejercicio está pensado para realizarse dentro de OpenShift Dev Spaces**. La VM Fedora del aula es alcanzable por SSH desde ese workspace.

Versiones de la imagen (compruébalas con `python3 --version`, `ansible --version`, `molecule --version`, `yamllint --version`, `ansible-lint --version`):

| Herramienta | Versión en Dev Spaces |
| ----------- | --------------------- |
| Python | **3.12** |
| ansible-core | **2.21.x** |
| yamllint | **1.38.x** |
| ansible-lint | **26.x** (p. ej. 26.6.0) |
| Molecule | **26.x** (p. ej. 26.6.0); driver **`default`** (no existe `delegated`) |
| ansible-sign, `oc` | Incluidos en la imagen |

No hace falta instalar estas herramientas a mano en el workspace. `pip install yamllint` / `ansible-lint` / `molecule` de más abajo solo aplica si alguna faltara.

**El repositorio no incluye `deploy-wildfly.yaml`.** Debes **crearlo tú** en la raíz del proyecto (mismo nivel que este README) copiando y ensamblando los fragmentos YAML de las secciones siguientes. Este documento es la guía para construirlo, refactorizarlo y validarlo con herramientas de calidad.

---

## Preparación del entorno

```bash
chmod 600 ssh_tests_connections/id_fedora_new
ansible-galaxy collection install community.general
```

**Resultado final del bloque (preparación):** clave SSH con permisos restrictivos para que SSH y Ansible la acepten; colección `community.general` disponible en el entorno de Ansible del controlador para módulos adicionales si el playbook las usa.

---

## 1. Contexto: qué hace `deploy-wildfly.yaml`

El playbook automatiza una instalación de **WildFly 39** alineada con la documentación oficial del producto. En una sola corrida sobre el grupo de inventario `servers` (con privilegios elevados):

1. **Define variables** de versión, rutas de instalación, usuario y grupo del servicio, y la URL de descarga del tarball oficial.
2. **Prepara el sistema operativo** instalando un JDK 17 o superior (requisito de WildFly 39) y utilidades necesarias para descomprimir el paquete. En las VM Fedora 44 del laboratorio el paquete es `java-25-openjdk-devel` (`java-21-openjdk-devel` ya no está en los repos).
3. **Crea identidad de servicio**: grupo y usuario de sistema dedicados, con home en el directorio de instalación y shell restrictivo.
4. **Descarga e instala** el WildFly desde GitHub en `/opt`, evitando repetir la extracción si ya existe el indicador de instalación previsto.
5. **Normaliza la ruta de trabajo** mediante un enlace simbólico desde `/opt/wildfly-<versión>` hacia `/opt/wildfly`, de modo que scripts y servicios apunten a una ruta estable.
6. **Ajusta la configuración** `standalone.xml` para que la interfaz pública escuche en `0.0.0.0` en lugar de solo `127.0.0.1`, permitiendo acceso de red al servidor de aplicaciones.
7. **Integra systemd**: copia `launch.sh`, la unidad `wildfly.service` y `wildfly.conf` desde los ejemplos incluidos en la distribución, crea `/etc/wildfly` y arranca y habilita el servicio con recarga del demonio systemd.
8. **Despliega una aplicación de ejemplo** empaquetando un `index.html` local como WAR en el controlador, copiándolo al directorio `standalone/deployments` del WildFly para comprobar el pipeline de despliegue.

En los ejemplos de esta guía hay tareas de **firewalld** comentadas; puedes activarlas en tu versión si el entorno lo requiere.

**Resultado final del bloque (§1 — visión global):** al ejecutar el playbook que has ido construyendo sobre `servers`, el nodo queda con WildFly instalado bajo `/opt`, servicio `wildfly` gestionado por systemd, escucha en red (interfaz pública `0.0.0.0`), y una aplicación de ejemplo accesible vía HTTP en el contexto `/sample/` (puerto 8080 por defecto), salvo que el cortafuegos impida el acceso externo.

---

## Inventario: host de la VM Fedora en OpenShift

Antes de la **sección 2 (guía paso a paso del playbook monolítico)**, debes adaptar el fichero `inventory` que está en **la misma carpeta que este README**. El play apunta al grupo `[servers]`; ahí se define contra qué máquina ejecutará Ansible y con qué usuario y clave SSH se conectará.

Los datos del host de tu **máquina virtual Fedora** (nombre, IP o dirección alcanzable desde OpenShift Dev Spaces, usuario SSH si difiere del de plantilla, etc.) figuran en los **datos de acceso de tu usuario de laboratorio** (Excel o ficha que te faciliten). Los valores de host e IP que aparecen en esta guía son **únicamente un ejemplo**: no los copies tal cual. Sustituye `ansible_host` (y, si el documento o el formador lo indican, `ansible_user` o el alias del host en la primera columna) por los de **tu** asignación. Deja la ruta de `ansible_ssh_private_key_file` alineada con la clave que preparaste en «Preparación del entorno» (por ejemplo `ssh_tests_connections/id_fedora_new`).

Plantilla de referencia del fichero (`fedora-user1` y el marcador de IP son ejemplos):

```ini
[servers]
fedora-user1 ansible_host=<IP_de_tus_datos_de_laboratorio> ansible_user=user1 ansible_ssh_private_key_file=ssh_tests_connections/id_fedora_new
```

Sin un inventario correcto, `ansible-playbook -i inventory …` no podrá alcanzar tu VM. Comprueba conectividad SSH desde el workspace antes de seguir con la guía.

**Resultado final del bloque (inventario):** fichero `inventory` con `ansible_host` (y demás campos si aplica) coherentes con **tus datos de usuario de laboratorio**; el grupo `servers` resuelve a tu VM Fedora para las ejecuciones posteriores del playbook.

---

## 2. Guía paso a paso (primer playbook monolítico)

Objetivo: construir `deploy-wildfly.yaml` en la raíz del proyecto (el fichero **no viene** en el repositorio), entendiendo el **orden lógico** y el **propósito** de cada bloque. No se repite aquí la documentación de cada módulo de Ansible; consulta la documentación oficial del módulo cuando lo uses por primera vez.

Tras cada paso aparece el **YAML concreto** que debes copiar e ir acumulando en `deploy-wildfly.yaml`. Al cierre de cada **bloque lógico** se resume el **estado resultante** en el nodo (ficheros, servicios o ausencia de cambios en disco).

### Paso 1 — Cabecera del play

Define un nombre descriptivo del play, el patrón de hosts (`servers` u otro grupo de tu inventario) y `become: true` si necesitas instalar paquetes y escribir bajo `/opt` y `/etc`.

```yaml
- name: Instalación de WildFly 39 siguiendo la Guía Oficial
  hosts: servers
  become: true
```

### Paso 2 — Variables del play (`vars`)

Declara al menos: versión de WildFly, directorio de instalación lógico (`/opt/wildfly`), usuario y grupo del servicio, y la URL de descarga del `.tar.gz` (puedes interpolar la versión en la cadena).

```yaml
  vars:
    wf_version: "39.0.1.Final"
    wf_install_dir: "/opt/wildfly"
    wf_user: "wildfly"
    wf_group: "wildfly"
    wf_url: "https://github.com/wildfly/wildfly/releases/download/{{ wf_version }}/wildfly-{{ wf_version }}.tar.gz"
    wf_java_package: java-25-openjdk-devel
```

**Resultado en el nodo (ficheros / estado):** los pasos 1 y 2 no escriben nada en el objetivo; solo fijan el alcance del play y las variables en memoria durante la ejecución.

**Resultado final del bloque (pasos 1–2 — cabecera y variables):** inventario y play listos para ejecutar tareas; ningún cambio persistente en el host hasta la primera tarea bajo `tasks:`.

### Paso 3 — Dependencias del sistema

Primera tarea: instalar en el nodo objetivo el JDK adecuado (Java 17+ para WildFly 39; en Fedora 44 usa `java-25-openjdk-devel`), más herramientas imprescindibles para manejar el archivo comprimido (por ejemplo `tar` y `gzip`).

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

**Resultado en el nodo:** paquetes RPM instalados (`java-25-openjdk-devel` en Fedora 44, `tar`, `gzip`); binarios disponibles en el PATH del sistema (`java`, `tar`, `gzip`).

**Resultado final del bloque (paso 3 — dependencias OS):** sistema preparado para descargar y desempaquetar WildFly y para ejecutar la JVM requerida.

### Paso 4 — Grupo de sistema para WildFly

Crea el grupo del servicio como grupo de sistema, presente en el nodo.

```yaml
    - name: Crear grupo de sistema para WildFly
      ansible.builtin.group:
        name: "{{ wf_group }}"
        system: true
        state: present
```

**Resultado final del bloque (paso 4 — solo grupo):** en `/etc/group` existe la línea del grupo de sistema `wildfly` (GID asignado por el sistema).

### Paso 5 — Usuario de sistema para WildFly

Crea el usuario del servicio asociado a ese grupo, con home en el directorio de instalación, shell de no login y marcado como cuenta de sistema.

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

**Resultado en el nodo:** entrada en `/etc/group` para `wildfly`; entrada en `/etc/passwd` (y shadow) para `wildfly` con GID del grupo anterior, home declarada como `/opt/wildfly` y shell `/sbin/nologin`. El directorio home puede aún no existir como árbol completo hasta que se cree la instalación bajo `/opt`.

**Resultado final del bloque (pasos 4–5 — identidad del servicio):** cuenta de sistema lista para ejecutar WildFly: grupo y usuario `wildfly` creados; aún no hay árbol de producto bajo `/opt/wildfly` hasta completar la instalación.

### Paso 6 — Descarga e instalación del producto

Descarga el archivo desde la URL y descomprímelo bajo `/opt`, asignando propietario y grupo al usuario WildFly. Usa un mecanismo idempotente (por ejemplo comprobación de que ya existe un fichero clave de la instalación) para no repetir la extracción innecesariamente.

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

**Resultado final del bloque (paso 6 — extracción):** existe `/opt/wildfly-{{ wf_version }}/` (p. ej. `/opt/wildfly-39.0.1.Final/`) con el contenido del tarball, UID/GID `wildfly`. La ruta canónica `/opt/wildfly` puede no existir aún si esta es la primera instalación y el enlace se crea en pasos posteriores.

### Paso 7 — Limpieza del enlace o directorio destino (si aplica)

Si tu diseño reutiliza siempre la misma ruta canónica (`/opt/wildfly`), incluye una tarea condicionada que elimine ese destino cuando no estés en modo check, de forma coherente con cómo quieres gestionar actualizaciones o reinstalaciones.

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

**Resultado final del bloque (paso 7 — limpieza del destino):** si `/opt/wildfly` existía como **directorio real** (no como enlace simbólico), ha sido eliminado; el directorio versionado `/opt/wildfly-{{ wf_version }}/` permanece. Si ya era un symlink, la tarea no lo borra (así las reejecuciones son idempotentes y no cortan el servicio). En modo `--check` tampoco aplica el cambio.

### Paso 8 — Enlace simbólico a la versión concreta

Crea el enlace desde el directorio versionado bajo `/opt` hacia la ruta estable de trabajo, con el mismo propietario y grupo que el servicio.

```yaml
    - name: Crear enlace simbólico a la versión instalada
      ansible.builtin.file:
        src: "/opt/wildfly-{{ wf_version }}"
        dest: "{{ wf_install_dir }}"
        state: link
        owner: "{{ wf_user }}"
        group: "{{ wf_group }}"
```

**Resultado en el nodo:** directorio versionado `/opt/wildfly-39.0.1.Final/` con el árbol completo del servidor (por ejemplo `bin/standalone.sh`, `standalone/configuration/standalone.xml`, `docs/contrib/scripts/systemd/`, etc.), propietario `wildfly`. Enlace simbólico `/opt/wildfly` → `/opt/wildfly-39.0.1.Final`. Tras el paso 7, solo se elimina `/opt/wildfly` si era un directorio (no un symlink) antes de asegurar el enlace.

**Resultado final del bloque (pasos 6–8 — instalación y ruta estable):** producto WildFly en `/opt/wildfly-<versión>/` y accesible también como `/opt/wildfly` (symlink); listo para configuración y servicio.

### Paso 9 — Escucha en todas las interfaces

Modifica `standalone.xml` del WildFly ya instalado (vía la ruta del enlace) para que la interfaz `public` use `0.0.0.0` por defecto en lugar de `127.0.0.1`. El fragmento en WildFly 39 está **en varias líneas**; `lineinfile` sobre una sola línea no coincide. Usa `replace` con un patrón que cubra el bloque real:

```yaml
    - name: Configurar WildFly para que escuche en todas las IPs (0.0.0.0)
      ansible.builtin.replace:
        path: "{{ wf_install_dir }}/standalone/configuration/standalone.xml"
        regexp: '<interface name="public">\s*<inet-address value="\$\{jboss\.bind\.address:127\.0\.0\.1\}"/>\s*</interface>'
        replace: '        <interface name="public"><inet-address value="${jboss.bind.address:0.0.0.0}"/></interface>'
```

**Resultado en el nodo:** en `/opt/wildfly/standalone/configuration/standalone.xml` (vía el enlace), el fragmento de la interfaz `public` queda con `inet-address` por defecto `0.0.0.0` en lugar de `127.0.0.1`, de modo que el servidor pueda escuchar en todas las interfaces de red.

**Resultado final del bloque (paso 9 — red / bind):** configuración persistente en `standalone.xml` para exponer la interfaz `public` en todas las IPs; efecto pleno tras el siguiente arranque del proceso WildFly (o reinicio del servicio).

### Paso 10 — Script de arranque para systemd

Copia desde la documentación incluida en la instalación el script `launch.sh` al árbol `bin` del WildFly, conservando permisos de ejecución.

```yaml
    - name: Copiar script launch.sh para systemd
      ansible.builtin.copy:
        src: "{{ wf_install_dir }}/docs/contrib/scripts/systemd/launch.sh"
        dest: "{{ wf_install_dir }}/bin/launch.sh"
        remote_src: yes
        mode: '0755'
```

### Paso 11 — Unidad systemd

Copia el fichero de unidad `wildfly.service` al directorio de unidades de systemd del sistema.

```yaml
    - name: Instalar el archivo de servicio systemd
      ansible.builtin.copy:
        src: "{{ wf_install_dir }}/docs/contrib/scripts/systemd/wildfly.service"
        dest: "/etc/systemd/system/wildfly.service"
        remote_src: yes
```

### Paso 12 — Directorio y fichero de configuración del servicio

Crea `/etc/wildfly` y copia allí el `wildfly.conf` de ejemplo desde la instalación.

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

**Resultado final del bloque (pasos 10–12 — ficheros de servicio en disco):** `/opt/wildfly/bin/launch.sh` con modo ejecutable; `/etc/systemd/system/wildfly.service`; directorio `/etc/wildfly/` con `wildfly.conf`. El demonio **aún puede no estar** activo hasta la tarea del paso 13.

### Paso 13 — Arranque y habilitación del servicio

Recarga la configuración de systemd, asegura que el servicio `wildfly` esté iniciado y habilitado al arranque.

```yaml
    - name: Recargar systemd y arrancar WildFly
      ansible.builtin.systemd:
        name: wildfly
        state: started
        enabled: true
        daemon_reload: true
```

**Resultado en el nodo:** `/opt/wildfly/bin/launch.sh` ejecutable; `/etc/systemd/system/wildfly.service`; directorio `/etc/wildfly/` con `wildfly.conf`. Tras la tarea systemd: unidad recargada, servicio `wildfly` activo (`systemctl is-active wildfly`) y habilitado al arranque; proceso escuchando (entre otros) en el puerto de aplicaciones HTTP configurado por defecto (8080).

**Resultado final del bloque (pasos 10–13 — integración systemd y runtime):** unidad instalada, configuración en `/etc/wildfly`, servicio `wildfly` **running** y **enabled**, con JVM escuchando en 8080 (y demás puertos por defecto de `standalone`).

### Paso 14 — (Opcional) Firewall

Si tu laboratorio usa `firewalld`, descomenta o añade la apertura del puerto HTTP del servidor de aplicaciones (por ejemplo 8080/tcp) de forma permanente e inmediata. Requiere la colección adecuada en el proyecto.

```yaml
    # - name: Abrir puerto 8080 en firewalld
    #   ansible.posix.firewalld:
    #     port: 8080/tcp
    #     permanent: true
    #     state: enabled
    #     immediate: true
```

**Resultado en el nodo (si descomentas y ejecutas):** regla permanente y efectiva en `firewalld` para `8080/tcp`; acceso externo al puerto según la política de red del host.

**Resultado final del bloque (paso 14 — firewall, opcional):** si la tarea está activa, `firewall-cmd --list-ports` (o equivalente) muestra `8080/tcp` en runtime y en configuración permanente.

### Paso 15 — Aplicación de ejemplo

Encapsula en un flujo claro: en el controlador, genera un WAR a partir de `index.html` (empaquetado como archivo zip con extensión `.war`); copia ese artefacto al directorio `standalone/deployments` del WildFly con el propietario correcto. Si el WAR se construye en localhost, usa delegación y desactiva `become` en esa parte para no exigir privilegios en la máquina desde la que ejecutas Ansible.

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

**Resultado en el nodo:** en la máquina de control: fichero `/tmp/sample.war` (ZIP con `index.html` dentro). En el objetivo: `/opt/wildfly/standalone/deployments/sample.war` con propietario `wildfly`; WildFly puede generar `sample.war.deployed` (y otros marcadores) al completar el despliegue. Respuesta HTTP esperada para comprobar el contexto, por ejemplo `curl http://<host>:8080/sample/`.

**Resultado final del bloque (paso 15 — aplicación de ejemplo):** artefacto `sample.war` desplegado; contexto `/sample/` sirve el contenido de `index.html`; comprobación típica `curl -sSf http://localhost:8080/sample/` desde el servidor o contra la IP del nodo.

Ejecuta el playbook y valida con `curl` o navegador contra la URL de la aplicación de ejemplo.

**Resultado final del bloque (§2 — playbook monolítico completo):** acumulado de todos los sub-bloques anteriores: RPM de Java y utilidades; usuario/grupo `wildfly`; `/opt/wildfly` → versión instalada; `standalone.xml` con bind `0.0.0.0`; systemd + servicio activo; opcionalmente firewalld; WAR de ejemplo y HTTP 200 en `/sample/`.

---

## 3. Segunda parte: refactorización con `tags` y `block`

Partiendo del playbook monolítico, mejora la operabilidad sin cambiar el comportamiento funcional.

### 3.1 Etiquetas (`tags`)

Asigna etiquetas coherentes a grupos de tareas para poder ejecutar solo fragmentos del play, por ejemplo:

- `deps` — paquetes del sistema.
- `wildfly_user` — grupo y usuario.
- `wildfly_install` — descarga, limpieza de destino y enlace simbólico.
- `wildfly_config` — modificación de `standalone.xml`.
- `wildfly_service` — ficheros systemd, `/etc/wildfly`, arranque del servicio.
- `app` — empaquetado y copia del WAR de ejemplo.
- `firewall` — reglas de cortafuegos, si las tienes.

Ejemplo de uso:

```bash
ansible-playbook -i inventory deploy-wildfly.yaml --tags wildfly_service
ansible-playbook -i inventory deploy-wildfly.yaml --skip-tags app
```

Ejemplo concreto (fragmento sobre tareas ya existentes):

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

**Resultado en el nodo:** idéntico al playbook sin etiquetas; las `tags` solo cambian **qué tareas se ejecutan** al invocar `--tags` / `--skip-tags`, no el estado final del sistema cuando corres el play completo.

### 3.2 Bloques (`block`)

Agrupa tareas relacionadas en `block` para:

- **Legibilidad**: un bloque “instalación binaria”, otro “integración systemd”, otro “aplicación de ejemplo”.
- **Rescate opcional** (`rescue`) o **siempre** (`always`): por ejemplo, si falla la copia del servicio, registrar un mensaje o intentar un diagnóstico; en `always`, tareas de limpieza o de registro de estado.

No es obligatorio añadir `rescue`/`always` si solo buscas agrupación visual; basta con `block` y comentarios en el playbook.

Ejemplo concreto (mismo bloque que el paso 15, ya presente en el playbook que estás construyendo):

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

**Resultado en el nodo:** igual que sin `block`: `/tmp/sample.war` en el controlador y `sample.war` bajo `standalone/deployments/` en el objetivo. El `block` agrupa el flujo para lectura y para poder añadir `rescue` / `always` sin alterar el resultado en disco.

**Resultado final del bloque (§3 — tags y block):** el **estado del nodo objetivo** tras un `ansible-playbook` completo sin `--tags` coincide con el del monolito (§2). En el **repositorio**, el playbook es más operable: puedes limitar ejecución por etiquetas y estructurar tareas en `block` sin cambiar el resultado en disco salvo que omitas tareas con `--skip-tags`.

---

## 4. Tercera parte: roles, variables y handlers

Extrae los bloques anteriores a **roles** dentro del mismo proyecto de playbook (por ejemplo directorio `roles/` junto al playbook). El playbook principal queda corto: lista de roles y, si hace falta, `vars` o `vars_files` que sobrescriban los valores por defecto de cada rol.

### 4.1 Esquema sugerido de roles


| Rol                  | Contenido típico                                                          |
| -------------------- | ------------------------------------------------------------------------- |
| `wildfly_os_deps`    | Instalación de paquetes (Java, tar, gzip).                                |
| `wildfly_account`    | Grupo y usuario de sistema.                                               |
| `wildfly_install`    | Descarga, extracción, limpieza condicional del destino, enlace simbólico. |
| `wildfly_bind`       | Ajuste de `standalone.xml` para `0.0.0.0`.                                |
| `wildfly_systemd`    | `launch.sh`, `wildfly.service`, plantilla `wildfly.conf.j2`, arranque.    |
| `wildfly_sample_app` | `files/index.html`, empaquetado local del WAR y copia al despliegue.      |


Puedes fusionar roles si prefieres menos granularidad; lo importante es que cada rol tenga una responsabilidad clara.

**Resultado en el proyecto (ficheros):** árbol orientativo tras crear los roles (los nombres de fichero son convención Ansible):

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
deploy-wildfly.yaml   # o site.yml que importa roles
```

### 4.2 Variables

Define en cada rol un `defaults/main.yml` con los valores por defecto (versión, rutas, nombres de usuario/grupo, URL). El playbook puede pasar variables con `vars:` o con un fichero `group_vars/servers.yml` para no hardcodear secretos o IPs.

Ejemplo concreto (`roles/wildfly_install/defaults/main.yml`):

```yaml
wf_version: "39.0.1.Final"
wf_install_dir: "/opt/wildfly"
wf_user: "wildfly"
wf_group: "wildfly"
wf_url: "https://github.com/wildfly/wildfly/releases/download/{{ wf_version }}/wildfly-{{ wf_version }}.tar.gz"
```

**Resultado en el nodo:** igual que en la guía monolítica; las variables solo cambian **dónde** se definen (rol vs play). Si el playbook o `group_vars` sobrescriben `wf_version`, el árbol bajo `/opt` usará la nueva versión en rutas y URL.

### 4.3 Handlers

Sustituye o complementa tareas que hoy mezclan “cambiar fichero” y “reiniciar servicio” con el patrón `notify`:

- Handler `recargar systemd`: ejecuta recarga del demonio cuando cambian unidades bajo `/etc/systemd/system`.
- Handler `reiniciar wildfly`: reinicia el servicio cuando cambian `wildfly.conf`, `launch.sh` o ficheros bajo `standalone/configuration` que requieran reinicio.

En las tareas `copy` o `template` que modifiquen esos ficheros, añade `notify` con el nombre del handler. Mantén coherencia: si una tarea ya fuerza `daemon_reload` y `state: started`, al introducir handlers revisa que no dupliques reinicios innecesarios en la primera ejecución.

Ejemplo concreto (`roles/wildfly_systemd/handlers/main.yml`):

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

Tarea que notifica (fragmento):

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

**Resultado en el nodo:** tras un cambio que dispare los handlers, systemd recarga unidades y el servicio `wildfly` se reinicia; en disco persisten los mismos ficheros que en el playbook monolítico (`/etc/systemd/system/wildfly.service`, etc.), con el orden de aplicación gobernado por Ansible al final del play (handlers).

### 4.4 Playbook que llama a los roles

Ejemplo de estructura (ilustrativo):

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

Las etiquetas puedes definirlas a nivel de rol en el playbook o dentro de cada rol en las tareas.

**Resultado en el nodo:** equivalente a ejecutar el playbook monolítico completo; la diferencia está en el **layout del repositorio** (roles reutilizables) y en la posibilidad de sobrescribir variables por entorno sin editar las tareas.

### 4.5 Ficheros estáticos (`files/`) y plantillas Jinja2 (`templates/`)

Cuando el playbook ya está partido en roles, deja de tratar `index.html` y `wildfly.conf` como rutas sueltas en la raíz del proyecto. Ansible busca ficheros estáticos en `files/` del rol y plantillas Jinja2 en `templates/`. El módulo `copy` con un `src` sin directorio resuelve el fichero dentro de `files/`; `template` hace lo mismo con `templates/` y además interpola variables.

#### Paso 1 — `index.html` en `files/` del rol `wildfly_sample_app`

Mueve el `index.html` de la raíz del proyecto a `roles/wildfly_sample_app/files/index.html` (mismo contenido HTML del paso 15). En el bloque de la aplicación de ejemplo, copia primero ese fichero al controlador (`delegate_to: localhost`, `become: false`) y después empaquétalo como WAR, igual que en el monolito.

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

No hace falta poner `roles/wildfly_sample_app/files/` en `src`: Ansible lo localiza solo porque la tarea vive en ese rol.

**Resultado en el nodo:** en el controlador, `/tmp/index.html` (copia del fichero del rol) y `/tmp/sample.war`. En el objetivo, `/opt/wildfly/standalone/deployments/sample.war` con propietario `wildfly`; el contexto `/sample/` sigue sirviendo el mismo HTML.

**Resultado final del bloque (4.5 paso 1 — `files/`):** el HTML de ejemplo vive en `roles/wildfly_sample_app/files/index.html`; el WAR se construye igual que en el paso 15, pero el origen ya no es la raíz del repositorio.

#### Paso 2 — `wildfly.conf` como plantilla Jinja2 en `wildfly_systemd`

Sustituye la copia `remote_src` del `wildfly.conf` de la distribución por un `template` generado desde `roles/wildfly_systemd/templates/wildfly.conf.j2`. Las rutas, el usuario del servicio y la dirección de bind salen de variables del rol (`defaults/main.yml` o `group_vars`).

Contenido de `roles/wildfly_systemd/templates/wildfly.conf.j2`:

```jinja
# {{ ansible_managed }}
JBOSS_HOME={{ wildfly_systemd_install_dir }}
JBOSS_USER={{ wildfly_systemd_user }}
WILDFLY_CONFIG={{ wildfly_systemd_config }}
WILDFLY_MODE={{ wildfly_systemd_mode }}
WILDFLY_BIND={{ wildfly_systemd_bind }}
```

Valores por defecto típicos en `roles/wildfly_systemd/defaults/main.yml` (ajusta el prefijo si `ansible-lint` exige `var-naming`):

```yaml
---
wildfly_systemd_install_dir: "/opt/wildfly"
wildfly_systemd_user: "wildfly"
wildfly_systemd_config: standalone.xml
wildfly_systemd_mode: standalone
wildfly_systemd_bind: "0.0.0.0"
```

Tarea que renderiza y notifica a los handlers (sustituye la `copy` remota del `wildfly.conf`):

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

`src: wildfly.conf.j2` se resuelve en `templates/` del rol. Si cambias `wildfly_systemd_bind` (u otra variable de la plantilla) y vuelves a ejecutar el play, el fichero cambia y los handlers recargan systemd y reinician WildFly.

**Resultado en el nodo:** `/etc/wildfly/wildfly.conf` generado a partir de la plantilla (comentario `ansible_managed`, `JBOSS_HOME=/opt/wildfly`, `JBOSS_USER=wildfly`, `WILDFLY_BIND=0.0.0.0`, etc.). El servicio `wildfly` usa ese `EnvironmentFile`; un cambio de plantilla provoca reinicio vía handlers.

**Resultado final del bloque (4.5 paso 2 — `templates/`):** la configuración del servicio deja de copiarse desde el tarball y pasa a ser un artefacto del repositorio, parametrizable por variables.

**Resultado final del bloque (§4 — roles):** en disco del objetivo, el mismo resultado que **Resultado final del bloque (§2)** si los roles replican las mismas tareas y variables, con `/etc/wildfly/wildfly.conf` renderizado por Jinja2 y el WAR generado desde `files/index.html`. En el **proyecto**: directorio `roles/` con `tasks/main.yml`, `defaults/main.yml`, y, si aplica, `handlers/main.yml`, `files/` y `templates/`; playbook corto que solo ordena roles y opcionalmente `group_vars` / `vars`.

---

## 5. Calidad: yamllint, ansible-lint y Molecule

### 5.1 yamllint

Comprueba sintaxis y estilo YAML (indentación, líneas largas, documentos múltiples).

Instalación (ejemplo con pip):

```bash
pip install yamllint
```

Ejecución típica sobre el proyecto:

```bash
yamllint .
```

Opcional: añade un fichero `.yamllint` en la raíz para relajar o endurecer reglas según el estándar del curso, e **ignorar** lo que no formes tú (por ejemplo `devfile.yaml` del repositorio, `.cache/` de Molecule y `.ansible-sign/`). Los ejemplos de esta guía llevan gazapos de estilo (véase **Gazapos intencionados** más abajo).

**Resultado final del bloque (5.1 — yamllint):** salida sin errores (código de salida `0`) o lista de ficheros/líneas a corregir según tu `.yamllint`; el YAML del proyecto cumple las reglas de estilo acordadas en el curso.

### 5.2 ansible-lint

Analiza playbooks y roles contra buenas prácticas de Ansible (nombres, `fqcn`, uso de `become`, idempotencia, etc.).

Instalación:

```bash
pip install ansible-lint
```

Ejecución (recorre el **proyecto completo**: playbook, roles y `group_vars`; `ansible-lint .` puede no analizar roles ni variables y dar un falso 0):

```bash
# Tras el playbook monolítico (aún sin roles):
ansible-lint deploy-wildfly.yaml

# Con roles y group_vars (validación del ejercicio completo):
ansible-lint deploy-wildfly.yaml roles group_vars
```

Corrige los avisos que el formador marque como obligatorios para aprobar el ejercicio. En este curso hay **gazapos intencionados** (véase el recuadro siguiente): el playbook puede desplegar bien y aun así fallar el lint.

**Resultado final del bloque (5.2 — ansible-lint):** ejecución con código de salida `0` (o solo avisos aceptados por el formador); playbooks y roles pasan las reglas de calidad configuradas (FQCN, nombres de tareas, idempotencia, etc.).

### Gazapos intencionados (yamllint y ansible-lint)

Los YAML de ejemplo de las secciones 2–4 incluyen **errores de estilo a propósito**. No rompen la ejecución en Dev Spaces; `yamllint` y `ansible-lint` sí deben marcarlos.

La tabla siguiente es **solo un ejemplo** de avisos frecuentes. **No es una lista cerrada**: las herramientas pueden reportar más reglas (`var-naming`, `line-length`, `key-order`, permisos en otras tareas `copy`/`file`, el `devfile.yaml` del repo, etc.). Revisa **toda** la salida, localiza cada fallo en tu árbol y corrígelo hasta código de salida `0`.

| Gazapo (ejemplo) | Dónde copiarlo / buscarlo | Herramienta y regla |
| ---------------- | ------------------------- | ------------------- |
| `remote_src: yes` (truthy `yes`/`no` en lugar de `true`/`false`) | `unarchive` y `copy` con `remote_src` | yamllint `truthy` / ansible-lint `yaml[truthy]` |
| Nombres de handlers que no empiezan por mayúscula (`recargar systemd`, `reiniciar wildfly`) | `roles/wildfly_systemd/handlers/main.yml` | ansible-lint `name[casing]` |
| Tareas `copy` / `file` sin `mode` | unidad `wildfly.service`, directorio `/etc/wildfly`, `wildfly.conf` | ansible-lint `risky-file-permissions` |
| YAML de rol sin cabecera `---` | p. ej. `roles/wildfly_install/defaults/main.yml` | yamllint `document-start` |
| Espacio en blanco al final de una línea | `group_vars/servers.yml` (línea de `wf_url`) | yamllint `trailing-spaces` |

Corrige **todos** los avisos (los de la tabla y el resto que salgan) en playbooks, roles y `group_vars` **antes** de lanzar Molecule. El escenario ejecuta `yamllint` y `ansible-lint` en el paso `prepare`; si siguen fallos, `molecule test` fallará ahí. No hace falta alterar los YAML de Molecule para resolverlos.

### 5.3 Molecule (prueba del playbook)

Molecule ejecuta el playbook contra un entorno de prueba y un playbook de verificación. En este ejercicio creas **tú** el árbol `molecule/` (no viene hecho en el repositorio).

La imagen de Dev Spaces incluye **Molecule 26.x** (p. ej. 26.6.0) con ansible-core **2.21**. El driver se llama `default` (el nombre antiguo `delegated` **ya no existe**; si lo usas, `molecule` falla al cargar los escenarios).

Los **dos escenarios se pueden definir** en el proyecto. Se diferencian en de dónde sale la máquina:

| Escenario | Máquina de prueba | Qué hace `create` / `destroy` | Dónde ejecutarlo |
| --------- | ----------------- | ----------------------------- | ---------------- |
| `default` | VM Fedora **generada dentro de OpenShift** (KubeVirt) | `create.yml` da de alta la VM; `destroy.yml` la elimina al terminar. | **Únicamente desde Dev Spaces** (en este curso no se lanza fuera de ese workspace). |
| `with_existing_machine` | VM Fedora **prearrancada** del laboratorio (la del `inventory`) | No crea ni borra la máquina; solo reutiliza la instancia ya encendida. | Desde Dev Spaces, contra la Fedora del inventario. |

La secuencia de `molecule test` será: `destroy` → `create` → **`prepare`** (`yamllint` y `ansible-lint`) → `converge` → `verify` → `destroy`.

Instalación (en Dev Spaces suele venir ya en la imagen; si no):

```bash
pip install molecule molecule-plugins ansible
```

Crea los directorios de ambos escenarios:

```bash
mkdir -p molecule/default molecule/with_existing_machine
```

Alinea tres cosas en todos los escenarios: `converge.yml` debe importar `deploy-wildfly.yaml` (o el playbook de roles); el inventario de Molecule debe declarar el grupo `servers`; `verify.yml` comprueba el servicio `wildfly`, el puerto **8080** y la URL `/sample/`.

#### 5.3.1 Escenario `default` — VM de prueba en OpenShift

Este escenario se ejecuta **únicamente desde Dev Spaces**.

##### Paso 1 — `molecule/default/molecule.yml`

Define el driver `default` (Molecule 26.x en la imagen del laboratorio), plataforma, inventario del grupo `servers` y la secuencia de test con `prepare` (lint).

```yaml
---
dependency:
  name: galaxy
driver:
  name: default
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

**Resultado en el proyecto:** Molecule reconoce el escenario `default`; el play `hosts: servers` resuelve al host de prueba.

##### Paso 2 — `molecule/default/molecule_vars.yml`

Credenciales de OpenShift para `create.yml` / `destroy.yml`. Sustituye URL, usuario y contraseña por los de tu asignación (Excel del laboratorio). **No** subas secretos reales a un remoto público.

```yaml
---
ocp_url: "https://api.tu-cluster.com:6443"
ocp_user: "admin"
ocp_pass: "mi_password_secreto"
```

**Resultado en el proyecto:** variables `ocp_*` disponibles para el playbook de creación.

##### Paso 3 — `molecule/default/create.yml`

Crea la VM Fedora con KubeVirt y espera SSH. Requiere `oc` autenticado y las colecciones `kubevirt.core` / `kubernetes.core`.

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

Ajusta `namespace`, `ansible_user` y la IP/DNS reales de la VM cuando el laboratorio te los indique. Sin un nodo alcanzable por SSH, `converge` no podrá aplicar el playbook.

**Resultado en OpenShift:** VM `fedora-chocolate-smelt-74` presente en el namespace; SSH en el puerto 22.

##### Paso 4 — `molecule/default/destroy.yml`

Elimina la VM y, de forma opcional, un Service asociado.

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

**Resultado en OpenShift:** la VM de prueba (y el Service si existía) ya no están; `ignore_errors` evita que falle el escenario si la VM no llegó a crearse.

##### Paso 5 — `molecule/default/prepare.yml` (yamllint y ansible-lint)

Este playbook es el gancho de Molecule **después de `create` y antes de `converge`**. Aquí se integran las mismas comprobaciones de las secciones 5.1 y 5.2, de modo que `molecule test` no continúe si el YAML o las prácticas Ansible no cumplen.

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

Si `yamllint .` se queja del caché de Molecule (`.cache/`) o del `devfile.yaml` del repositorio, añade un `.yamllint` en la raíz del proyecto con `ignore` de `.cache/`, `.ansible-sign/` y `devfile.yaml` (véase 5.1).

**Resultado en el proyecto:** `molecule prepare` (y el paso `prepare` de `molecule test`) termina con código `0` solo si yamllint y ansible-lint pasan.

##### Paso 6 — `molecule/default/converge.yml`

Aplica el playbook real del ejercicio, no un placeholder.

```yaml
---
- name: Converge
  ansible.builtin.import_playbook: ../../deploy-wildfly.yaml
```

**Resultado en el nodo de prueba:** el mismo estado que al ejecutar `ansible-playbook -i inventory deploy-wildfly.yaml` (WildFly, servicio y WAR de ejemplo).

##### Paso 7 — `molecule/default/verify.yml`

Comprueba servicio, puerto y aplicación de ejemplo.

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

**Resultado en el nodo:** `wildfly` activo, puerto 8080 a la escucha y HTTP 200 en `/sample/`.

**Resultado final del bloque (5.3.1 — escenario `default`):** árbol `molecule/default/` con `molecule.yml`, `molecule_vars.yml`, `create.yml`, `destroy.yml`, `prepare.yml`, `converge.yml` y `verify.yml`.

#### 5.3.2 Escenario `with_existing_machine` — VM del laboratorio

Usa la Fedora que ya configuraste en **Inventario**. Copia `prepare.yml` y `verify.yml` del escenario `default` (mismo lint y mismas aserciones). `converge.yml` es idéntico (importa `deploy-wildfly.yaml`).

##### Paso 8 — `molecule/with_existing_machine/molecule.yml`

Driver `default` con `managed: false`: Molecule no provisiona instancia. El `ansible_host` debe ser la IP de **tus datos de laboratorio** (la misma que en `inventory`). Los valores `fedora-user1`, `127.0.0.1` y el puerto `2222` del YAML siguiente son **solo un ejemplo** (túnel SSH en Dev Spaces). Si desde el workspace alcanzas la VM directamente, usa esa IP y el puerto 22.

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

**Resultado en el proyecto:** el grupo `servers` apunta a `fedora-user1` con la misma identidad SSH que el inventario del curso.

##### Paso 9 — `molecule/with_existing_machine/create.yml`

```yaml
---
- name: Create (delegated — la VM de laboratorio ya existe)
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Confirmar que no se crea una VM nueva
      ansible.builtin.debug:
        msg: >-
          Driver default (delegated) con managed=false.
          Se reutiliza la instancia {{ molecule_yml.platforms[0].name }} del laboratorio.
```

**Resultado en el nodo:** ninguno; solo un mensaje. La VM del laboratorio sigue igual.

##### Paso 10 — `molecule/with_existing_machine/destroy.yml`

```yaml
---
- name: Destroy (delegated — no se elimina la VM de laboratorio)
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Conservar la VM Fedora del ejercicio
      ansible.builtin.debug:
        msg: >-
          No se destruye {{ molecule_yml.platforms[0].name }}.
          La instancia pertenece al laboratorio y se gestiona fuera de Molecule.
```

**Resultado en el nodo:** ninguno; la Fedora del alumno **no** se apaga ni se borra.

##### Paso 11 — Resto de ficheros del escenario

Crea:

- `molecule/with_existing_machine/prepare.yml` — mismo contenido que el **paso 5**.
- `molecule/with_existing_machine/converge.yml` — mismo contenido que el **paso 6**.
- `molecule/with_existing_machine/verify.yml` — mismo contenido que el **paso 7**.

**Resultado final del bloque (5.3.2 — escenario `with_existing_machine`):** árbol `molecule/with_existing_machine/` con `molecule.yml`, `create.yml`, `destroy.yml`, `prepare.yml`, `converge.yml` y `verify.yml`; lint y verificación funcionales idénticos al escenario `default`, sin crear ni destruir la VM del aula.

#### 5.3.3 Lanzar los tests de Molecule

Desde la **raíz del proyecto** (junto a `deploy-wildfly.yaml`), en **Dev Spaces**.

- El escenario `with_existing_machine` es el que usas contra la Fedora del laboratorio.
- El escenario `default` se lanza **únicamente desde Dev Spaces** (`molecule test` sin `-s` usa `default`).

##### Escenario `default` — genera la VM en OpenShift (solo Dev Spaces)

Crea la Fedora en OpenShift, pasa lint (`prepare`), aplica el playbook, verifica WildFly y **destruye** la VM al final. Necesitas `oc` autenticado y `molecule_vars.yml` con URL/usuario/contraseña del clúster.

Ciclo completo:

```bash
molecule test
# equivalente:
molecule test -s default
```

Paso a paso (depuración):

```bash
molecule create -s default
molecule prepare -s default
molecule converge -s default
molecule verify -s default
molecule destroy -s default
```

Tras `create`, en OpenShift debe existir la VM `fedora-chocolate-smelt-74`. Tras `destroy`, esa VM ya no debe estar.

##### Escenario `with_existing_machine` — máquina prearrancada

No provisiona nada: usa la Fedora que ya está encendida (inventario del laboratorio / túnel SSH). `create` y `destroy` solo confirman que no se crea ni se borra esa instancia.

Ciclo completo:

```bash
molecule test -s with_existing_machine
```

Paso a paso (depuración):

```bash
molecule create -s with_existing_machine
molecule prepare -s with_existing_machine
molecule converge -s with_existing_machine
molecule verify -s with_existing_machine
molecule destroy -s with_existing_machine
```

Tras `destroy`, la VM del laboratorio **sigue arrancada**; Molecule no la apaga.

`molecule prepare` (en ambos escenarios) ejecuta **yamllint** y **ansible-lint** sobre el proyecto (playbook, roles y `group_vars`). Si falla, corrige todos los avisos de 5.1/5.2 (no solo los de la tabla de ejemplos) antes de `converge`.

**Resultado final del bloque (5.3 — Molecule):** los dos escenarios se ejecutan hasta código `0`. En `default`, `molecule test` (o `-s default`) crea la VM en OpenShift, hace lint, converge, verifica `/sample/` y elimina la VM. En `with_existing_machine`, `molecule test -s with_existing_machine` hace lo mismo sobre la máquina prearrancada y la deja intacta al terminar.

**Resultado final del bloque (§5 — calidad):** pipeline local repetible: YAML válido (yamllint), buenas prácticas Ansible (ansible-lint) — primero a mano (5.1–5.2) y otra vez **dentro** de Molecule (`prepare`) — y prueba de extremo a extremo alineada con WildFly y `/sample/`.

---

## 6. Firma del proyecto con `ansible-sign`

[ansible-sign](https://ansible.readthedocs.io/projects/sign/en/latest/) genera un manifiesto de comprobación (SHA-256) de los ficheros que elijas del proyecto y firma ese manifiesto con GPG. Así puedes demostrar que el contenido firmado no ha sido alterado. En este curso usamos una **frase de paso GPG común** para que todos los participantes utilicen el mismo criterio al crear la clave de firma y al firmar.

### Contraseña de laboratorio (frase de paso GPG)

Al generar tu par de claves GPG y cuando `ansible-sign` o GnuPG te pidan la contraseña de la clave privada, utiliza **exactamente** esta frase de paso (misma para todos los asistentes al laboratorio):

```text
CorreosAnsibleSign-Lab2026
```

Es la contraseña del **contenedor de la clave GPG** (passphrase), no un usuario de sistema. Guárdala solo para el ejercicio; en entornos reales cada firmante usaría una frase de paso propia y confidencial.

### 6.1 Requisitos e instalación

Necesitas GnuPG (`gpg`) en el sistema y el CLI de ansible-sign, en este caso en el laboratorio ya esta instalado dentro de la imagen que usamos dentro de devspaces y no es necesario:

```bash
pip install ansible-sign
ansible-sign --version
```

Comprueba si ya tienes una clave secreta (opcional; si no, el siguiente apartado la crea):

```bash
gpg --list-secret-keys
```

### 6.2 Par de claves GPG para firmar

Si no tienes clave adecuada para firmar, créala (tipo y validez por defecto suelen bastar). Cuando solicite **passphrase**, introduce `CorreosAnsibleSign-Lab2026`.

```bash
gpg --full-generate-key
```

Anota el **identificador** de la clave (fingerprint o e-mail asociado) por si más adelante usas `ansible-sign project gpg-sign --fingerprint <ID> .`.

Para **verificar** una firma hecha por otra persona necesitas su **clave pública** en tu llavero. Quien firma puede exportarla:

```bash
gpg --armor --export tu@email.del.laboratorio > lab-ansible-sign-pub.asc
```

Quien verifica la importa:

```bash
gpg --import lab-ansible-sign-pub.asc
```

Si firmas y verificas tú mismo el mismo proyecto en la misma máquina, tu clave pública ya está en tu llavero y no hace falta importar nada.

### 6.3 `MANIFEST.in`: qué ficheros entran en la firma

**Antes de firmar**, crea en la **raíz del proyecto** (mismo nivel que `deploy-wildfly.yaml`) un fichero `MANIFEST.in`. ansible-sign usa la [sintaxis de manifiestos](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html).

Comportamiento importante: al **verificar** (`gpg-verify`), ansible-sign antepone `global-include *` al manifiesto. Eso significa que **cualquier fichero del proyecto que no esté excluido** se compara con el checksum. Si solo pones `include` del playbook y dejas fuera `.git`, `inventory` o las claves SSH, la firma GPG puede ser válida y **aun así fallar** la validación de sumas.

Por eso el manifiesto debe:

1. **Incluir** el playbook y el resto de artefactos de automatización que quieras proteger (`deploy-wildfly.yaml`, roles —incluidos `files/` y `templates/`—, YAML de Molecule, `group_vars`, etc.).
2. **Excluir** datos propios de tu VM y secretos: `inventory`, clave privada SSH, `molecule/default/molecule_vars.yml` (credenciales de OpenShift).
3. **Hacer `prune`** de directorios que no deben entrar en la firma: `.git`, `.cache` (Molecule) y, si existe, `.ansible-sign` ya lo ignora la herramienta.

Ejemplo orientativo para este ejercicio (ajústalo a tu árbol; si no tienes `roles/` o `group_vars/` aún, omite esas líneas o créalas antes de firmar):

```text
include deploy-wildfly.yaml
include README.md
include .yamllint
include .ansible-lint
recursive-include roles *.yml
recursive-include roles *.html
recursive-include roles *.j2
recursive-include molecule *.yml
recursive-include group_vars *.yml
prune .git
prune .cache
exclude inventory
exclude molecule/default/molecule_vars.yml
exclude ssh_tests_connections/id_fedora_new
exclude ssh_tests_connections/id_fedora_new.pub
global-exclude *.pyc
global-exclude *.retry
```

Crea el fichero, revisa que las rutas existen y **después** ejecuta `gpg-sign`. Si `gpg-verify` lista ficheros en `added`, añádelos con `include`/`recursive-include` o exclúyelos con `exclude`/`prune` y vuelve a firmar.

### 6.4 Firmar el proyecto

Desde la raíz del proyecto:

```bash
ansible-sign project gpg-sign --prompt-passphrase .
```

Si no aparece el diálogo gráfico de GPG, `--prompt-passphrase` hace que la frase de paso se pida en terminal; introduce `CorreosAnsibleSign-Lab2026`.

En entornos automatizados también se admite la variable `ANSIBLE_SIGN_GPG_PASSPHRASE` con la misma frase (útil en CI; en el curso prioriza la práctica interactiva).

Salida esperada (resumida): creación o actualización de `.ansible-sign/sha256sum.txt` y la firma `.ansible-sign/sha256sum.txt.sig`.

### 6.5 Verificar la firma

Con el mismo proyecto (y la clave pública del firmante importada si no eres tú quien firmó):

```bash
ansible-sign project gpg-verify .
```

Debes obtener confirmación de que la **firma GPG** es válida y que las **sumas de comprobación** coinciden con los ficheros actuales. Si modificas un fichero listado en `MANIFEST.in` sin volver a firmar, la verificación fallará (comportamiento deseado).

Más detalle ante errores: `ansible-sign --debug project gpg-verify .`

**Resultado final del bloque (§6 — firma):** `MANIFEST.in` definido; proyecto firmado con `ansible-sign project gpg-sign`; verificación correcta con `ansible-sign project gpg-verify`; frase de paso del laboratorio usada de forma uniforme en la generación de la clave y en la firma.

---

## Resumen

1. Este laboratorio se realiza **en OpenShift Dev Spaces**. Configura el fichero `inventory` de esta carpeta con el host de tu VM Fedora según **tus datos de acceso de laboratorio** (los valores de IP de esta guía son solo un ejemplo; véase la sección **Inventario** anterior a la sección 2).
2. **Crea** `deploy-wildfly.yaml` copiando los fragmentos de la sección 2 (el fichero no viene en el repositorio).
3. Refactoriza con `tags` y `block` (sección 3).
4. Extrae a roles, centraliza variables, añade handlers y usa `files/` y `templates/` (sección 4).
5. Valida con yamllint, ansible-lint (playbook + roles + `group_vars`) y Molecule (sección 5). El escenario `default` solo desde Dev Spaces.
6. Crea `MANIFEST.in` (sección 6.3), firma el proyecto con `ansible-sign` y comprueba la firma con `ansible-sign project gpg-verify` (sección 6), usando la frase de paso común del laboratorio.

La práctica consiste en construir el playbook, mejorarlo estructuralmente y demostrar calidad con las herramientas anteriores.

---

## Comandos auxiliares

El inventario debe estar ya configurado como en la sección **Inventario: host de la VM Fedora en OpenShift**. Usa la IP de **tus datos de laboratorio**; la dirección del `ssh` siguiente es **solo un ejemplo**.

```bash
ansible-playbook -i inventory deploy-wildfly.yaml
```

Comprobaciones manuales tras el despliegue:

```bash
ssh user1@<IP_de_tus_datos_de_laboratorio> -i ssh_tests_connections/id_fedora_new
curl localhost:8080/sample/
```

**Resultado final del bloque (comandos auxiliares):** playbook ejecutado contra el inventario ajustado; sesión SSH al nodo posible con la clave indicada; `curl` devuelve el HTML de la app de ejemplo (código HTTP 200) si WildFly y el despliegue `/sample/` están correctos.
