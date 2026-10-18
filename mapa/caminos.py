"FAUSTO: MODELO 1 - mapa/caminos.py"
# caminos.py
# Camino más corto entre dos esquinas con A*
# Siempre se procesa la esquina con menor f(n) = g(n) + h(n):
#   g(n) = metros realmente recorridos desde el origen hasta n
#   h(n) = metros en línea recta (Haversine) desde n hasta el destino
# h nunca es mayor que el camino real por calles, así que A* siempre devuelve el camino más corto. Respeta las calles cerradas porque recorre el mapa con grafo.vecinos().
# Devuelve (lista_de_esquinas, metros); si no hay camino devuelve (None, inf).
# El parámetro opcional stats (un diccionario) recibe en "explorados" cuántas esquinas se procesaron, para comparar rendimiento.
import heapq  # Cola de prioridad: siempre entrega primero el elemento con menor valor

from mapa.distancias import distancia_recta

INF = float("inf")  # Infinito: es mayor que cualquier número, sirve como "todavía no hay camino"


# Busca el camino más corto por calles entre dos esquinas, sin recorrer todo el mapa
def a_estrella(grafo, origen, destino, stats=None):
    lat_d, lon_d = grafo.nodos[destino]  # Coordenadas del destino, se usan en cada cálculo de h

    # Estima cuánto falta para llegar al destino; guía a A* hacia el lado correcto
    def h(esquina):
        # Heurística: metros en línea recta hasta el destino
        lat, lon = grafo.nodos[esquina]
        return distancia_recta(lat, lon, lat_d, lon_d)  # Nunca se pasa del costo real: ninguna calle es más corta que la línea recta

    # Datos con los que trabaja el algoritmo
    g = {origen: 0.0}             # g(n): mejor distancia conocida desde el origen
    anterior = {}                 # De qué esquina se llegó a cada una (para armar la ruta)
    cola = [(h(origen), 0.0, origen)]   # Lista abierta: (f, g, esquina). Son las esquinas pendientes de procesar, ordenadas por f
    explorados = 0                # Esquinas procesadas por completo

    # Procesa esquinas de menor a mayor f hasta llegar al destino o quedarse sin esquinas
    while cola:
        _f, costo, actual = heapq.heappop(cola)  # Saca la esquina con menor f
        if costo > g.get(actual, INF):  # Una esquina puede estar varias veces en la cola si se le encontró un camino mejor después
            continue              # Entrada vieja: ya se encontró un camino mejor
        explorados += 1
        if actual == destino:     # Ya es la ruta óptima: se detiene sin recorrer todo el mapa
            break  # Al sacarlo de la cola, ningún otro camino pendiente puede ser más corto
        # Prueba avanzar por cada calle abierta que sale de esta esquina
        for vecino, metros, _nombre, _id in grafo.vecinos(actual):  # Vecinos() ya salta las calles cerradas; nombre e id no se necesitan aquí
            nuevo = costo + metros  # Metros desde el origen si se llega al vecino pasando por esta esquina
            if nuevo < g.get(vecino, INF):  # Solo vale la pena si mejora lo que ya se conocía (o si es la primera vez que se llega)
                g[vecino] = nuevo
                anterior[vecino] = actual  # Se anota por dónde se llegó, para reconstruir la ruta al final
                heapq.heappush(cola, (nuevo + h(vecino), nuevo, vecino))  # f = g + h

    # Guarda cuántas esquinas se procesaron, para comparar A* con otros algoritmos
    if stats is not None:
        stats["explorados"] = explorados
    if destino not in g:  # Se vació la cola sin llegar al destino: las calles cerradas lo dejaron aislado
        return None, INF

    # Reconstruir la ruta retrocediendo por "anterior" y luego invertirla
    camino = [destino]
    while camino[-1] != origen:
        camino.append(anterior[camino[-1]])  # Va de la última esquina hacia atrás, hasta llegar al origen
    camino.reverse()  # Quedó de destino a origen, se voltea
    return camino, g[destino]  # g[destino] son los metros totales
