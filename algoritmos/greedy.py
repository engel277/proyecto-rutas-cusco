# algoritmos/greedy.py
# Algoritmos voraces (greedy): vecino más cercano y asignación de pedidos urgentes.

# distancia(a, b) la entrega la Persona 1 en mapa/distancias.py. Mientras ese
# archivo no exista se usa una copia local (Haversine, en línea recta) para
# poder probar todo. Cuando exista, se usa automáticamente la de Persona 1.
try:
    from mapa.distancias import distancia
except ImportError:
    from math import sin, cos, asin, sqrt, radians

    def distancia(a, b):
        """Metros en línea recta entre dos objetos con atributos lat y lon."""
        radio_tierra = 6371000  # metros
        lat1, lon1 = radians(a.lat), radians(a.lon)
        lat2, lon2 = radians(b.lat), radians(b.lon)
        d_lat = lat2 - lat1
        d_lon = lon2 - lon1
        h = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
        return 2 * radio_tierra * asin(sqrt(h))


INF = float("inf")   # distancia(a, b) devuelve infinito si no hay camino por calles (calles cerradas)


# ---------------------------------------------------------------------------
# VECINO MÁS CERCANO
# ---------------------------------------------------------------------------
def vecino_mas_cercano(repartidor, pedidos):
    """Arma la ruta de un repartidor con la estrategia del vecino más cercano.

    1. Parte de la posición del repartidor con todos los pedidos pendientes.
    2. En cada paso elige el pendiente con menor distancia(posición_actual, pedido).
    3. Si el peso de ese pedido haría que la carga total supere la capacidad del
       repartidor, no se toma y se prueba con el siguiente más cercano.
    4. Un pedido al que no se puede llegar (distancia infinita por calles cerradas)
       también se salta, para que los metros totales nunca sean infinitos.
    5. Termina cuando no queda ningún pendiente que quepa y sea alcanzable.

    No modifica la lista `pedidos` que recibe.
    Devuelve (lista_de_pedidos_en_orden, metros_totales).
    """
    pendientes = list(pedidos)
    ruta = []
    metros_totales = 0.0
    carga_actual = 0.0
    posicion = repartidor            # tiene lat y lon, igual que un pedido

    while pendientes:
        mejor_indice = -1
        mejor_distancia = 0.0

        for i in range(len(pendientes)):
            pedido = pendientes[i]
            # Si no cabe en lo que le queda de capacidad, no se toma
            if carga_actual + pedido.peso > repartidor.capacidad:
                continue
            d = distancia(posicion, pedido)
            if d == INF:                 # sin camino hasta ese pedido
                continue
            if mejor_indice == -1 or d < mejor_distancia:
                mejor_indice = i
                mejor_distancia = d

        # Ningún pendiente cabe: se termina la ruta
        if mejor_indice == -1:
            break

        elegido = pendientes.pop(mejor_indice)
        ruta.append(elegido)
        metros_totales += mejor_distancia
        carga_actual += elegido.peso
        posicion = elegido           # desde aquí se busca el siguiente

    return ruta, metros_totales


# ---------------------------------------------------------------------------
# ASIGNAR PEDIDO URGENTE
# ---------------------------------------------------------------------------
def asignar_urgente(pedido, repartidores):
    """Devuelve el repartidor más cercano al pedido entre los que tienen
    capacidad suficiente (capacidad >= peso del pedido) y con camino hasta el
    pedido. Si ninguno puede llevarlo, devuelve None."""
    mejor = None
    mejor_distancia = 0.0

    for repartidor in repartidores:
        if repartidor.capacidad < pedido.peso:
            continue
        d = distancia(repartidor, pedido)
        if d == INF:                     # sin camino (calles cerradas)
            continue
        if mejor is None or d < mejor_distancia:
            mejor = repartidor
            mejor_distancia = d

    return mejor
