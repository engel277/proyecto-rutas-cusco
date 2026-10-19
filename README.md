# Sistema de Gestión de Rutas Óptimas en Cusco

Proyecto de Programación III (UNSAAC). Aplicación en Python con interfaz gráfica (tkinter) que
gestiona pedidos de reparto en Cusco y aplica cuatro estrategias algorítmicas sobre el mapa real
de la ciudad (OpenStreetMap).

## Cómo ejecutarlo

Requiere Python 3.8 o superior con tkinter (viene con Python en Windows y macOS; en Linux:
`sudo apt install python3-tk`). No hay que instalar paquetes para usar la aplicación.

```
python main.py                                    # abre la aplicación
python -m unittest pruebas.test_algoritmos -v     # pruebas unitarias
python -m pruebas.benchmark                       # tiempos con 10, 50, 100, 500 y 1000 pedidos
```

El mapa está en `herramientas/grafo.json`. Si falta, se genera una sola vez con
`pip install osmnx` y `python herramientas/mapacusco.py`.

## Qué se puede hacer en la aplicación

A la izquierda están las pestañas (con una línea de ayuda de cada una) y a la derecha el mapa con su leyenda
(rueda del mouse = zoom, arrastrar = mover, clic = elegir un punto; botones "Acercar al centro" y "Ver todo el mapa"). Los algoritmos deciden el orden de visita con la distancia en línea recta (Haversine, rápida), pero las rutas de Greedy, Zonas y Mochila se dibujan **por las calles reales** (A*) y muestran los metros reales que recorrería el repartidor. Si se cierra una calle en la pestaña Rutas, esos recorridos la rodean.
El menú **Archivo** permite cargar pedidos desde un JSON o generar pedidos aleatorios.

| Pestaña | Técnica | Qué hace |
|---|---|---|
| Pedidos | Ordenación y búsqueda | Agrega pedidos, los ordena por prioridad o distancia con Merge Sort y los busca por ID (búsqueda binaria) o por sector. |
| Repartidores | (datos) | Agrega o elimina repartidores con su nombre, capacidad (kg) y posición inicial (clic en el mapa). Las demás pestañas los usan al instante. |
| Greedy | Voraz | **Vecino más cercano**: el repartidor siempre va al pedido más próximo que le quepa. **Pedido urgente**: se asigna al repartidor más cercano con capacidad. |
| Zonas | Divide y Vencerás | Parte la ciudad en zonas (una por repartidor) cortando por el eje de mayor dispersión; cada zona se recorre con el vecino más cercano y se dibuja en un color. |
| Mochila | Programación Dinámica | Elige qué pedidos cargar en el vehículo para maximizar el valor sin pasar la capacidad (mochila 0/1). |
| Rutas | Backtracking | Busca la ruta más corta entre dos puntos evitando las calles cerradas; se acota con Divide y Vencerás, poda y memoria. Se puede detener. |

La búsqueda de rutas (backtracking) corre en un hilo aparte, así que la ventana no se congela y se puede detener.

## Estructura del proyecto

```
main.py                      Punto de entrada: carga el mapa y los pedidos y abre la ventana
modelos.py                   Pedido y Repartidor (dataclass) y cargar_pedidos()
mapa/
  distancias.py              distancia(a, b): metros en línea recta (Haversine)
  grafo.py                   Grafo: esquinas, calles, calles cerradas, esquina más cercana
  caminos.py                 a_estrella: camino más corto por calles entre dos esquinas
  recorridos.py              recorrido_por_calles: convierte paradas en el trazo y los metros reales
algoritmos/
  ordenacion_busqueda.py     Merge Sort, búsqueda binaria, agrupar por sector
  greedy.py                  vecino_mas_cercano, asignar_urgente
  divide_venceras.py         dividir_en_zonas, rutas_por_zona
  mochila.py                 llenar_mochila (programación dinámica)
  backtracking.py            buscar_rutas
gui/
  ventana_principal.py       App: pestañas, mapa y ejecución en hilos
  canvas_mapa.py             CanvasMapa: dibuja calles, pedidos, repartidores y rutas
  pestana_*.py               Una pestaña por técnica (más pestana_repartidores.py)
herramientas/
  mapacusco.py               Descarga el mapa de OpenStreetMap y crea grafo.json
datos/pedidos_ejemplo.json   15 pedidos de ejemplo en Cusco
pruebas/
  test_algoritmos.py         Pruebas unitarias (unittest)
  benchmark.py               Mide tiempos y compara técnicas (datos para el informe)
```

## Complejidad (resumen)

n = pedidos, r = repartidores, W = capacidad en unidades enteras.

| Algoritmo | Tiempo | Espacio |
|---|---|---|
| Merge Sort | O(n log n) | O(n) |
| Búsqueda binaria | O(log n) | O(1) |
| Vecino más cercano | O(n²) | O(n) |
| Dividir en zonas | O(n log n · log r) | O(n) |
| Mochila 0/1 | O(n · W) | O(n · W) |
| A* (camino por calles) | O(E log V) | O(V) |
| Backtracking (puro) | exponencial | O(V) |

El análisis completo y las comparaciones van en el informe técnico.
