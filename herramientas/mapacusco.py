"FAUSTO: MODELO 2 - herramientas/mapacusco.py"
#mapacusco.py
#Descarga la red vial de Cusco desde OpenStreetMap (con osmnx) y la guarda en herramientas/grafo.json (junto a este archivo).

import json
import math
from pathlib import Path
import osmnx as ox # OpenStreetMap para Python

# ---------------------------------------------------------------------------
# Carpeta de trabajo
# ---------------------------------------------------------------------------
try:
    CARPETA = Path(__file__).resolve().parent
except NameError:                      # Colab / cuaderno: no existe __file__
    CARPETA = Path.cwd()
ox.settings.use_cache = True
ox.settings.cache_folder = str(CARPETA / "cache")

# ---------------------------------------------------------------------------
# Distritos (nombre, lat, lon): definen el área que cubre el mapa
# y sirven como sectores para clasificar pedidos
# ---------------------------------------------------------------------------
DISTRITOS = [
    ("Santiago", -13.576680075172892, -71.98784062083368),
    ("Ccorca", -13.581894133668104, -72.06040129387019),
    ("Poroy", -13.499018294799225, -72.04087257760868),
    ("San Jerónimo", -13.525301066856702, -71.86965795184344),
    ("San Sebastián", -13.552614852902776, -71.94027775226438),
    ("Saylla", -13.549021173086478, -71.8281371779059),
    ("Wánchaq", -13.534595892793657, -71.94905381593156),
    ("Cusco", -13.489926143752763, -71.98757320970638),
]

BUFFER = 0.01  # margen extra en grados (~1 km) para no cortar calles justo en el borde

# ---------------------------------------------------------------------------
# Importancia de cada tipo de vía (1 = la más importante). Sirve para decidir qué
# nombres se muestran de lejos y cuáles solo al acercar el mapa. Cualquier otro
# tipo (residential, unclassified, living_street...) vale 4.
# ---------------------------------------------------------------------------
RANGOS_VIA = {
    "motorway": 1, "motorway_link": 1, "trunk": 1, "trunk_link": 1,
    "primary": 1, "primary_link": 1,
    "secondary": 2, "secondary_link": 2,
    "tertiary": 3, "tertiary_link": 3,
}
LARGO_MINIMO = 40        # metros: no se rotulan tramos más cortos (salvo el más largo de cada calle)
M_POR_GRADO = 111320     # metros que mide un grado de latitud


def primero(valor):
    # osmnx a veces entrega una lista de valores; se usa el primero
    if isinstance(valor, list):
        return valor[0] if valor else ""
    return valor or ""


def metros_entre(lat1, lon1, lat2, lon2):
    # Distancia aproximada en metros (suficiente para distancias cortas)
    return math.hypot((lat2 - lat1) * M_POR_GRADO,
                      (lon2 - lon1) * M_POR_GRADO * math.cos(math.radians(lat1)))


# ---------------------------------------------------------------------------
# Rectángulo que cubre todos los distritos (orden de osmnx 2.x: oeste, sur, este, norte)
# ---------------------------------------------------------------------------
lats = [d[1] for d in DISTRITOS]
lons = [d[2] for d in DISTRITOS]
bbox = (min(lons) - BUFFER, min(lats) - BUFFER, max(lons) + BUFFER, max(lats) + BUFFER)

# ---------------------------------------------------------------------------
# Descarga de la red vial para autos
# ---------------------------------------------------------------------------
print("Descargando red vial (puede tardar varios minutos)...")
G = ox.graph_from_bbox(bbox=bbox, network_type="drive")
print(f"Descargado: {len(G.nodes)} nodos, {len(G.edges)} aristas")

# Se conserva solo la parte del mapa en la que se puede ir de cualquier esquina
# a cualquier otra; así ninguna ruta falla por esquinas aisladas o sin salida
G = ox.truncate.largest_component(G, strongly=True)
print(f"Conectado: {len(G.nodes)} nodos, {len(G.edges)} aristas")

# ---------------------------------------------------------------------------
# Nodos: cada esquina con su id y sus coordenadas
# ---------------------------------------------------------------------------
nodos = [{"id": str(n), "lat": round(d["y"], 6), "lon": round(d["x"], 6)}
         for n, d in G.nodes(data=True)]

# ---------------------------------------------------------------------------
# Aristas: cada tramo de calle, con id propio, longitud en metros, nombre y sentido
# Si OpenStreetMap no tiene nombre, se usa la referencia de la vía (ref); si tampoco
# la tiene, queda "Sin nombre"
# ---------------------------------------------------------------------------
aristas = []
tramos_por_calle = {}     # nombre -> lista de (largo, origen, destino, rango); para las etiquetas
vistos = set()            # una calle de doble sentido aparece dos veces; se rotula una sola
for i, (u, v, k, data) in enumerate(G.edges(keys=True, data=True)):
    nombre = primero(data.get("name")) or primero(data.get("ref")) or "Sin nombre"
    largo = round(data.get("length", 0), 2)  # metros
    aristas.append({
        "id": i,
        "origen": str(u),
        "destino": str(v),
        "costo": largo,
        "nombre": nombre,
        "sentido_unico": bool(data.get("oneway", False)),
    })
    if nombre != "Sin nombre":
        clave = (min(u, v), max(u, v), nombre)
        if clave not in vistos:
            vistos.add(clave)
            rango = RANGOS_VIA.get(primero(data.get("highway")), 4)
            tramos_por_calle.setdefault(nombre, []).append((largo, str(u), str(v), rango))

# ---------------------------------------------------------------------------
# Lista de nombres de calles, para elegir cuáles cerrar desde la interfaz
# (los tramos "Sin nombre" solo se pueden cerrar por su id)
# ---------------------------------------------------------------------------
calles = sorted({a["nombre"] for a in aristas if a["nombre"] != "Sin nombre"})

# ---------------------------------------------------------------------------
# Etiquetas: puntos del mapa donde se puede escribir el nombre de una calle.
# Para cada calle se toman sus tramos más largos, separados entre sí; las avenidas
# (rango 1 y 2) llevan más etiquetas que las calles chicas. Cada etiqueta trae:
#   nombre, lat y lon (punto medio del tramo), angulo (grados, para escribir el texto
#   a lo largo de la calle, sin quedar de cabeza), rango (1 a 4) y largo del tramo (m)
# ---------------------------------------------------------------------------
posicion = {n["id"]: (n["lat"], n["lon"]) for n in nodos}
etiquetas = []
for nombre, tramos in tramos_por_calle.items():
    rango = min(t[3] for t in tramos)              # la calle toma el rango de su tramo más importante
    maximo, separacion = (8, 500) if rango <= 2 else (3, 300)
    elegidas = []
    for largo, u, v, _r in sorted(tramos, reverse=True):     # primero los tramos más largos
        if largo < LARGO_MINIMO and elegidas:
            break
        lat1, lon1 = posicion[u]
        lat2, lon2 = posicion[v]
        lat_m, lon_m = (lat1 + lat2) / 2, (lon1 + lon2) / 2
        if any(metros_entre(lat_m, lon_m, e["lat"], e["lon"]) < separacion for e in elegidas):
            continue
        # Dirección del tramo en pantalla (este = 0 grados, sentido contrario a las agujas)
        angulo = math.degrees(math.atan2(lat2 - lat1, (lon2 - lon1) * math.cos(math.radians(lat1))))
        if angulo > 90:
            angulo -= 180
        elif angulo <= -90:
            angulo += 180
        elegidas.append({"nombre": nombre, "lat": round(lat_m, 6), "lon": round(lon_m, 6),
                         "angulo": round(angulo, 1), "rango": rango, "largo": round(largo)})
        if len(elegidas) >= maximo:
            break
    etiquetas.extend(elegidas)

# ---------------------------------------------------------------------------
# Límites del mapa: sirven para convertir coordenadas a píxeles al dibujar
# ---------------------------------------------------------------------------
limites = {
    "norte": max(n["lat"] for n in nodos),
    "sur": min(n["lat"] for n in nodos),
    "este": max(n["lon"] for n in nodos),
    "oeste": min(n["lon"] for n in nodos),
}

# ---------------------------------------------------------------------------
# Distritos tal cual (nombre y coordenadas)
# ---------------------------------------------------------------------------
distritos = [{"nombre": n, "lat": la, "lon": lo} for n, la, lo in DISTRITOS]

# ---------------------------------------------------------------------------
# Guardar todo en herramientas/grafo.json
# ---------------------------------------------------------------------------
salida = {
    "limites": limites,
    "distritos": distritos,
    "calles": calles,
    "etiquetas": etiquetas,
    "nodos": nodos,
    "aristas": aristas,
}
with open(CARPETA / "grafo.json", "w", encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False)

print(f"grafo.json generado: {len(nodos)} nodos, {len(aristas)} aristas, "
      f"{len(calles)} calles con nombre, {len(etiquetas)} etiquetas.")
