# algoritmos/ordenacion_busqueda.py
# Merge Sort (hecho a mano, sin sorted), búsqueda binaria y agrupación por sector.

import unicodedata


# ---------------------------------------------------------------------------
# MERGE SORT
# ---------------------------------------------------------------------------
def merge_sort(lista, clave=None):
    """Ordena `lista` de menor a mayor según `clave` (una función que recibe un
    elemento y devuelve el valor a comparar). Devuelve una lista NUEVA y no
    modifica la original. Es estable: si dos elementos tienen la misma clave,
    conservan su orden relativo.

    Ejemplos:
        merge_sort(pedidos, lambda p: p.prioridad)
        merge_sort(pedidos, lambda p: (p.prioridad, p.id))   # desempata por id
    """
    if clave is None:
        clave = lambda x: x

    # Caso base: 0 o 1 elemento ya está ordenado
    if len(lista) <= 1:
        return list(lista)

    # Dividir en dos mitades y ordenar cada una
    medio = len(lista) // 2
    izquierda = merge_sort(lista[:medio], clave)
    derecha = merge_sort(lista[medio:], clave)

    # Combinar las dos mitades ya ordenadas
    return _mezclar(izquierda, derecha, clave)


def _mezclar(izquierda, derecha, clave):
    resultado = []
    i = 0
    j = 0
    while i < len(izquierda) and j < len(derecha):
        # "<=" mantiene la estabilidad (en empate sale primero el de la izquierda)
        if clave(izquierda[i]) <= clave(derecha[j]):
            resultado.append(izquierda[i])
            i += 1
        else:
            resultado.append(derecha[j])
            j += 1
    # Lo que sobre de alguna de las dos mitades ya está ordenado
    resultado.extend(izquierda[i:])
    resultado.extend(derecha[j:])
    return resultado


# ---------------------------------------------------------------------------
# BÚSQUEDA BINARIA
# ---------------------------------------------------------------------------
def busqueda_binaria(pedidos_ordenados_por_id, id_buscado):
    """Busca un pedido por su id en una lista YA ORDENADA por id (de menor a
    mayor). Devuelve el Pedido o None si no existe. Costo: O(log n)."""
    inicio = 0
    fin = len(pedidos_ordenados_por_id) - 1

    while inicio <= fin:
        medio = (inicio + fin) // 2
        pedido = pedidos_ordenados_por_id[medio]
        if pedido.id == id_buscado:
            return pedido
        if pedido.id < id_buscado:
            inicio = medio + 1
        else:
            fin = medio - 1
    return None


# ---------------------------------------------------------------------------
# AGRUPAR POR SECTOR
# ---------------------------------------------------------------------------
def agrupar_por_sector(pedidos):
    """Devuelve un diccionario {sector: [pedidos de ese sector]}."""
    grupos = {}
    for pedido in pedidos:
        if pedido.sector not in grupos:
            grupos[pedido.sector] = []
        grupos[pedido.sector].append(pedido)
    return grupos


# ---------------------------------------------------------------------------
# UTILIDAD: comparar textos sin importar mayúsculas ni tildes
# ("wanchaq" debe encontrar "Wánchaq", "san jeronimo" a "San Jerónimo")
# ---------------------------------------------------------------------------
def normalizar_texto(texto):
    descompuesto = unicodedata.normalize("NFD", texto)
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return sin_tildes.lower().strip()
