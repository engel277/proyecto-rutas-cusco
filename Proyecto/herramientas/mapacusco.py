"FAUSTO: MODELO 1 - herramientas/mapacusco.py"
#mapacusco.py
#Descarga la red vial de Cusco desde OpenStreetMap (con osmnx) y la guarda en herramientas/grafo.json (junto a este archivo).

import json
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
# ---------------------------------------------------------------------------
aristas = []
for i, (u, v, k, data) in enumerate(G.edges(keys=True, data=True)):
    nombre = data.get("name", "")
    if isinstance(nombre, list):                   # a veces OSM da varios nombres
        nombre = nombre[0] if nombre else ""
    aristas.append({
        "id": i,
        "origen": str(u),
        "destino": str(v),
        "costo": round(data.get("length", 0), 2),  # metros
        "nombre": nombre if nombre else "Sin nombre",
        "sentido_unico": bool(data.get("oneway", False)),
    })

# ---------------------------------------------------------------------------
# Lista de nombres de calles, para elegir cuáles cerrar desde la interfaz
# (los tramos "Sin nombre" solo se pueden cerrar por su id)
# ---------------------------------------------------------------------------
calles = sorted({a["nombre"] for a in aristas if a["nombre"] != "Sin nombre"})

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
    "nodos": nodos,
    "aristas": aristas,
}
with open(CARPETA / "grafo.json", "w", encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False)

print(f"grafo.json generado: {len(nodos)} nodos, {len(aristas)} aristas, "
      f"{len(calles)} calles con nombre.")
