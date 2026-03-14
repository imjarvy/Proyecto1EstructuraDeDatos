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


LOGICA DE COMO USE BLUEPRINT DE FLASK PARA LA SIMULACION DE CONCUERRENCIAS (LOS VUELOS QUE ESTAN ENCOLADOS)

Flujo: 
# app.py línea 59:
init_queue(manager)

    ↓
# Inicializa _queue y _controller en queue_routes.py:
_queue = FlightQueue()
_controller = QueueController(manager, _queue)

    ↓
# Ahora las rutas del blueprint pueden usarlos:
@queue_bp.route("/api/queue/enqueue", methods=["POST"])
def enqueue_flight():
    _queue.enqueue(node)  # ✅ Usa la cola inicializada

# Sección 3 — Concurrent Insertion Simulation (Flight Queue)

Para manejar múltiples solicitudes de inserción sin comprometer la estabilidad del AVL tree, se implementó un sistema de cola FIFO que permite programar vuelos antes de procesarlos en la estructura.
Cómo está organizado:
El módulo se divide en tres capas. FlightQueue (src/modelos/FlightQueue.py) es la estructura base — una cola que almacena FlightNode objetos pendientes, lleva el historial de vuelos procesados y registra cualquier balance conflict que ocurra. QueueController (src/controllers/QueueController.py) es el motor de procesamiento, toma los vuelos de la cola uno por uno y los inserta en el AVL tree a través del AVLTreeManager, garantizando que cada inserción quede registrada en el undo stack. También detecta critical balance spikes después de cada inserción y los guarda como conflictos. Finalmente, queue_routes.py (src/routes/queue_routes.py) expone todo como una Flask API mediante un Blueprint.
Endpoints disponibles:

GET /api/queue — estado actual de la cola
POST /api/queue/enqueue — programa un vuelo sin insertarlo de inmediato
POST /api/queue/process-one — inserta el siguiente vuelo pendiente en el árbol
POST /api/queue/process-all — drena la cola completa de una vez
DELETE /api/queue/clear — limpia todos los vuelos pendientes

En la interfaz:
Se agregó una sección dedicada donde el usuario puede llenar el formulario de un vuelo, encolarlo, y luego elegir procesarlos uno a uno o todos de una vez. Los vuelos pendientes se listan en tiempo real, los contadores se actualizan automáticamente, y cualquier conflicto detectado aparece en un log debajo de la cola. 
