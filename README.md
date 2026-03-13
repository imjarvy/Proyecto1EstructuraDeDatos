# Proyecto1EstructuraDeDatos

## Estado actual (lo que ya esta implementado)

Esta etapa del proyecto ya tiene implementadas y probadas las funcionalidades base del modulo AVL.

### 1 Carga inicial desde JSON (sin ruta fija)

- La carga se hace desde selector de archivo (explorador de archivos).
- Se soportan los 2 modos requeridos:
	- Topologia: reconstruye respetando padres e hijos del JSON.
	- Insercion: inserta vuelo por vuelo en AVL y en BST para comparacion.

Archivos principales:
- `src/acceso_datos/DataLoader.py`
- `src/acceso_datos/DataStorage.py`

### 2 AVL + BST en modo insercion

- En modo insercion se construyen ambos arboles con el mismo orden de insercion.
- El BST se mantiene como referencia visual/comparativa.
- El AVL mantiene balance automatico.

Archivos principales:
- `src/modelos/AVLTree.py`
- `src/modelos/BST.py`
- `src/acceso_datos/DataStorage.py`

### 3 CRUD y logica de negocio del AVL

- Insercion de vuelos.
- Modificacion de vuelos.
- Eliminacion individual de nodos.
- Cancelacion en cascada (vuelo + toda su descendencia), diferente de eliminacion individual.

Archivo principal:
- `src/negocio/AVLTreeManager.py`

### 4 Modo estres + rebalanceo global

- Modo normal: balanceo en cada insercion.
- Modo estres: difiere balanceo durante inserciones.
- `global_rebalance()` aplica rebalanceo masivo al final.

Archivo principal:
- `src/modelos/AVLTree.py`

### 5 Versionado persistente

- Versiones guardadas en disco (JSON por version).
- Cada version guarda metadatos (incluye `version_name`) y snapshot del arbol.
- Funciones disponibles: guardar, listar, info, restaurar, eliminar, exportar e importar version.

Archivo principal:
- `src/acceso_datos/VersionManager.py`

### 6 Pila de retroceso (Ctrl+Z)

- Se guarda snapshot antes de acciones mutantes.
- Se puede deshacer: insercion, eliminacion, modificacion y cancelacion.
- API de negocio:
	- `can_undo()`
	- `undo_last_action()`

Archivo principal:
- `src/negocio/AVLTreeManager.py`

