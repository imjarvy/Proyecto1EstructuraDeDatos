# Proyecto1EstructuraDeDatos

## SkyBalance AVL - Sistema de Gestión Aérea

Este proyecto implementa un sistema de gestión aérea utilizando un Árbol AVL como estructura de datos principal.

## Estructura del Proyecto

```
src/
├── acceso_datos/          # Capa de acceso a datos
│   ├── DataLoader.py
│   ├── DataPersistence.py
│   ├── DataStorage.py
│   └── VersionManager.py
├── modelos/               # Modelos de datos
│   ├── AVLTree.py
│   ├── FlightNode.py
│   └── __init__.py
├── negocio/               # Lógica de negocio y API web
│   └── app.py
└── presentacion/          # Interfaz de usuario
    ├── estilos/
    │   ├── styles.css
    │   └── script.js
    └── vistas/
        └── index.html
```

## Instalación y Ejecución

### Prerrequisitos

- Python 3.8 o superior
- pip

### Instalación

1. Clona el repositorio:
   ```bash
   git clone <url-del-repositorio>
   cd Proyecto1EstructuraDeDatos
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

### Ejecución

Para ejecutar la aplicación web:

```bash
python src/negocio/app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Funcionalidades Implementadas

### Interfaz Web
- **Visualización del Árbol**: Gráfico interactivo del árbol AVL usando D3.js
- **Gestión de Vuelos**: Agregar, editar, eliminar y cancelar vuelos
- **Modo Estrés**: Visualización del árbol sin balanceo automático
- **Sistema de Penalización**: Nodos críticos marcados visualmente
- **Auditoría AVL**: Verificación de la propiedad AVL en modo estrés
- **Versionado**: Guardar y restaurar versiones del árbol
- **Simulación Concurrente**: Procesamiento de colas de inserciones
- **Métricas en Tiempo Real**: Altura, rotaciones, recorridos, etc.

### API Endpoints

- `GET /`: Página principal
- `POST /api/load-tree`: Cargar árbol desde JSON
- `GET /api/export-tree`: Exportar árbol a JSON
- `POST /api/add-flight`: Agregar vuelo
- `PUT /api/edit-flight`: Editar vuelo
- `DELETE /api/delete-flight/<code>`: Eliminar vuelo
- `DELETE /api/cancel-flight/<code>`: Cancelar vuelo (eliminar subárbol)
- `POST /api/toggle-stress-mode`: Alternar modo estrés
- `GET /api/audit-avl`: Realizar auditoría AVL

## Uso

1. Abre la aplicación en tu navegador
2. Carga un archivo JSON con la estructura del árbol o crea vuelos manualmente
3. Gestiona los vuelos usando los controles de la interfaz
4. Explora las diferentes funcionalidades como modo estrés, auditoría, etc.

## Desarrollo

### Arquitectura
- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Visualización**: D3.js
- **Estructura de Datos**: AVL Tree personalizado

### Extensiones
Para desarrollo, se recomienda instalar:
- VS Code con extensiones de Python y HTML/CSS/JS
- Live Server para desarrollo frontend
- Python extension para debugging

## Contribución

1. Crea una rama para tu feature
2. Implementa los cambios
3. Ejecuta pruebas
4. Crea un pull request

## Licencia

Este proyecto es parte del curso de Estructuras de Datos.