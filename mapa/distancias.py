"FAUSTO: MODELO 1 - mapa/distancias.py"
# distancias.py
# Distancia entre dos puntos. Es lo que usan todos los algoritmos del proyecto.
# Por defecto es en línea recta.
# Cuando la aplicación llama a usar_grafo(grafo), distancia() pasa a devolver los metros reales por las calles del mapa (con A*) y respeta las calles cerradas.

import math

# Estas variables preparan el sistema para calcular distancias sin repetir operaciones costosas.
_grafo = None      # Mapa con el que se miden las distancias por calles (el grafo: esquinas y calles con su largo en metros). None = aún no hay mapa
_version = -1      # Versión del mapa con la que se llenó la memoria. El mapa cambia de versión al cerrar o abrir una calle
_esquinas = {}     # (lat, lon) -> Esquina más cercana. A* solo entiende esquinas y buscarla es lento, por eso se guarda
_pares = {}        # (esquina_a, esquina_b) -> Metros, cada par se calcula una sola vez porque A* es lo más lento


# Esta función aplica la fórmula de Haversine para calcular la distancia aproximada entre dos puntos de la superficie terrestre, utilizando sus latitudes y longitudes.
def distancia_recta(lat1, lon1, lat2, lon2):
    R = 6371000  # Radio de la Tierra en metros
    f1, f2 = math.radians(lat1), math.radians(lat2)  # sin y cos trabajan en radianes, las coordenadas vienen en grados
    df = f2 - f1
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2  # El cos existe porque un grado de longitud mide menos lejos del ecuador
    return 2 * R * math.asin(math.sqrt(a))  # Ángulo entre los puntos por el radio = largo del arco = metros


# Esta función recibe el mapa que se utilizará para calcular las distancias y lo guarda en _grafo
def usar_grafo(grafo):
    # Activa las distancias por calles. Con None se vuelve a la línea recta
    global _grafo, _version  # Sin esto Python crearía variables locales y las de afuera no cambiarían
    _grafo = grafo # Guarda el mapa recibido
    _esquinas.clear()  # Borran los resultados guardados anteriormente, porque podrían corresponder a otro mapa.
    _pares.clear()
    _version = grafo.version if grafo is not None else -1  # Registra la versión del mapa. Si grafo es None, asigna -1.


# Esta función convierte la ubicación geográfica de un pedido o repartidor en el identificador de una esquina del grafo.
def esquina_de(punto):
    # Esquina del mapa más cercana a un objeto con lat y lon (se guarda para no repetir)
    clave = (round(punto.lat, 6), round(punto.lon, 6))  # Tupla de números (clave con coordenadas del putno), redondeado a 6 decimales ≈ 0.1 m
    if clave not in _esquinas: # Comprueba si ya se buscó la esquina más cercana a esas coordenadas.
        _esquinas[clave] = _grafo.esquina_mas_cercana(punto.lat, punto.lon) # Si no se había buscado, llama al grafo para encontrar la esquina más cercana y guarda su identificador.
    return _esquinas[clave] # Devuelve el identificador


# Esta es la función que utilizarán los demás algoritmos para obtener la distancia entre dos objetos
def distancia(a, b):
    # Recibe dos objetos con atributos lat y lon (pedido, repartidor...) y devuelve metros. Si no hay camino entre los dos (por calles cerradas), devuelve infinito.
    global _version  # Se reasigna más abajo
    if _grafo is None:
        return distancia_recta(a.lat, a.lon, b.lat, b.lon) # Llama a distancia_recta() y devuelve la distancia en línea recta.

    # Compara la versión actual del grafo con la que se registró anteriormente
    if _grafo.version != _version:        # Se cerró o se abrió una calle: lo guardado ya no sirve
        # Si son diferentes, borra las distancias guardadas porque los cierres o aperturas de calles pueden cambiar los recorridos.
        _pares.clear()  # _esquinas se queda: Cerrar una calle no mueve los pedidos
        _version = _grafo.version

    clave = (esquina_de(a), esquina_de(b))  # Llama a esquina_de() para obtener las esquinas más cercanas a ambos objetos.
    if clave not in _pares: # Si la distancia no está guardada, importa y ejecuta A* con el grafo, la esquina de origen y la esquina de destino.
        from mapa.caminos import a_estrella
        _pares[clave] = a_estrella(_grafo, clave[0], clave[1])[1]  # A* devuelve una tupla con la ruta y sus metros totales. El índice [1] extrae los metros y los guarda en _pares.
    return _pares[clave]
