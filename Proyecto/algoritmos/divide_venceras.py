# algoritmos/divide_venceras.py
# Divide y Vencerás: segmenta la ciudad en zonas, una por repartidor.
#
# Reutiliza lo que ya existe (no se reescribe nada):
#   - merge_sort           -> algoritmos/ordenacion_busqueda.py  (Persona 2)
#   - vecino_mas_cercano   -> algoritmos/greedy.py               (Persona 2)

from algoritmos.ordenacion_busqueda import merge_sort
from algoritmos.greedy import vecino_mas_cercano


def _dispersion(puntos, atributo):
    """Diferencia entre el mayor y el menor valor de `atributo` ('lat' o 'lon')."""
    if not puntos:
        return 0.0
    valores = [getattr(p, atributo) for p in puntos]
    return max(valores) - min(valores)


# ---------------------------------------------------------------------------
# DIVIDIR EN ZONAS
# ---------------------------------------------------------------------------
def dividir_en_zonas(pedidos, repartidores):
    """Reparte los pedidos entre los repartidores dividiendo el mapa en zonas.

    DIVIDIR : se mide la dispersión de los pedidos en latitud y en longitud y se
              elige el eje donde están más separados. Se ordenan pedidos y
              repartidores por ese eje (merge_sort) y se cortan "a la mitad":
              la mitad de los repartidores se queda con la mitad de los pedidos
              del lado norte/oeste, y el resto con el otro lado.
    VENCER  : caso base = 1 repartidor -> se queda con todos los pedidos que
              le llegaron (su zona).
    COMBINAR: se juntan las listas de zonas de las dos mitades.

    No modifica las listas recibidas.
    Devuelve una lista de (repartidor, pedidos_de_su_zona).

    Costo: T(n) = 2T(n/2) + O(n log n)  ->  O(n log n log r)  (r = repartidores)
    """
    if len(repartidores) == 0:
        return []

    # Caso base: un solo repartidor se lleva toda su zona
    if len(repartidores) == 1:
        return [(repartidores[0], list(pedidos))]

    # Eje de corte: el de mayor dispersión (si no hay pedidos, se mira a los repartidores)
    referencia = pedidos if len(pedidos) > 0 else repartidores
    if _dispersion(referencia, "lat") >= _dispersion(referencia, "lon"):
        eje = "lat"
    else:
        eje = "lon"
    clave = lambda punto: getattr(punto, eje)

    pedidos_ord = merge_sort(pedidos, clave)
    repartidores_ord = merge_sort(repartidores, clave)

    # Cortar a la mitad. Los pedidos se reparten en proporción a los repartidores
    # de cada lado (con cantidad par es exactamente la mitad).
    mitad_rep = len(repartidores_ord) // 2
    corte = int(round(len(pedidos_ord) * mitad_rep / len(repartidores_ord)))

    zonas_a = dividir_en_zonas(pedidos_ord[:corte], repartidores_ord[:mitad_rep])
    zonas_b = dividir_en_zonas(pedidos_ord[corte:], repartidores_ord[mitad_rep:])
    return zonas_a + zonas_b


# ---------------------------------------------------------------------------
# RUTAS POR ZONA
# ---------------------------------------------------------------------------
def rutas_por_zona(zonas):
    """Para cada zona calcula la ruta del repartidor con vecino_mas_cercano.

    Recibe lo que devuelve dividir_en_zonas.
    Devuelve una lista de (repartidor, ruta, metros), donde `ruta` es la lista
    de pedidos en el orden de visita y `metros` el recorrido total.
    (Si el peso de la zona supera la capacidad, vecino_mas_cercano deja fuera
    los pedidos que no caben; se pueden saber con len(pedidos_zona) - len(ruta).)
    """
    resultado = []
    for repartidor, pedidos_zona in zonas:
        ruta, metros = vecino_mas_cercano(repartidor, pedidos_zona)
        resultado.append((repartidor, ruta, metros))
    return resultado
