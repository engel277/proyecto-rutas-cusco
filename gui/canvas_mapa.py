"MODELO 2: Daniel - gui/canvas_mapa.py" 
# gui/canvas_mapa.py
# Persona 4 (Daniel): CanvasMapa, el mapa de Cusco dibujado sobre un tk.Canvas.
#
# Qué hace:
#   - Dibuja todas las calles del grafo (mapa base) y los nombres de los distritos.
#   - Dibuja pedidos (color según prioridad), repartidores y rutas (líneas de colores).
#   - Dibuja en rojo las calles cerradas.
#   - Escribe el nombre de las calles (grafo.etiquetas) con más o menos detalle según el zoom.
#   - Zoom con la rueda del mouse y desplazamiento arrastrando con el mouse.
#   - Avisa a la ventana cuando el usuario hace clic o mueve el mouse sobre el mapa.
#
# Métodos que usan las pestañas de los demás (los nombres ya están acordados):
#   convertir(lat, lon)                          -> (x, y) en píxeles del canvas
#   dibujar_pedidos(pedidos)                     (Persona 2: pestana_pedidos.py)
#   dibujar_ruta(puntos, color="#1f77b4")        (Personas 1, 2 y 3: puntos = lista de (lat, lon))
#   limpiar_rutas()                              (Personas 1, 2 y 3)
#   dibujar_calle_cerrada(nombre=None, id_arista=None) y actualizar_cerradas()
#
# Qué necesita del grafo (el Grafo de Persona 1): limites, calles, distritos,
# cerradas_nombre, cerradas_id, version y etiquetas (si el grafo.json es viejo y no las trae,
# simplemente no se escriben nombres de calles).
#
# NUEVO - Fondo de mapa real (como Google Maps):
#   - Teselas (mosaicos de 256x256 px) de Esri: "Mapa" (calles a color), "Satélite" y "Híbrido"
#     (satélite + nombres). Un selector pequeño aparece arriba a la derecha del mapa.
#   - Se descargan en hilos aparte (la ventana no se congela) y se guardan en la carpeta
#     cache_mapa/ junto al proyecto: la segunda vez que se ve una zona carga al instante.
#   - Necesita Pillow (pip install pillow) e internet la primera vez. Si falta Pillow, el mapa
#     funciona igual que antes (calles sobre fondo liso).
#   - Ningún método público cambió: convertir, inverso, dibujar_ruta, etc. siguen igual.

import io
import math
import os
import queue
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from collections import OrderedDict

try:
    from PIL import Image, ImageTk
    HAY_PIL = True
except ImportError:                  # sin Pillow no hay fondo, pero lo demás funciona
    HAY_PIL = False

# ---------------------------------------------------------------------------
# Colores y tamaños (todo junto para cambiarlos fácil)
# ---------------------------------------------------------------------------
COLOR_FONDO = "#f4f1ea"
COLOR_CALLE = "#b9b4aa"
COLOR_CERRADA = "#d62728"
COLOR_DISTRITO = "#6b6b6b"
COLOR_RUTA = "#1f77b4"            # color por defecto de dibujar_ruta
COLOR_REPARTIDOR = "#5e2a9e"
COLORES_PRIORIDAD = {1: "#d62728",   # urgente
                     2: "#ff9800",   # normal
                     3: "#2e9e44"}   # baja
COLOR_ETIQUETA = "#555555"
FUENTE_ETIQUETA = ("TkDefaultFont", 8)
ANCHO_LETRA = 5                   # píxeles que mide aproximadamente cada letra de la fuente de 8 pt
ALTO_TEXTO = 10                   # píxeles de alto de una línea de texto
CELDA = 12                        # lado (px) de las celdas de la cuadrícula que evita que las etiquetas se pisen
RADIO_PEDIDO = 6
LADO_REPARTIDOR = 7
MARGEN = 20                       # píxeles libres alrededor del mapa al encuadrar
FACTOR_ZOOM = 1.25
ZOOM_MAXIMO = 80                  # veces el zoom inicial
ZOOM_MINIMO = 0.4

# ---------------------------------------------------------------------------
# Fondo de mapa (teselas)
# ---------------------------------------------------------------------------
TESELA = 256                      # lado (px) de cada tesela descargada
Z_MIN, Z_MAX = 10, 18             # niveles de zoom de teselas que se piden (más allá se amplía)
MARGEN_FONDO = 200                # px extra alrededor de la ventana que se precargan al mover el mapa
MAX_TESELAS = 120                 # tope de seguridad por dibujo
MAX_MEMORIA = 300                 # teselas que se guardan en RAM (~60 MB)
HILOS_TESELAS = 6                 # descargas en paralelo
USER_AGENT = "CuscoRutas/1.0 (proyecto academico UNSAAC)"
DIR_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache_mapa")

_ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/"
_URL_CALLES = _ESRI + "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
_URL_SATELITE = _ESRI + "World_Imagery/MapServer/tile/{z}/{y}/{x}"
_URL_NOMBRES = _ESRI + "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"

# Colores del mapa base original (los que se usan sin fondo)
_TEMA_CLARO = {"fondo": "#e8e4d8", "calle": "#6d6d6d", "etiqueta": "#555555", "distrito": "#333333",
               "sombra": None, "texto_pedido": "black", "texto_rep": COLOR_REPARTIDOR}
_TEMA_OSCURO = {"fondo": "#2b2b2b", "calle": "#ffe082", "etiqueta": "#ffffff", "distrito": "#ffffff",
                "sombra": "#000000", "texto_pedido": "#ffffff", "texto_rep": "#e1bee7"}

# urls: la primera es la base; las siguientes se pegan encima (transparentes).
# etiquetas_propias: el fondo ya trae nombres de calles, así que no se escriben los del grafo.
CAPAS = {
    "Mapa":     {"urls": [_URL_CALLES], "ext": "png", "etiquetas_propias": True,
                 "credito": "Fondo: © Esri", "tema": _TEMA_CLARO},
    "Satélite": {"urls": [_URL_SATELITE], "ext": "jpg", "etiquetas_propias": False,
                 "credito": "Fondo: © Esri, Maxar, Earthstar", "tema": _TEMA_OSCURO},
    "Híbrido":  {"urls": [_URL_SATELITE, _URL_NOMBRES], "ext": "jpg", "etiquetas_propias": True,
                 "credito": "Fondo: © Esri, Maxar, Earthstar", "tema": _TEMA_OSCURO},
    "Sin fondo": {"urls": [], "ext": "png", "etiquetas_propias": False,
                  "credito": "", "tema": {"fondo": COLOR_FONDO, "calle": COLOR_CALLE,
                                          "etiqueta": COLOR_ETIQUETA, "distrito": COLOR_DISTRITO,
                                          "sombra": None, "texto_pedido": "black",
                                          "texto_rep": COLOR_REPARTIDOR}},
}
CAPA_INICIAL = "Mapa"


# Matemática de teselas (proyección Web Mercator, la de Google Maps / OpenStreetMap / Esri)
def _lon_a_x(lon, z):
    return (lon + 180.0) / 360.0 * (1 << z)


def _lat_a_y(lat, z):
    return (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * (1 << z)


def _tesela_a_latlon(x, y, z):
    """Esquina superior izquierda de la tesela (x, y) del nivel z -> (lat, lon)."""
    n = 1 << z
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2.0 * y / n))))
    return lat, lon


def rango_maximo(z):
    """Hasta qué rango de calles se escribe el nombre, según el zoom z = escala actual / escala inicial.
    Rango 1 = vías principales, 2 = secundarias, 3 = terciarias, 4 = el resto."""
    if z < 2:
        return 1
    if z < 5:
        return 2
    if z < 12:
        return 3
    return 4


def leer_etiqueta(e):
    """Devuelve (nombre, lat, lon, angulo, rango, largo) de una etiqueta del grafo.
    Acepta que venga como diccionario (claves nombre, lat, lon, angulo, rango, largo) o como
    lista/tupla con esos seis datos en ese orden."""
    if isinstance(e, dict):
        return e["nombre"], e["lat"], e["lon"], e["angulo"], e["rango"], e["largo"]
    nombre, lat, lon, angulo, rango, largo = e
    return nombre, lat, lon, angulo, rango, largo


class CanvasMapa(tk.Canvas):
    def __init__(self, parent, grafo, ancho=700, alto=600):
        super().__init__(parent, width=ancho, height=alto, bg=COLOR_FONDO,
                         highlightthickness=0)
        self.grafo = grafo

        # Funciones que pone la ventana principal (si siguen en None no pasa nada):
        #   al_clic(lat, lon)   -> se llama cuando el usuario hace clic en el mapa
        #   al_mover(lat, lon)  -> se llama cuando el mouse se mueve sobre el mapa
        self.al_clic = None
        self.al_mover = None

        # Lo que hay que dibujar encima del mapa base. Se guarda en listas porque al hacer
        # zoom se borra y se vuelve a dibujar (los círculos no deben agrandarse con el zoom)
        self._pedidos = []
        self._repartidores = []
        self._rutas = []              # lista de (puntos, color, ancho)

        # Conversión de coordenadas a píxeles (se calcula en reencuadrar):
        #   x = x0 + escala * (lon - oeste) * cos_lat      y = y0 + escala * (norte - lat)
        # El cos_lat corrige que un grado de longitud mide menos que uno de latitud
        lim = grafo.limites
        self._oeste, self._norte = lim["oeste"], lim["norte"]
        lat_media = (lim["norte"] + lim["sur"]) / 2
        self._cos_lat = math.cos(math.radians(lat_media))
        self._escala = 1.0            # píxeles por grado de latitud
        self._escala_inicial = 1.0    # la del encuadre inicial, para limitar el zoom
        self._x0 = 0.0
        self._y0 = 0.0
        self._listo = False           # True cuando el canvas ya tiene tamaño y se dibujó el mapa

        # Para distinguir "clic" de "arrastrar"
        self._press = None
        self._arrastro = False

        # Versión del grafo con la que se dibujaron las calles cerradas
        self._version_vista = grafo.version

        # Fondo de mapa: hilos de descarga, cachés y selector de capa
        self._iniciar_fondo()

        self.bind("<Configure>", self._al_cambiar_tamano)
        self.bind("<ButtonPress-1>", self._presionar)
        self.bind("<B1-Motion>", self._arrastrar)
        self.bind("<ButtonRelease-1>", self._soltar)
        self.bind("<Motion>", self._mover)
        self.bind("<MouseWheel>", self._rueda)          # Windows y macOS
        self.bind("<Button-4>", self._rueda)            # Linux: rueda hacia arriba
        self.bind("<Button-5>", self._rueda)            # Linux: rueda hacia abajo

        self.after(300, self._vigilar_cierres)

    # ------------------------------------------------------------------
    # Conversión coordenadas <-> píxeles
    # ------------------------------------------------------------------
    def convertir(self, lat, lon):
        """(lat, lon) -> (x, y) en coordenadas del canvas."""
        x = self._x0 + self._escala * (lon - self._oeste) * self._cos_lat
        y = self._y0 + self._escala * (self._norte - lat)
        return x, y

    def inverso(self, x, y):
        """(x, y) en coordenadas del canvas -> (lat, lon). Es el camino contrario de convertir."""
        lon = self._oeste + (x - self._x0) / (self._escala * self._cos_lat)
        lat = self._norte - (y - self._y0) / self._escala
        return lat, lon

    # ------------------------------------------------------------------
    # Encuadre y dibujo del mapa base
    # ------------------------------------------------------------------
    def reencuadrar(self):
        """Ajusta el zoom y la posición para que todo el mapa entre en la ventana."""
        ancho = self.winfo_width()
        alto = self.winfo_height()
        if ancho < 50 or alto < 50:      # el canvas todavía no tiene su tamaño real
            return
        lim = self.grafo.limites
        ancho_grados = (lim["este"] - lim["oeste"]) * self._cos_lat
        alto_grados = lim["norte"] - lim["sur"]
        # Se usa la misma escala en los dos ejes para no deformar el mapa
        self._escala = min((ancho - 2 * MARGEN) / ancho_grados,
                           (alto - 2 * MARGEN) / alto_grados)
        self._escala_inicial = self._escala
        # Se centra en lo que se ve ahora (canvasx(0) es la esquina visible si se desplazó)
        self._x0 = self.canvasx(0) + (ancho - self._escala * ancho_grados) / 2
        self._y0 = self.canvasy(0) + (alto - self._escala * alto_grados) / 2
        self._listo = True
        self._dibujar_todo()

    def _al_cambiar_tamano(self, evento):
        # La primera vez que el canvas tiene tamaño se dibuja el mapa; después se respeta
        # el zoom del usuario (para volver a encuadrar está el botón de la ventana)
        if not self._listo:
            self.reencuadrar()
        else:
            self._programar_fondo(150)          # el área nueva también necesita fondo

    def _dibujar_todo(self):
        self.delete("all")
        self._dibujar_calles()
        self._dibujar_etiquetas()
        self._dibujar_distritos()
        self.actualizar_cerradas()
        self._dibujar_dinamicos()
        self._actualizar_fondo()

    def _dibujar_calles(self):
        # Cada calle de doble sentido aparece dos veces en el grafo (ida y vuelta):
        # se dibuja una sola vez usando el par ordenado de esquinas como clave
        vistos = set()
        for u, lista in self.grafo.calles.items():
            xu, yu = self.convertir(*self.grafo.nodos[u])
            for v, _metros, _nombre, _id in lista:
                clave = (u, v) if u < v else (v, u)
                if clave in vistos:
                    continue
                vistos.add(clave)
                xv, yv = self.convertir(*self.grafo.nodos[v])
                self.create_line(xu, yu, xv, yv, fill=self._tema()["calle"], width=1,
                                 tags=("calle", "estatico"))

    def _dibujar_etiquetas(self):
        """Escribe el nombre de las calles. Cada etiqueta del grafo trae nombre, lat, lon, angulo
        (ya corregido para que el texto no salga de cabeza), rango (1 principal ... 4 el resto) y largo.
        Se muestran solo los rangos que corresponden al zoom actual y se saltan las etiquetas que
        se solaparían con una ya puesta."""
        etiquetas = getattr(self.grafo, "etiquetas", None)
        if not etiquetas or CAPAS[self._capa]["etiquetas_propias"]:
            return
        color = self._tema()["etiqueta"]
        maximo = rango_maximo(self._escala / self._escala_inicial)
        candidatas = [leer_etiqueta(e) for e in etiquetas]
        candidatas = [c for c in candidatas if c[4] <= maximo]
        # Primero las calles más importantes y, dentro de cada rango, las más largas: ganan el lugar
        candidatas.sort(key=lambda c: (c[4], -c[5]))

        ocupadas = set()               # celdas de la pantalla que ya tienen texto
        for nombre, lat, lon, angulo, _rango, _largo in candidatas:
            x, y = self.convertir(lat, lon)
            # Caja que ocupa el texto girado (rectángulo ancho x alto rotado, aproximado)
            ancho, alto = len(nombre) * ANCHO_LETRA, ALTO_TEXTO
            c, s = abs(math.cos(math.radians(angulo))), abs(math.sin(math.radians(angulo)))
            caja_x, caja_y = ancho * c + alto * s, ancho * s + alto * c
            celdas = [(i, j)
                      for i in range(int((x - caja_x / 2) // CELDA), int((x + caja_x / 2) // CELDA) + 1)
                      for j in range(int((y - caja_y / 2) // CELDA), int((y + caja_y / 2) // CELDA) + 1)]
            if any(celda in ocupadas for celda in celdas):
                continue               # se pisaría con otra etiqueta: no se dibuja
            ocupadas.update(celdas)
            try:
                self.create_text(x, y, text=nombre, angle=angulo, font=FUENTE_ETIQUETA,
                                 fill=color, tags=("etiqueta",))   # "angle" existe desde Tk 8.6
            except tk.TclError:
                self.create_text(x, y, text=nombre, font=FUENTE_ETIQUETA,
                                 fill=color, tags=("etiqueta",))   # Tk viejo: texto sin girar

    def _dibujar_distritos(self):
        # Nombre de cada distrito, para ubicarse en el mapa
        tema = self._tema()
        for nombre, lat, lon in self.grafo.distritos:
            x, y = self.convertir(lat, lon)
            if tema["sombra"]:
                self.create_text(x + 1, y + 1, text=nombre, fill=tema["sombra"],
                                 font=("TkDefaultFont", 10, "italic"),
                                 tags=("distrito", "estatico"))
            self.create_text(x, y, text=nombre, fill=tema["distrito"],
                             font=("TkDefaultFont", 10, "italic"),
                             tags=("distrito", "estatico"))

    # ------------------------------------------------------------------
    # Pedidos y repartidores
    # ------------------------------------------------------------------
    def dibujar_pedidos(self, pedidos):
        """Dibuja un círculo por pedido: rojo urgente, naranja normal, verde baja."""
        self._pedidos = list(pedidos)
        if self._listo:
            self._dibujar_dinamicos()

    def dibujar_repartidores(self, repartidores):
        """Dibuja un cuadrado morado por repartidor con su nombre."""
        self._repartidores = list(repartidores)
        if self._listo:
            self._dibujar_dinamicos()

    # ------------------------------------------------------------------
    # Rutas
    # ------------------------------------------------------------------
    def dibujar_ruta(self, puntos, color=COLOR_RUTA, ancho=3):
        """Dibuja una ruta como línea. `puntos` es una lista de (lat, lon).
        Las rutas se acumulan hasta llamar a limpiar_rutas()."""
        if len(puntos) < 2:
            return
        self._rutas.append((list(puntos), color, ancho))
        if self._listo:
            self._trazar_ruta(puntos, color, ancho)
            self._ordenar_capas()

    def limpiar_rutas(self):
        """Borra todas las rutas dibujadas (no toca pedidos ni calles cerradas)."""
        self._rutas = []
        self.delete("ruta")

    def _trazar_ruta(self, puntos, color, ancho):
        coordenadas = []
        for lat, lon in puntos:
            coordenadas.extend(self.convertir(lat, lon))
        self.create_line(*coordenadas, fill=color, width=ancho, arrow="last",
                         capstyle="round", joinstyle="round", tags=("ruta",))

    # ------------------------------------------------------------------
    # Calles cerradas (en rojo)
    # ------------------------------------------------------------------
    def dibujar_calle_cerrada(self, nombre=None, id_arista=None):
        """Pinta de rojo todos los tramos de la calle `nombre`, o el tramo con ese id."""
        if nombre is None and id_arista is None:
            return
        self._pintar_cerradas(lambda n, i: n == nombre or i == id_arista)
        self._ordenar_capas()

    def actualizar_cerradas(self):
        """Borra y vuelve a pintar todas las calles que el grafo tiene cerradas ahora."""
        self.delete("cerrada")
        g = self.grafo
        if g.cerradas_nombre or g.cerradas_id:
            self._pintar_cerradas(
                lambda n, i: n in g.cerradas_nombre or i in g.cerradas_id)
        self._version_vista = g.version
        self._ordenar_capas()

    def _pintar_cerradas(self, criterio):
        # Recorre los tramos del grafo y pinta los que cumplen `criterio(nombre, id)`
        vistos = set()
        for u, lista in self.grafo.calles.items():
            for v, _metros, nombre, id_ in lista:
                if not criterio(nombre, id_):
                    continue
                clave = (u, v) if u < v else (v, u)
                if clave in vistos:
                    continue
                vistos.add(clave)
                xu, yu = self.convertir(*self.grafo.nodos[u])
                xv, yv = self.convertir(*self.grafo.nodos[v])
                self.create_line(xu, yu, xv, yv, fill=COLOR_CERRADA, width=3,
                                 tags=("cerrada", "estatico"))

    def _vigilar_cierres(self):
        # La pestaña Rutas (Persona 1) cierra calles directamente en el grafo, sin avisar al
        # canvas. Cada 300 ms se mira la versión del grafo y, si cambió, se repintan las rojas
        if self._listo and self.grafo.version != self._version_vista:
            self.actualizar_cerradas()
        self.after(300, self._vigilar_cierres)

    # ------------------------------------------------------------------
    # Dibujo de lo que va encima del mapa base
    # ------------------------------------------------------------------
    def _dibujar_dinamicos(self):
        self.delete("ruta", "pedido", "repartidor")
        tema = self._tema()
        for puntos, color, ancho in self._rutas:
            self._trazar_ruta(puntos, color, ancho)
        for p in self._pedidos:
            x, y = self.convertir(p.lat, p.lon)
            color = COLORES_PRIORIDAD.get(p.prioridad, "black")
            self.create_oval(x - RADIO_PEDIDO, y - RADIO_PEDIDO,
                             x + RADIO_PEDIDO, y + RADIO_PEDIDO,
                             fill=color, outline="black", tags=("pedido",))
            self.create_text(x + RADIO_PEDIDO + 2, y - RADIO_PEDIDO - 2, text=str(p.id),
                             anchor="sw", font=("TkDefaultFont", 8, "bold"),
                             fill=tema["texto_pedido"], tags=("pedido",))
        for r in self._repartidores:
            x, y = self.convertir(r.lat, r.lon)
            self.create_rectangle(x - LADO_REPARTIDOR, y - LADO_REPARTIDOR,
                                  x + LADO_REPARTIDOR, y + LADO_REPARTIDOR,
                                  fill=COLOR_REPARTIDOR, outline="white",
                                  tags=("repartidor",))
            self.create_text(x, y + LADO_REPARTIDOR + 2, text=r.nombre, anchor="n",
                             fill=tema["texto_rep"], font=("TkDefaultFont", 8, "bold"),
                             tags=("repartidor",))
        self._ordenar_capas()

    def _ordenar_capas(self):
        # De abajo hacia arriba: calles, cerradas, nombres de calle, nombres de distrito, rutas, pedidos, repartidores
        for etiqueta in ("calle", "cerrada", "etiqueta", "distrito", "ruta", "pedido", "repartidor"):
            self.tag_raise(etiqueta)

    # ------------------------------------------------------------------
    # Mouse: zoom con la rueda, arrastrar para mover, clic para elegir un punto
    # ------------------------------------------------------------------
    def _rueda(self, evento):
        # Linux manda Button-4 (acercar) y Button-5 (alejar); Windows/macOS mandan delta
        if evento.num == 4 or getattr(evento, "delta", 0) > 0:
            factor = FACTOR_ZOOM
        else:
            factor = 1 / FACTOR_ZOOM
        nueva = self._escala * factor
        if not (self._escala_inicial * ZOOM_MINIMO <= nueva <= self._escala_inicial * ZOOM_MAXIMO):
            return
        # El zoom se hace alrededor del puntero para que el punto bajo el mouse no se mueva
        cx, cy = self.canvasx(evento.x), self.canvasy(evento.y)
        self.scale("estatico", cx, cy, factor, factor)  # calles, cerradas y distritos se escalan en bloque
        self._x0 = cx + (self._x0 - cx) * factor
        self._y0 = cy + (self._y0 - cy) * factor
        self._escala = nueva
        # Los nombres de calle NO llevan la etiqueta "estatico": scale() solo los movería, pero con otro
        # zoom deben verse otros rangos. Por eso se borran y se vuelven a dibujar
        self.delete("etiqueta")
        self._dibujar_etiquetas()
        self._ordenar_capas()
        self._dibujar_dinamicos()                   # pedidos y rutas se redibujan para no deformarse
        self._programar_fondo(50)                   # el fondo se re-pide al nivel de zoom que toque

    def _presionar(self, evento):
        self._press = (evento.x, evento.y)
        self._arrastro = False
        self.scan_mark(evento.x, evento.y)

    def _arrastrar(self, evento):
        if self._press is None:
            return
        # Menos de 4 píxeles de movimiento se considera clic, no arrastre
        if not self._arrastro and abs(evento.x - self._press[0]) + abs(evento.y - self._press[1]) < 4:
            return
        self._arrastro = True
        self.scan_dragto(evento.x, evento.y, gain=1)
        self._programar_fondo(150, reiniciar=False)   # cada ~150 ms mientras se arrastra

    def _soltar(self, evento):
        if self._arrastro:
            self._programar_fondo(30)
        if self._press is not None and not self._arrastro and self.al_clic is not None:
            lat, lon = self.inverso(self.canvasx(evento.x), self.canvasy(evento.y))
            self.al_clic(lat, lon)
        self._press = None

    def _mover(self, evento):
        if self.al_mover is not None and self._listo:
            lat, lon = self.inverso(self.canvasx(evento.x), self.canvasy(evento.y))
            self.al_mover(lat, lon)

    # ------------------------------------------------------------------
    # Fondo de mapa: teselas de Esri (Mapa / Satélite / Híbrido)
    # ------------------------------------------------------------------
    def _tema(self):
        return CAPAS[self._capa]["tema"]

    def _iniciar_fondo(self):
        self._capa = "Sin fondo"
        self._fondo_after = None              # id del after pendiente (para no duplicar redibujos)
        self._fotos = []                      # referencias a las PhotoImage (si no, Tk las borra)
        self._memoria = OrderedDict()         # caché en RAM: (capa, z, x, y) -> imagen PIL
        self._pendientes = set()              # teselas ya pedidas que aún no llegan
        self._fallidos = {}                   # clave -> hora del último fallo (se reintenta a los 60 s)
        self._sin_conexion = False
        self._lock = threading.Lock()
        self._jobs = queue.LifoQueue()        # LIFO: lo último que se ve en pantalla se descarga primero
        self._resultados = queue.Queue()      # los hilos avisan aquí; solo el hilo de Tk toca widgets
        self._var_fondo = tk.StringVar()
        if not HAY_PIL:
            return
        self._capa = CAPA_INICIAL
        self.configure(bg=self._tema()["fondo"])
        self._crear_selector()
        for _ in range(HILOS_TESELAS):
            threading.Thread(target=self._trabajador, daemon=True).start()
        self.after(150, self._revisar_teselas)

    def _crear_selector(self):
        # place() lo deja fijo en la esquina aunque el mapa se desplace
        panel = tk.Frame(self, bg="white", bd=1, relief="solid")
        panel.place(relx=1.0, x=-10, y=10, anchor="ne")
        fila = tk.Frame(panel, bg="white")
        fila.pack(padx=3, pady=3)
        self._var_capa = tk.StringVar(value=self._capa)
        for nombre in CAPAS:
            tk.Radiobutton(fila, text=nombre, value=nombre, variable=self._var_capa,
                           indicatoron=False, bg="white", selectcolor="#cfe3ff",
                           padx=8, pady=2, bd=1, command=self._cambiar_capa).pack(side="left", padx=1)
        tk.Label(panel, textvariable=self._var_fondo, bg="white", fg="#666666",
                 font=("TkDefaultFont", 7)).pack(anchor="e", padx=4)

    def _cambiar_capa(self):
        self._capa = self._var_capa.get()
        self.configure(bg=self._tema()["fondo"])
        if not self._listo:
            return
        # Calles, nombres y distritos cambian de color (o de visibilidad) según la capa
        self.delete("calle", "etiqueta", "distrito")
        self._dibujar_calles()
        self._dibujar_etiquetas()
        self._dibujar_distritos()
        self._dibujar_dinamicos()             # también reordena las capas
        self._programar_fondo(0)

    def _programar_fondo(self, espera=50, reiniciar=True):
        """Agenda un redibujo del fondo. reiniciar=False: si ya hay uno agendado, no hace nada."""
        if not HAY_PIL:
            return
        if self._fondo_after is not None:
            if not reiniciar:
                return
            self.after_cancel(self._fondo_after)
        self._fondo_after = self.after(espera, self._actualizar_fondo)

    def _actualizar_fondo(self):
        self._fondo_after = None
        self.delete("fondo")
        self._fotos = []
        cfg = CAPAS[self._capa]
        if not HAY_PIL or not self._listo or not cfg["urls"]:
            self._var_fondo.set("")
            return
        # Zona visible (más un margen) en coordenadas del canvas y en lat/lon
        x0 = self.canvasx(0) - MARGEN_FONDO
        y0 = self.canvasy(0) - MARGEN_FONDO
        x1 = self.canvasx(self.winfo_width()) + MARGEN_FONDO
        y1 = self.canvasy(self.winfo_height()) + MARGEN_FONDO
        lat_n, lon_o = self.inverso(x0, y0)
        lat_s, lon_e = self.inverso(x1, y1)
        # Nivel de teselas para que cada una mida ~256 px en pantalla
        px_por_grado = self._escala * self._cos_lat
        z = max(Z_MIN, min(Z_MAX, round(math.log2(px_por_grado * 360.0 / TESELA))))
        n = 1 << z
        tx0 = max(0, math.floor(_lon_a_x(lon_o, z)))
        tx1 = min(n - 1, math.floor(_lon_a_x(lon_e, z)))
        ty0 = max(0, math.floor(_lat_a_y(min(lat_n, 85.0), z)))
        ty1 = min(n - 1, math.floor(_lat_a_y(max(lat_s, -85.0), z)))
        if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) > MAX_TESELAS:
            return
        clip = (round(x0), round(y0), round(x1), round(y1))
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                self._pintar_tesela((self._capa, z, tx, ty), clip)
        self.tag_lower("fondo")               # el fondo siempre queda debajo de todo
        self._actualizar_estado_fondo()

    def _pintar_tesela(self, clave, clip):
        capa, z, tx, ty = clave
        # Se ubica por sus dos esquinas con el mismo convertir() que usan las calles: así el fondo
        # y el grafo coinciden. Se redondea igual en tesela vecina, por eso no quedan rendijas
        lat_a, lon_a = _tesela_a_latlon(tx, ty, z)
        lat_b, lon_b = _tesela_a_latlon(tx + 1, ty + 1, z)
        xa, ya = (round(v) for v in self.convertir(lat_a, lon_a))
        xb, yb = (round(v) for v in self.convertir(lat_b, lon_b))

        img = self._de_memoria(clave)
        if img is not None:
            self._poner_imagen(img, (0, 0, img.width, img.height), (xa, ya, xb, yb), clip)
            return
        self._pedir_tesela(clave)
        # Mientras llega, se muestra la tesela del nivel anterior ampliada (borrosa pero útil)
        for k in range(1, 4):
            if z - k < 0:
                break
            padre = self._de_memoria((capa, z - k, tx >> k, ty >> k))
            if padre is not None:
                lado = padre.width / (1 << k)
                izq = (tx - ((tx >> k) << k)) * lado
                arr = (ty - ((ty >> k) << k)) * lado
                self._poner_imagen(padre, (izq, arr, izq + lado, arr + lado), (xa, ya, xb, yb), clip)
                return

    def _poner_imagen(self, img, caja, destino, clip):
        """Pega la parte `caja` de `img` en el rectángulo `destino` del canvas, recortando a `clip`
        (así, aunque el zoom sea enorme, solo se procesa lo que se ve)."""
        xa, ya, xb, yb = destino
        ancho, alto = xb - xa, yb - ya
        if ancho < 1 or alto < 1:
            return
        ix0, iy0 = max(xa, clip[0]), max(ya, clip[1])
        ix1, iy1 = min(xb, clip[2]), min(yb, clip[3])
        if ix0 >= ix1 or iy0 >= iy1:
            return
        izq, arr, der, aba = caja
        sw, sh = der - izq, aba - arr
        recorte = (izq + (ix0 - xa) / ancho * sw, arr + (iy0 - ya) / alto * sh,
                   izq + (ix1 - xa) / ancho * sw, arr + (iy1 - ya) / alto * sh)
        remuestreo = getattr(Image, "Resampling", Image).BILINEAR
        foto = ImageTk.PhotoImage(img.resize((ix1 - ix0, iy1 - iy0), remuestreo, box=recorte))
        self._fotos.append(foto)
        self.create_image(ix0, iy0, image=foto, anchor="nw", tags=("fondo",))

    # --- caché en memoria (compartida con los hilos, por eso el candado) ---
    def _de_memoria(self, clave):
        with self._lock:
            img = self._memoria.get(clave)
            if img is not None:
                self._memoria.move_to_end(clave)
            return img

    def _guardar_memoria(self, clave, img):
        with self._lock:
            self._memoria[clave] = img
            self._memoria.move_to_end(clave)
            while len(self._memoria) > MAX_MEMORIA:
                self._memoria.popitem(last=False)

    # --- hilos de descarga ---
    def _pedir_tesela(self, clave):
        with self._lock:
            if clave in self._pendientes:
                return
            if time.time() - self._fallidos.get(clave, 0) < 60:
                return
            self._pendientes.add(clave)
        self._jobs.put(clave)

    def _trabajador(self):
        # Corre en un hilo aparte: NO toca widgets, solo deja el resultado en las colas
        while True:
            clave = self._jobs.get()
            try:
                if clave[0] != self._capa:    # el usuario ya cambió de capa: no vale la pena
                    continue
                img = self._leer_disco(clave) or self._descargar(clave)
                if img is not None:
                    self._guardar_memoria(clave, img)
                    self._resultados.put(clave)
            except Exception:
                pass
            finally:
                with self._lock:
                    self._pendientes.discard(clave)

    def _ruta_cache(self, clave):
        capa, z, x, y = clave
        return os.path.join(DIR_CACHE, capa, str(z), str(x), f"{y}.{CAPAS[capa]['ext']}")

    def _leer_disco(self, clave):
        ruta = self._ruta_cache(clave)
        if not os.path.exists(ruta):
            return None
        try:
            return Image.open(ruta).convert("RGB")
        except Exception:                     # archivo dañado: se borra y se vuelve a descargar
            try:
                os.remove(ruta)
            except OSError:
                pass
            return None

    def _descargar(self, clave):
        capa, z, x, y = clave
        cfg = CAPAS[capa]
        base = None
        try:
            for i, plantilla in enumerate(cfg["urls"]):
                pedido = urllib.request.Request(plantilla.format(z=z, x=x, y=y),
                                                headers={"User-Agent": USER_AGENT})
                try:
                    with urllib.request.urlopen(pedido, timeout=10) as r:
                        capa_img = Image.open(io.BytesIO(r.read())).convert("RGBA")
                except Exception:
                    if i == 0:
                        raise                 # sin la base no hay tesela; las capas extra son opcionales
                    continue
                if base is None:
                    base = capa_img
                else:
                    if capa_img.size != base.size:
                        capa_img = capa_img.resize(base.size)
                    base = Image.alpha_composite(base, capa_img)
            img = base.convert("RGB")
            self._sin_conexion = False
        except urllib.error.HTTPError:        # el servidor respondió pero no tiene esa tesela
            with self._lock:
                self._fallidos[clave] = time.time()
            return None
        except Exception:                     # sin internet, tiempo agotado, etc.
            self._sin_conexion = True
            with self._lock:
                self._fallidos[clave] = time.time()
            return None
        try:                                  # guardar en disco (si falla, no pasa nada)
            ruta = self._ruta_cache(clave)
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            tmp = ruta + ".tmp"
            if cfg["ext"] == "png":
                img.save(tmp, format="PNG")
            else:
                img.save(tmp, format="JPEG", quality=88)
            os.replace(tmp, ruta)
        except Exception:
            pass
        return img

    def _revisar_teselas(self):
        # Cada 150 ms, en el hilo de Tk: si llegaron teselas nuevas, se redibuja el fondo
        llego = False
        try:
            while True:
                if self._resultados.get_nowait()[0] == self._capa:
                    llego = True
        except queue.Empty:
            pass
        if llego:
            self._programar_fondo(30, reiniciar=False)
        else:
            self._actualizar_estado_fondo()
        self.after(150, self._revisar_teselas)

    def _actualizar_estado_fondo(self):
        with self._lock:
            pendientes = len(self._pendientes)
        if pendientes:
            texto = f"Cargando fondo ({pendientes})..."
        elif self._sin_conexion:
            texto = "Sin conexión: no se pudo cargar el fondo"
        else:
            texto = CAPAS[self._capa]["credito"]
        if self._var_fondo.get() != texto:
            self._var_fondo.set(texto)