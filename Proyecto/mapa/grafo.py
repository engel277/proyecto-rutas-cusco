"FAUSTO: MODELO 1 - mapa/grafo.py"
# grafo.py
# Carga el mapa (grafo.json) y permite consultarlo y cerrar calles.

import json
from pathlib import Path

from mapa.distancias import distancia_recta

# Ruta donde se busca grafo.json si no se indica otra ubicación por defecto de grafo.json: herramientas/grafo.json
RUTA_GRAFO = Path(__file__).resolve().parent.parent / "herramientas" / "grafo.json"


# Clase que guarda el mapa en memoria: las esquinas, las calles que las unen y cuáles están cerradas
class Grafo:
    # Crea el grafo vacío; los datos se llenan después con cargar()
    def __init__(self):
        self.nodos = {}               # id de esquina -> (lat, lon)
        self.calles = {}              # id de esquina -> lista de (vecino, metros, nombre, id_arista). Una arista es un tramo de calle entre dos esquinas
        self.distritos = []           # Lista de (nombre, lat, lon)
        self.nombres_calles = []      # Nombres de calles que se pueden cerrar
        self.limites = {}             # Norte, sur, este, oeste
        self.cerradas_nombre = set()  # Calles cerradas por nombre (cierra todos los tramos que se llamen así)
        self.cerradas_id = set()      # Tramos cerrados por id (para los "Sin nombre", que no se pueden cerrar por nombre)
        self.version = 0              # Sube cada vez que se abre o cierra una calle. distancias.py la compara para saber si sus distancias guardadas quedaron viejas

    # ------------------------------------------------------------------
    # Carga
    # ------------------------------------------------------------------
    # Este método transforma los datos de grafo.json en las estructuras que utilizarán los algoritmos (los diccionarios del grafo).
    def cargar(self, ruta=RUTA_GRAFO):
        # Abre el archivo con codificación UTF-8 y convierte su contenido JSON en diccionarios y listas de Python
        with open(ruta, encoding="utf-8") as f:  # utf-8 para que se lean bien las tildes de los nombres de calles
            datos = json.load(f)  # Convierte el JSON en diccionarios y listas de Python

        # Datos generales del mapa: Copia los límites y los nombres de calles, y transforma los distritos en tuplas con su nombre y coordenadas.
        self.limites = datos["limites"]
        self.nombres_calles = datos["calles"]
        self.distritos = [(d["nombre"], d["lat"], d["lon"]) for d in datos["distritos"]]  # De cada distrito guarda solo nombre y coordenadas

        # Para cada nodo, guarda sus coordenadas en self.nodos y crea una lista vacía en self.calles, preparada para recibir los tramos que salen de esa esquina.
        for n in datos["nodos"]:
            self.nodos[n["id"]] = (n["lat"], n["lon"])
            self.calles[n["id"]] = []

        # Cada arista se agrega a la lista de calles de su esquina de origen. La tupla contiene cuatro datos
        # a["destino"]: Esquina a la que se llega.
        # a["costo"]: Metros que mide ese tramo.
        # a["nombre"]: Nombre de la calle.
        # a["id"]: Identificador único del tramo, según los datos generados.
        for a in datos["aristas"]:
            self.calles[a["origen"]].append((a["destino"], a["costo"], a["nombre"], a["id"]))

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    # Devuelve las calles por las que se puede salir de una esquina. A* y Backtracking usan esto para avanzar
    def vecinos(self, esquina):
        # Calles que salen de una esquina, sin las cerradas: (vecino, metros, nombre, id)
        return [c for c in self.calles[esquina]
                if c[2] not in self.cerradas_nombre and c[3] not in self.cerradas_id]  # c[2] es el nombre y c[3] el id; se descarta la calle si cualquiera de los dos está cerrado

    # Convierte unas coordenadas en una esquina del grafo, porque A* solo trabaja con esquinas
    def esquina_mas_cercana(self, lat, lon):
        # Id de la esquina más cercana a unas coordenadas (ubica un pedido en el mapa)
        mejor, mejor_d = None, float("inf")  # Empieza con distancia infinita para que cualquier esquina la mejore
        for id_, (la, lo) in self.nodos.items():  # Revisa todas las esquinas una por una
            d = distancia_recta(lat, lon, la, lo)
            if d < mejor_d:  # Si esta esquina está más cerca que la mejor hasta ahora, la reemplaza
                mejor, mejor_d = id_, d
        return mejor

    # Dice en qué distrito cae un pedido (sirve para agrupar por sector)
    def sector_de(self, lat, lon):
        # Nombre del distrito más cercano a unas coordenadas
        return min(self.distritos, key=lambda d: distancia_recta(lat, lon, d[1], d[2]))[0]  # Elige el distrito con menor distancia al punto; [0] toma su nombre

    # Dado dos esquinas seguidas de una ruta, dice por qué calle se va (para mostrar la ruta con nombres)
    def nombre_tramo(self, origen, destino):
        # Nombre de la calle que une dos esquinas seguidas (si hay varias, la más corta)
        tramos = [c for c in self.calles[origen] if c[0] == destino]  # Calles que salen de origen y llegan a destino
        return min(tramos, key=lambda c: c[1])[2] if tramos else "Sin nombre"  # Si hay varias se queda con la de menos metros; si no hay ninguna, "Sin nombre"

    # ------------------------------------------------------------------
    # Cierre y apertura de calles
    # ------------------------------------------------------------------
    # Estos métodos modifican los conjuntos de calles cerradas y aumentan version para avisar que el mapa ha cambiado.
    def cerrar_calle(self, nombre):
        # Cierra todos los tramos que tengan ese nombre
        if nombre == "Sin nombre":  # Muchos tramos distintos comparten este nombre, cerrarlo por nombre bloquearía todos a la vez
            raise ValueError("Las calles sin nombre se cierran por id con cerrar_tramo().")
        self.cerradas_nombre.add(nombre)
        self.version += 1  # Avisa que el mapa cambió

    # Vuelve a abrir una calle cerrada por nombre
    def abrir_calle(self, nombre):
        self.cerradas_nombre.discard(nombre)  # discard no da error si la calle no estaba cerrada
        self.version += 1

    # Cierra un solo tramo, usando su id
    def cerrar_tramo(self, id_arista):
        self.cerradas_id.add(id_arista)
        self.version += 1

    # Vuelve a abrir un tramo cerrado por id
    def abrir_tramo(self, id_arista):
        self.cerradas_id.discard(id_arista)
        self.version += 1

    # Deja todas las calles abiertas
    def abrir_todas(self):
        self.cerradas_nombre.clear()
        self.cerradas_id.clear()
        self.version += 1
