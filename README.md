# 🛫 SkyBalance AVL — Sistema de Gestión Aérea

> **Sistema inteligente de gestión de vuelos** basado en un árbol AVL autobalanceado, con análisis de rentabilidad, modo estrés y versionado persistente.

## Descripción del proyecto

**SkyBalance AVL** es una aplicación completa de gestión de vuelos que demuestra la implementación práctica de estructuras de datos avanzadas. El sistema utiliza un árbol AVL autobalanceado para mantener información de vuelos de forma eficiente, permitiendo operaciones CRUD, búsqueda, análisis económico y auditoría, todo con una interfaz gráfica moderna que se actualiza en tiempo real.

### Caso de uso
Una aerolínea necesita gestionar su catálogo de vuelos manteniendo un balance óptimo entre profundidad de búsqueda (minimizar latencia) y profundidad crítica (aplicar recargos de tarifa). **SkyBalance AVL** lo hace automáticamente.

---

## 🚀 Inicio rápido

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar la aplicación
python app.py

# 3. Abrir en el navegador
# http://localhost:5000
```

---

## Estructura del proyecto

```
Proyecto1EstructuraDeDatos/
│
├── app.py                          ← Servidor Flask + endpoints REST
├── requirements.txt                ← Dependencias (Flask, Flask-CORS)
├── README.md                       ← Este archivo
│
├── src/                            ← Código fuente principal
│   ├── acceso_datos/               ← Capa de persistencia
│   │   ├── DataLoader.py           ├─ Carga y validación de JSON
│   │   ├── DataPersistence.py      ├─ Serialización del árbol
│   │   ├── DataStorage.py          ├─ Orquestador central
│   │   └── VersionManager.py       └─ Sistema de versionado
│   │
│   ├── controllers/                ← Lógica de control
│   │   └── QueueController.py      ← Procesador de cola FIFO
│   │
│   ├── modelos/                    ← Estructuras de datos
│   │   ├── AVLTree.py              ├─ Árbol AVL (CORE)
│   │   ├── BST.py                  ├─ Árbol binario (comparativa)
│   │   ├── FlightNode.py           ├─ Nodo con datos de vuelo
│   │   └── FlightQueue.py          └─ Cola de concurrencia
│   │
│   ├── negocio/                    ← Lógica de negocios
│   │   ├── AVLTreeManager.py       ├─ Operaciones CRUD
│   │   └── TreeAnalysisManager.py  └─ Análisis y auditoría
│   │
│   ├── routes/                     ← Endpoints REST
│   │   └── queue_routes.py         ← Blueprint de cola
│   │
│   └── presentacion/               ← Frontend
│       ├── estilos/
│       │   └── styles.css          ← Tema + modo estrés
│       └── vistas/
│           └── index.html          ← Aplicación SPA
│
└── versions/                       ← Versiones guardadas (JSON snapshots)
    ├── demo_tutorial_*.json
    ├── prueba_*.json
    └── ...
```

### Componentes principales

| Componente | Responsabilidad |
|---|---|
| **AVLTree.py** | Árbol autobalanceado con rotaciones (LL, RR, LR, RL) y modo estrés |
| **DataStorage.py** | Orquestador central: carga, guardado, versionado |
| **AVLTreeManager.py** | Operaciones CRUD con validación exhaustiva |
| **TreeAnalysisManager.py** | Auditoría, penalización por profundidad, rentabilidad |
| **Flask (app.py)** | API REST con endpoints para todas las operaciones |
| **Frontend (index.html)** | Visualización D3.js con sincronización en tiempo real |

---

## 📋 Requisitos previos

- **Python 3.7+**
- **pip** (gestor de paquetes)
- **Navegador moderno** (Chrome, Firefox, Edge, Safari)

---

## 🎯 Funcionalidades principales

### 1. **Árbol AVL Autobalanceado** 🌳
- Mantiene balance automático mediante rotaciones (LL, RR, LR, RL)
- Factor de balance siempre en {−1, 0, 1}
- Complejidad garantizada O(log n) para búsqueda, inserción y eliminación

### 2. **Gestión completa de datos (CRUD)** ✏️
- **Agregar** — validación de campos, cálculo de precio final con promoción
- **Editar** — modificación en sitio con rebalanceo automático si cambia código
- **Eliminar** — eliminación individual con reubicación automática de hijos
- **Cancelar** — eliminación atómica de nodo + subárbol completo

### 3. **Modo Estrés + Rebalanceo Global** ⚡
- **Modo normal**: rebalanceo automático tras cada inserción/eliminación
- **Modo estrés**: rotaciones diferidas (árbol acumula desbalance intencionalmente)
  - Interfaz cambia a tema visual rojo
  - `global_rebalance()`: ejecuta todas las rotaciones pendientes en un paso
  - Reporta número total de rotaciones ejecutadas

### 4. **Penalización por profundidad crítica** 📊
- Nodos más profundos que el límite aplican **recargo del 25%** sobre precio base
- Fórmula: `final_price = base_price × 1.25`
- Profundidad crítica es configurable desde la interfaz
- Recalculación automática sin necesidad de rebalanceo

### 5. **Versionado con snapshots** 💾
- Guarda estado completo del árbol en archivos JSON independientes
- Metadatos: nombre, timestamp, altura, contadores de rotación
- Operaciones: guardar, listar, restaurar, eliminar
- Restauración exacta (incluyendo contadores de rotación)

### 6. **Pila Deshacer (Ctrl+Z)** ↩️
- Captura snapshot antes de cada operación mutante
- Historial ilimitado durante la sesión
- Navega entre estados sin limitación de profundidad

### 7. **Auditoría AVL** 🔍
- Verifica invariantes:
  1. Balance factor ∈ {−1, 0, 1} para todos los nodos
  2. Altura almacenada coincide con la calculada
- Reporta nodo, profundidad, valores encontrados vs. esperados
- Activable en modo estrés

### 8. **Análisis de rentabilidad** 💹
- Calcula rentabilidad: `pasajeros × precio_final`
- Identifica vuelo menos rentable con tie-breaking
  - Prioridad 1: mayor profundidad
  - Prioridad 2: código lexicográfico mayor
- Eliminación automática con subárbol completo

### 9. **Cola FIFO de concurrencia** 📋
- Encola vuelos antes de insertarlos en el árbol
- Procesamiento: uno a uno o en lote
- Detecta *critical balance spikes* (balance_factor ≥ 2)
- Registro automático de conflictos detectados

### 10. **Árbol BST comparativo** 📈
- Se construye en modo inserción en paralelo con AVL
- Referencia visual: muestra diferencia de profundidad sin balanceo
- Justifica la necesidad de AVL para aplicaciones reales

---

## 📡 API REST — Referencia completa

### 🌳 Operaciones de árbol

| Método | Ruta | Descripción |
|:---:|---|---|
| `GET` | `/api/tree-state` | Estado completo (topología, nodos, metadatos) |
| `POST` | `/api/load-tree` | Carga y reconstruye árbol desde JSON |
| `GET` | `/api/export-tree` | Exporta árbol a `~/Downloads` |

### ✈️ CRUD de vuelos

| Método | Ruta | Descripción |
|:---:|---|---|
| `POST` | `/api/add-flight` | Inserta vuelo con validación |
| `POST` | `/api/edit-flight` | Actualiza datos de vuelo existente |
| `POST` | `/api/delete-flight` | Elimina nodo individual |
| `POST` | `/api/cancel-flight` | Cancela vuelo y su subárbol completo |

### 🎮 Control y análisis

| Método | Ruta | Descripción |
|:---:|---|---|
| `POST` | `/api/undo` | Deshace última acción |
| `POST` | `/api/toggle-stress-mode` | Activa/desactiva modo estrés |
| `POST` | `/api/global-rebalance` | Ejecuta rebalanceo masivo |
| `GET` | `/api/audit-avl` | Auditoría de propiedades AVL |
| `POST` | `/api/delete-least-profitable` | Cancela vuelo menos rentable |
| `POST` | `/api/update-critical-depth` | Configura profundidad crítica |

### 📦 Versiones y cola

| Método | Ruta | Descripción |
|:---:|---|---|
| `POST` | `/api/save-version` | Guarda versión con nombre |
| `GET` | `/api/list-versions` | Lista todas las versiones |
| `POST` | `/api/restore-version` | Restaura versión guardada |
| `POST` | `/api/delete-version` | Elimina versión |
| `GET` | `/api/queue` | Estado actual de cola |
| `POST` | `/api/queue/enqueue` | Encola vuelo sin insertarlo |
| `POST` | `/api/queue/process-one` | Inserta siguiente vuelo |
| `POST` | `/api/queue/process-all` | Drena cola completa |
| `DELETE` | `/api/queue/clear` | Limpia todos los vuelos pendientes |

---

## ✨ Características destacadas

✅ **Visualización en tiempo real** con D3.js  
✅ **Tema dinámico** (modo normal + modo estrés visual)  
✅ **Validación exhaustiva** en tres niveles (entrada → lógica → negocio)  
✅ **Análisis económico integrado** (profundidad, rentabilidad, penalización)  
✅ **Versionado completo** con snapshots instantáneos  
✅ **Deshacer ilimitado** (Ctrl+Z) sin límite de profundidad  
✅ **Auditoría integrada** para verificar invariantes AVL  
✅ **Modo estrés** para demostraciones y análisis de comportamiento  

---