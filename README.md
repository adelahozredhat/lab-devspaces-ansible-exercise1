# lab-devspaces-ansible-exercise1

## ¿Qué es una colección de Ansible?

Una **colección de Ansible** es un paquete versionado que agrupa contenido reutilizable bajo un **espacio de nombres** y un **nombre** (`namespace.nombre_coleccion`). Dentro puede convivir, entre otras cosas:

- **Módulos, plugins y utilidades Python** (`plugins/`), incluidos los `module_utils` compartidos por varios módulos.
- **Roles** (`roles/`) con la estructura habitual de tareas, handlers, meta, etc.
- **Playbooks**, documentación, metadatos de Galaxy (`galaxy.yml`), requisitos de Ansible (`meta/runtime.yml`) y **pruebas** bajo `tests/`.

Las colecciones se publican en [Ansible Galaxy](https://galaxy.ansible.com/), se instalan con `ansible-galaxy collection install` y en los playbooks se referencian los módulos con el **FQCN** (nombre completamente calificado), por ejemplo `namespace_example.collection_example.get_servers`.

## Objetivo de este laboratorio

Este ejercicio está pensado sobre todo para **entender la estructura** de una colección de Ansible y cómo encajan el rol, el módulo, los tests y `ansible-test`. **No es imprescindible modificar el código** para sacar provecho del laboratorio: basta con recorrer el árbol de directorios, localizar cada pieza y ejecutar las herramientas de calidad que se indican más abajo.

## Contenido de `template-ansible-collection-develop`

En el directorio `template-ansible-collection-develop/` hay un proyecto tipo plantilla. La colección concreta vive en:

`template-ansible-collection-develop/ansible_collections/namespace_example/collection_example/`

Según `galaxy.yml`, la colección se identifica como **`namespace_example.collection_example`**: espacio de nombres `namespace_example`, nombre `collection_example`.

### Rol incluido: `get_server_example_role`

En `roles/get_server_example_role/` hay un rol de ejemplo que:

- Invoca el módulo de la colección `namespace_example.collection_example.get_servers` con variables (`example_username`, `example_password`, `example_url`, etc.).
- Registra el resultado, muestra un `debug` y escribe la salida en un fichero de ejemplo.

Sirve para ver **cómo un rol consume un módulo propio de la misma colección** usando el FQCN.

### Módulo y código de soporte (plugins)

En `plugins/` se incluye:

| Ruta | Descripción |
| :--- | :---------- |
| `plugins/modules/get_servers.py` | Módulo **`get_servers`**: obtiene listas de servidores (con sus *hostvars*) vía API tipo HAIINV; opciones como `username`, `password`, `url`, `proxy`, `techgroups`, `environment`. |
| `plugins/module_utils/haiinv.py` | Utilidades compartidas para hablar con la API. |
| `plugins/module_utils/exceptions.py` | Excepciones usadas por el módulo y las utilidades. |

En la documentación de Ansible, este tipo de ficheros en `plugins/modules/` suele llamarse genéricamente **plugin** de tipo módulo; aquí el foco del laboratorio es ver **dónde vive el código Python** y cómo se relaciona con el rol y los tests.

### Otras carpetas útiles para orientarse

- `meta/runtime.yml`: versión de Ansible soportada (`requires_ansible`).
- `playbooks/playbook.yml`: ejemplo de uso.
- `tests/unit/`: pruebas unitarias (módulo y `module_utils`).
- `tests/integration/targets/get_server/`: target de integración que ejercita el módulo.
- `tests/output/`: salidas de ejecuciones anteriores (JUnit, informes de cobertura en `tests/output/reports/`); conviene conocerlas al revisar resultados en IDE o CI.

## Entorno (OpenShift Dev Spaces)

El fichero `devfile.yaml` define un workspace con la imagen **ansible-devspaces**, adecuada para ejecutar `ansible` y `ansible-test` sin instalar herramientas a mano en tu máquina local.

## Pruebas con `ansible-test` y cobertura

Todos los comandos siguientes deben ejecutarse **desde el directorio raíz de la colección** (donde está `galaxy.yml`):

```bash
cd template-ansible-collection-develop/ansible_collections/namespace_example/collection_example
ansible-galaxy collection install . -p ~/.ansible/collections --force
```

Ajusta la versión de Python (`3.11`, etc.) a la disponible en el contenedor. El flag `--requirements` instala dependencias de test cuando haga falta.

### Sanidad (`sanity`)

Comprueba formato, sintaxis, documentación del módulo y otras comprobaciones estándar del ecosistema Ansible:

```bash
ansible-test sanity -v --python 3.11 --requirements
```

Para ignorar artefactos bajo `tests/output/` si molestan al analizador:

```bash
ansible-test sanity -v --python 3.11 --requirements --exclude tests/output/
```

### Pruebas unitarias (`units`)

Ejecuta los tests Python bajo `tests/unit/` (módulo `get_servers` y `module_utils`).

En la imagen **ansible-devspaces**, el Python del sistema trae **pytest-ansible**, que rompe `ansible-test units` (rutas de colección con `:`). Además `ansible-test` **no reenvía** `PYTEST_ADDOPTS` al subproceso de pytest, y desinstalar paquetes del sistema a menudo falla (sin pip en `/usr/bin/python3` o sin permisos).

**Solución recomendada:** usar **`--venv`**. `ansible-test` crea un virtualenv e instala solo las dependencias de `units` (pytest, xdist, mock, etc.); ahí **no** entra pytest-ansible de la imagen.

La colección declara en **`tests/unit/requirements.txt`** la dependencia **`requests`**: sin ella, `plugins/module_utils/haiinv.py` carga un stub vacío (`class Haiinv: pass`) y los tests del módulo fallan.

```bash
ansible-test units --venv --python 3.11 --requirements --coverage
```

### Pruebas de integración (`integration`)

Ejecuta el target `get_server` y el resto de targets definidos bajo `tests/integration/`:

```bash
ansible-test integration --python 3.11 --requirements
```

En muchos entornos hace falta privilegios para ciertos escenarios; si la documentación o el entorno lo requieren, se puede usar `sudo` delante del comando.

Puedes combinar integración con recogida de cobertura (según versión de `ansible-test`):

```bash
ansible-test integration --python 3.11 --requirements --coverage
```

### Informes de cobertura de código

Tras ejecutar `units` o `integration` con `--coverage`, Ansible deja datos de cobertura que puedes **combinar y volcar** a informes legibles:

```bash
ansible-test coverage combine
ansible-test coverage report
ansible-test coverage html --requirements
```

El HTML resultante se puede abrir en el navegador para revisar **qué líneas del módulo y de `module_utils` están cubiertas** por los tests. En el repositorio ya hay un ejemplo de informe XML en `tests/output/reports/coverage.xml` de una corrida anterior.

## Referencias

- [Uso de colecciones](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)
- [Desarrollo de colecciones](https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html)
- [ansible-test](https://docs.ansible.com/ansible/latest/dev_guide/testing_integration.html)
