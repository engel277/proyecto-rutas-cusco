# recorridos.py
# Convierte una lista de paradas (repartidor, pedido, pedido...) en el recorrido REAL por calles.
# Los algoritmos (Greedy, Zonas, Mochila) deciden el ORDEN de visita; este módulo calcula por
# dónde se va de una parada a la siguiente y cuántos metros son de verdad.

from dataclasses import dataclass, field

from mapa.caminos import a_estrella
from mapa.distancias import distancia_recta


@dataclass
class Recorrido:
    trazo: list = field(default_factory=list)    # Puntos (lat, lon) que siguen las calles, listos para dibujar
    metros: float = 0.0                          # Metros totales por calles (incluye llegar de la parada a la esquina)
    tramos: list = field(default_factory=list)   # Metros de cada tramo entre paradas seguidas
    sin_camino: int = 0                          # Tramos sin camino por calles (calles cerradas): se dibujan rectos


_esquinas = {}    # (grafo, lat, lon) -> esquina más cercana. Buscarla recorre todo el mapa, por eso se guarda


def _esquina(grafo, parada):
    clave = (id(grafo), round(parada.lat, 6), round(parada.lon, 6))
    if clave not in _esquinas:
        _esquinas[clave] = grafo.esquina_mas_cercana(parada.lat, parada.lon)
    return _esquinas[clave]


def recorrido_por_calles(grafo, paradas):
    """`paradas`: objetos con lat y lon, en el orden en que se visitan (el primero suele ser el
    repartidor). Devuelve un Recorrido. Con grafo=None (o si un tramo no tiene camino por calles)
    ese tramo se une con línea recta, así nunca falla."""
    paradas = list(paradas)
    recorrido = Recorrido(trazo=[(paradas[0].lat, paradas[0].lon)] if paradas else [])

    for a, b in zip(paradas, paradas[1:]):
        camino = None
        if grafo is not None:
            esquina_a, esquina_b = _esquina(grafo, a), _esquina(grafo, b)
            camino, por_calles = a_estrella(grafo, esquina_a, esquina_b)

        if camino is None:                           # sin mapa o sin camino: línea recta
            metros = distancia_recta(a.lat, a.lon, b.lat, b.lon)
            if grafo is not None:
                recorrido.sin_camino += 1
        else:
            # Caminar de la parada a su esquina y de la esquina final a la parada también cuenta
            lat_a, lon_a = grafo.nodos[esquina_a]
            lat_b, lon_b = grafo.nodos[esquina_b]
            metros = (distancia_recta(a.lat, a.lon, lat_a, lon_a) + por_calles
                      + distancia_recta(lat_b, lon_b, b.lat, b.lon))
            recorrido.trazo.extend(grafo.nodos[e] for e in camino)

        recorrido.trazo.append((b.lat, b.lon))
        recorrido.tramos.append(metros)
        recorrido.metros += metros
    return recorrido
