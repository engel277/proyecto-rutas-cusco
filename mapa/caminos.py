# caminos.py
# Camino más corto POR CALLES entre dos esquinas del mapa (algoritmo A*).
# Lo usan las pestañas Greedy, Zonas y Mochila para dibujar la ruta siguiendo las calles reales
# en vez de una línea recta, y para dar los metros reales que recorrería el repartidor.

import heapq

from mapa.distancias import distancia_recta

_cache = {}               # (grafo, versión, origen, destino) -> (camino, metros). Cada par se calcula una sola vez
_CACHE_MAXIMO = 5000      # Para que la memoria no crezca sin límite


def a_estrella(grafo, origen, destino):
    """Camino más corto por calles entre dos ids de esquina.
    Devuelve (lista_de_esquinas, metros_totales); si no hay camino (por ejemplo, calles
    cerradas) devuelve (None, infinito). Respeta las calles cerradas del grafo.

    A* es como Dijkstra, pero ordena la cola por  f = metros_recorridos + estimación,
    donde la estimación es la distancia en línea recta hasta el destino. Como la línea recta
    nunca es más larga que ir por calles, la estimación no se pasa y el camino sigue siendo
    el más corto, pero se exploran muchas menos esquinas.
    Tiempo O(E log V) en el peor caso, espacio O(V)."""
    clave = (id(grafo), grafo.version, origen, destino)
    if clave in _cache:
        return _cache[clave]
    resultado = _buscar(grafo, origen, destino)
    if len(_cache) >= _CACHE_MAXIMO:
        _cache.clear()
    _cache[clave] = resultado
    return resultado


def _buscar(grafo, origen, destino):
    if origen == destino:
        return [origen], 0.0

    lat_d, lon_d = grafo.nodos[destino]
    metros = {origen: 0.0}                  # esquina -> mejor distancia conocida desde el origen
    de_donde = {}                           # esquina -> esquina anterior en el mejor camino
    hecho = set()                           # esquinas ya cerradas (su mejor camino es definitivo)
    contador = 0                            # desempata en la cola sin comparar ids
    cola = [(distancia_recta(*grafo.nodos[origen], lat_d, lon_d), contador, origen)]

    while cola:
        _, _, actual = heapq.heappop(cola)
        if actual in hecho:
            continue
        if actual == destino:               # reconstruir el camino yendo hacia atrás
            camino = [destino]
            while camino[-1] != origen:
                camino.append(de_donde[camino[-1]])
            camino.reverse()
            return camino, metros[destino]
        hecho.add(actual)

        for vecino, largo, _nombre, _id in grafo.vecinos(actual):   # vecinos() salta las calles cerradas
            nuevo = metros[actual] + largo
            if nuevo < metros.get(vecino, float("inf")):
                metros[vecino] = nuevo
                de_donde[vecino] = actual
                contador += 1
                estimacion = distancia_recta(*grafo.nodos[vecino], lat_d, lon_d)
                heapq.heappush(cola, (nuevo + estimacion, contador, vecino))

    return None, float("inf")
