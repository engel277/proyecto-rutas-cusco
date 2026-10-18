"FAUSTO: MODELO 2 - mapa/distancias.py"
# distancias.py
# Distancia entre dos puntos. La usan los algoritmos del proyecto (Greedy, Divide y Vencerás).
# Es siempre en línea recta, calculada con la fórmula de Haversine.

import math


# Esta función aplica la fórmula de Haversine para calcular la distancia aproximada entre dos puntos de la superficie terrestre, utilizando sus latitudes y longitudes.
def distancia_recta(lat1, lon1, lat2, lon2):
    # Metros en línea recta entre dos coordenadas (fórmula de Haversine)
    R = 6371000  # Radio de la Tierra en metros
    f1, f2 = math.radians(lat1), math.radians(lat2)  # sin y cos trabajan en radianes, las coordenadas vienen en grados
    df = f2 - f1
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2  # El cos existe porque un grado de longitud mide menos lejos del ecuador
    return 2 * R * math.asin(math.sqrt(a))  # Ángulo entre los puntos por el radio = largo del arco = metros


# Esta es la función que utilizarán los demás algoritmos para obtener la distancia entre dos objetos
def distancia(a, b):
    # Recibe dos objetos con atributos lat y lon (pedido, repartidor...) y devuelve metros
    return distancia_recta(a.lat, a.lon, b.lat, b.lon)  # Llama a distancia_recta() con las coordenadas de ambos objetos y devuelve la distancia en línea recta
