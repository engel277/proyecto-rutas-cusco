"Daniel - gui/canvas_mapa.py"
# gui/canvas_mapa.py
# Persona 4 (JC): CanvasMapa, el mapa de Cusco dibujado sobre un tk.Canvas.
#
# Qué hace:
#   - Dibuja todas las calles del grafo (mapa base) y los nombres de los distritos.
#   - Dibuja pedidos (color según prioridad), repartidores y rutas (líneas de colores).
#   - Dibuja en rojo las calles cerradas.
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
# cerradas_nombre, cerradas_id y version.

import math
import tkinter as tk

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
RADIO_PEDIDO = 6
LADO_REPARTIDOR = 7
MARGEN = 20                       # píxeles libres alrededor del mapa al encuadrar
FACTOR_ZOOM = 1.25
ZOOM_MAXIMO = 80                  # veces el zoom inicial
ZOOM_MINIMO = 0.4


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

    def _dibujar_todo(self):
        self.delete("all")
        self._dibujar_calles()
        self._dibujar_distritos()
        self.actualizar_cerradas()
        self._dibujar_dinamicos()

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
                self.create_line(xu, yu, xv, yv, fill=COLOR_CALLE, width=1,
                                 tags=("calle", "estatico"))

    def _dibujar_distritos(self):
        # Nombre de cada distrito, para ubicarse en el mapa
        for nombre, lat, lon in self.grafo.distritos:
            x, y = self.convertir(lat, lon)
            self.create_text(x, y, text=nombre, fill=COLOR_DISTRITO,
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
                             tags=("pedido",))
        for r in self._repartidores:
            x, y = self.convertir(r.lat, r.lon)
            self.create_rectangle(x - LADO_REPARTIDOR, y - LADO_REPARTIDOR,
                                  x + LADO_REPARTIDOR, y + LADO_REPARTIDOR,
                                  fill=COLOR_REPARTIDOR, outline="white",
                                  tags=("repartidor",))
            self.create_text(x, y + LADO_REPARTIDOR + 2, text=r.nombre, anchor="n",
                             fill=COLOR_REPARTIDOR, font=("TkDefaultFont", 8, "bold"),
                             tags=("repartidor",))
        self._ordenar_capas()

    def _ordenar_capas(self):
        # De abajo hacia arriba: calles, cerradas, nombres de distrito, rutas, pedidos, repartidores
        for etiqueta in ("calle", "cerrada", "distrito", "ruta", "pedido", "repartidor"):
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
        self._dibujar_dinamicos()                   # pedidos y rutas se redibujan para no deformarse

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

    def _soltar(self, evento):
        if self._press is not None and not self._arrastro and self.al_clic is not None:
            lat, lon = self.inverso(self.canvasx(evento.x), self.canvasy(evento.y))
            self.al_clic(lat, lon)
        self._press = None

    def _mover(self, evento):
        if self.al_mover is not None and self._listo:
            lat, lon = self.inverso(self.canvasx(evento.x), self.canvasy(evento.y))
            self.al_mover(lat, lon)
