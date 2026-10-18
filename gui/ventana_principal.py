"Daniel - gui/ventana_principal.py"
# gui/ventana_principal.py
# Persona 4 (Daniel): ventana principal de la aplicación.
#
# Qué hace:
#   - Clase App (tk.Tk): reparte la ventana en dos partes, a la izquierda un ttk.Notebook con
#     las pestañas de todos y a la derecha el CanvasMapa.
#   - Guarda lo que comparten todas las pestañas: app.grafo, app.pedidos, app.repartidores y
#     app.canvas (los mismos nombres que las pestañas de los demás ya esperan).
#   - Reenvía los clics del mapa a la pestaña que los pida (al_hacer_clic de la pestaña Rutas)
#     y, si está abierta la pestaña Pedidos, rellena su latitud y longitud.
#   - ejecutar_en_hilo(): ayuda para correr algoritmos pesados en un threading.Thread sin
#     congelar la ventana. El resultado vuelve por una queue.Queue y se recoge con after(100, ...).
#   - Menú Archivo: cargar pedidos desde un JSON o generar pedidos aleatorios.

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from gui.canvas_mapa import CanvasMapa
from gui.pestana_pedidos import PestanaPedidos
from gui.pestana_greedy import PestanaGreedy
from gui.pestana_zonas import PestanaZonas
from gui.pestana_mochila import PestanaMochila
# La Persona 1 puede haber guardado su archivo como "pestaña_rutas.py" (con ñ) o "pestana_rutas.py"
try:
    from gui.pestaña_rutas import PestañaRutas
except ImportError:
    from gui.pestana_rutas import PestañaRutas

from modelos import cargar_pedidos
from pruebas.benchmark import generar_pedidos


class App(tk.Tk):
    def __init__(self, grafo, pedidos, repartidores):
        super().__init__()
        self.title("Sistema de Gestión de Rutas Óptimas en Cusco")
        self.geometry("1500x860")
        self.minsize(1100, 650)
        try:
            ttk.Style(self).theme_use("clam")      # un tema más limpio que el de defecto
        except tk.TclError:
            pass

        # Datos compartidos: las pestañas leen y modifican estas MISMAS listas
        self.grafo = grafo
        self.pedidos = pedidos
        self.repartidores = repartidores

        # Para los hilos: la cola donde dejan su resultado y cuántos siguen corriendo
        self._cola = queue.Queue()
        self._hilos_activos = 0

        self._crear_menu()
        self._crear_barra_superior()
        self._crear_cuerpo()
        self._crear_barra_estado()

        # Se dibujan los repartidores y pedidos iniciales en el mapa
        self.canvas.dibujar_repartidores(self.repartidores)
        self.canvas.dibujar_pedidos(self.pedidos)

    # ------------------------------------------------------------------
    # Construcción de la ventana
    # ------------------------------------------------------------------
    def _crear_menu(self):
        barra = tk.Menu(self)
        archivo = tk.Menu(barra, tearoff=False)
        archivo.add_command(label="Cargar pedidos (JSON)...", command=self._cargar_json)
        archivo.add_command(label="Generar pedidos aleatorios...", command=self._generar_aleatorios)
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self.destroy)
        barra.add_cascade(label="Archivo", menu=archivo)
        self.config(menu=barra)

    def _crear_barra_superior(self):
        barra = ttk.Frame(self, padding=(8, 4))
        barra.pack(fill="x")
        ttk.Label(barra, text="Distancias en línea recta (Haversine).  "
                              "Mapa: rueda = zoom, arrastrar = mover, clic = elegir un punto.",
                  foreground="#666666").pack(side="left")
        ttk.Button(barra, text="Reencuadrar mapa",
                   command=lambda: self.canvas.reencuadrar()).pack(side="right")

    def _crear_cuerpo(self):
        # PanedWindow: el usuario puede arrastrar la barra del medio para dar más espacio al mapa
        cuerpo = ttk.PanedWindow(self, orient="horizontal")
        cuerpo.pack(fill="both", expand=True)
        # Posición inicial de la barra del medio: ~780 px para las pestañas y el resto para el mapa
        self.after(100, lambda: cuerpo.sashpos(0, 780))
        izquierda = ttk.Frame(cuerpo)
        derecha = ttk.Frame(cuerpo)
        cuerpo.add(izquierda, weight=1)
        cuerpo.add(derecha, weight=2)

        # El canvas se crea ANTES que las pestañas porque ellas lo usan como app.canvas
        self.canvas = CanvasMapa(derecha, self.grafo)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.al_clic = self._clic_en_mapa
        self.canvas.al_mover = self._mouse_en_mapa

        # Cuaderno con una pestaña por técnica algorítmica
        self.cuaderno = ttk.Notebook(izquierda)
        self.cuaderno.pack(fill="both", expand=True)
        self.pestanas = {
            "Pedidos": PestanaPedidos(self.cuaderno, self),
            "Greedy": PestanaGreedy(self.cuaderno, self),
            "Zonas": PestanaZonas(self.cuaderno, self),
            "Mochila": PestanaMochila(self.cuaderno, self),
            "Rutas": PestañaRutas(self.cuaderno, self),
        }
        for titulo, pestana in self.pestanas.items():
            self.cuaderno.add(pestana, text=titulo)

    def _crear_barra_estado(self):
        barra = ttk.Frame(self, padding=(8, 2))
        barra.pack(fill="x", side="bottom")
        self.var_estado = tk.StringVar(value="Listo. Rueda del mouse = zoom, arrastrar = mover el mapa.")
        self.var_coordenadas = tk.StringVar(value="")
        ttk.Label(barra, textvariable=self.var_estado).pack(side="left")
        ttk.Label(barra, textvariable=self.var_coordenadas).pack(side="right")

    # ------------------------------------------------------------------
    # Eventos del mapa
    # ------------------------------------------------------------------
    def _clic_en_mapa(self, lat, lon):
        # 1) Si alguna pestaña pidió un clic (la pestaña Rutas con "Elegir en el mapa"), se lo queda
        for pestana in self.pestanas.values():
            usar = getattr(pestana, "al_hacer_clic", None)
            if usar is not None and usar(lat, lon):
                return
        # 2) Si está abierta la pestaña Pedidos, se rellenan latitud y longitud del formulario
        actual = self.cuaderno.nametowidget(self.cuaderno.select())
        if hasattr(actual, "var_lat") and hasattr(actual, "var_lon"):
            actual.var_lat.set(f"{lat:.6f}")
            actual.var_lon.set(f"{lon:.6f}")
            self.var_estado.set("Coordenadas copiadas al formulario de Pedidos.")
        else:
            self.var_estado.set(f"Punto elegido: {lat:.6f}, {lon:.6f}")

    def _mouse_en_mapa(self, lat, lon):
        self.var_coordenadas.set(f"lat {lat:.5f}   lon {lon:.5f}   "
                                 f"sector: {self.grafo.sector_de(lat, lon)}")

    # ------------------------------------------------------------------
    # Hilos: para que un algoritmo pesado no congele la ventana
    # ------------------------------------------------------------------
    def ejecutar_en_hilo(self, trabajo, al_terminar, al_error=None):
        """Corre `trabajo()` (función sin argumentos) en un hilo aparte.
        Al terminar llama a `al_terminar(resultado)` en el hilo de la ventana, que es el único
        que puede tocar widgets de tkinter. Si `trabajo` falla se llama a `al_error(excepcion)`
        o, si no se dio, se muestra un messagebox.

        Ejemplo (para cualquier pestaña):
            self.app.ejecutar_en_hilo(lambda: vecino_mas_cercano(rep, pedidos), self._mostrar)
        """
        def correr():
            try:
                self._cola.put(("ok", trabajo(), al_terminar))
            except Exception as error:      # el hilo no puede abrir mensajes: se manda a la cola
                self._cola.put(("error", error, al_error))

        self._hilos_activos += 1
        self.config(cursor="watch")
        self.var_estado.set("Calculando...")
        threading.Thread(target=correr, daemon=True).start()
        self.after(100, self._revisar_cola)

    def _revisar_cola(self):
        # Cada 100 ms mira si algún hilo dejó su resultado. get_nowait no espera: si la cola
        # está vacía lanza queue.Empty y la ventana sigue libre
        try:
            while True:
                tipo, dato, funcion = self._cola.get_nowait()
                self._hilos_activos -= 1
                if tipo == "ok":
                    funcion(dato)
                elif funcion is not None:
                    funcion(dato)
                else:
                    messagebox.showerror("Error", str(dato))
        except queue.Empty:
            pass
        if self._hilos_activos > 0:
            self.after(100, self._revisar_cola)
        else:
            self.config(cursor="")
            if self.var_estado.get() == "Calculando...":    # no pisar el mensaje que dejó al_terminar
                self.var_estado.set("Listo.")

    # ------------------------------------------------------------------
    # Menú Archivo
    # ------------------------------------------------------------------
    def _reemplazar_pedidos(self, nuevos):
        # [:] cambia el contenido sin crear otra lista: las pestañas siguen apuntando a la misma
        self.pedidos[:] = nuevos
        self.canvas.dibujar_pedidos(self.pedidos)
        tabla = self.pestanas["Pedidos"]
        tabla.mostrar(self.pedidos)

    def _cargar_json(self):
        ruta = filedialog.askopenfilename(title="Pedidos (JSON)",
                                          filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            self._reemplazar_pedidos(cargar_pedidos(ruta))
        except Exception as error:
            messagebox.showerror("No se pudo cargar", f"El archivo no tiene el formato esperado.\n{error}")
            return
        self.var_estado.set(f"{len(self.pedidos)} pedidos cargados.")

    def _generar_aleatorios(self):
        n = simpledialog.askinteger("Pedidos aleatorios", "¿Cuántos pedidos?",
                                    initialvalue=30, minvalue=1, maxvalue=2000, parent=self)
        if n is None:
            return
        self._reemplazar_pedidos(generar_pedidos(n))
        self.var_estado.set(f"{n} pedidos aleatorios generados.")
