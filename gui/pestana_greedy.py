# gui/pestana_greedy.py
# Pestaña "Greedy" (enfoque voraz). Tiene dos partes:
#   1) Vecino más cercano: el repartidor siempre visita el pedido más próximo que le quepa.
#   2) Pedido urgente: se asigna al repartidor más cercano que tenga capacidad para llevarlo.
#
# Lo que espera del objeto `app` (lo entrega ventana_principal.py):
#     app.pedidos       -> lista de Pedido
#     app.repartidores  -> lista de Repartidor
#     app.canvas        -> CanvasMapa con limpiar_rutas() y dibujar_ruta(puntos, color)
#     app.grafo         -> Grafo (para dibujar el recorrido por las calles reales)
#     app.ejecutar_en_hilo(trabajo, al_terminar, al_error)   (opcional: evita congelar la ventana)

import tkinter as tk
from tkinter import ttk, messagebox

from algoritmos.greedy import vecino_mas_cercano, asignar_urgente, distancia
from mapa.recorridos import recorrido_por_calles

COLOR_URGENTE = "#d62728"
NOMBRE_PRIORIDAD = {1: "urgente", 2: "normal", 3: "baja"}


class PestanaGreedy(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._repartidores = []     # copia de la lista que muestra el combo de repartidores
        self._pedidos = []          # copia de la lista que muestra el combo de pedidos urgentes

        # --- Barra superior: repartidor + botón Ejecutar
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=8, pady=8)
        ttk.Label(barra, text="Repartidor:").pack(side="left")
        self.var_repartidor = tk.StringVar()
        self.combo = ttk.Combobox(barra, textvariable=self.var_repartidor,
                                  state="readonly", width=38)
        self.combo.pack(side="left", padx=6)
        self.boton = ttk.Button(barra, text="Ejecutar", command=self._ejecutar)
        self.boton.pack(side="left")

        # --- Resultados
        self.var_total = tk.StringVar(value="Recorrido por calles: -")
        self.var_recta = tk.StringVar(value="")
        self.var_carga = tk.StringVar(value="")
        self.var_omitidos = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.var_total,
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=8)
        ttk.Label(self, textvariable=self.var_recta).pack(anchor="w", padx=8)
        ttk.Label(self, textvariable=self.var_carga).pack(anchor="w", padx=8)
        ttk.Label(self, textvariable=self.var_omitidos, foreground="#b34700").pack(
            anchor="w", padx=8, pady=(0, 6))

        # --- Asignar un pedido urgente (abajo, para que la tabla use el resto del espacio)
        urgente = ttk.LabelFrame(
            self, text="Asignar pedido urgente (repartidor más cercano con capacidad)", padding=6)
        urgente.pack(fill="x", side="bottom", padx=8, pady=(0, 8))
        fila = ttk.Frame(urgente)
        fila.pack(fill="x")
        ttk.Label(fila, text="Pedido:").pack(side="left")
        self.var_pedido = tk.StringVar()
        self.combo_pedido = ttk.Combobox(fila, textvariable=self.var_pedido,
                                         state="readonly", width=42)
        self.combo_pedido.pack(side="left", padx=6)
        self.boton_urgente = ttk.Button(fila, text="Asignar", command=self._asignar_urgente)
        self.boton_urgente.pack(side="left")
        self.var_urgente = tk.StringVar(value="")
        ttk.Label(urgente, textvariable=self.var_urgente, wraplength=520).pack(
            anchor="w", pady=(6, 0))

        # --- Tabla con el orden de visita
        columnas = ("orden", "id", "cliente", "sector", "peso", "tramo")
        titulos = ("#", "ID", "Cliente", "Sector", "Peso (kg)", "Por calles (m)")
        anchos = (40, 40, 190, 110, 80, 100)
        self.tabla = ttk.Treeview(self, columns=columnas, show="headings", height=10)
        for col, titulo, ancho in zip(columnas, titulos, anchos):
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, width=ancho, anchor="center")
        self.tabla.column("cliente", anchor="w")
        self.tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Cada vez que la pestaña se muestra, se refrescan las listas
        self.bind("<Map>", lambda e: self._cargar_listas())
        self._cargar_listas()

    # ------------------------------------------------------------------
    def _cargar_listas(self):
        self._repartidores = list(getattr(self.app, "repartidores", []))
        textos = [f"{r.id} - {r.nombre} (capacidad {r.capacidad:g} kg)"
                  for r in self._repartidores]
        self.combo["values"] = textos
        if textos and self.var_repartidor.get() not in textos:
            self.combo.current(0)

        # Pedidos: primero los urgentes (prioridad 1), que son los que más se asignan así
        pedidos = list(getattr(self.app, "pedidos", []))
        self._pedidos = [p for p in pedidos if p.prioridad == 1] + \
                        [p for p in pedidos if p.prioridad != 1]
        textos = [f"#{p.id} {p.cliente} ({NOMBRE_PRIORIDAD.get(p.prioridad, p.prioridad)}, "
                  f"{p.peso:g} kg)" for p in self._pedidos]
        self.combo_pedido["values"] = textos
        if textos and self.var_pedido.get() not in textos:
            self.combo_pedido.current(0)

    def _correr(self, boton, trabajo, al_terminar):
        """Ejecuta `trabajo` en un hilo si la ventana lo permite (calcular las calles puede tardar)."""
        def terminado(resultado):
            boton.state(["!disabled"])
            al_terminar(resultado)

        def fallo(error):
            boton.state(["!disabled"])
            messagebox.showerror("Error", str(error))

        boton.state(["disabled"])
        en_hilo = getattr(self.app, "ejecutar_en_hilo", None)
        if en_hilo is None:
            try:
                terminado(trabajo())
            except Exception as error:
                fallo(error)
        else:
            en_hilo(trabajo, terminado, fallo)

    # ------------------------------------------------------------------
    # Vecino más cercano
    # ------------------------------------------------------------------
    def _ejecutar(self):
        indice = self.combo.current()
        if indice < 0:
            messagebox.showwarning("Falta repartidor", "Elige un repartidor.")
            return
        if len(self.app.pedidos) == 0:
            messagebox.showwarning("Sin pedidos", "No hay pedidos cargados.")
            return

        repartidor = self._repartidores[indice]
        pedidos = list(self.app.pedidos)
        grafo = getattr(self.app, "grafo", None)

        def trabajo():
            # El algoritmo decide el orden (con distancia recta); luego se calcula por dónde
            # pasaría el repartidor por las calles reales
            ruta, metros = vecino_mas_cercano(repartidor, pedidos)
            return ruta, metros, recorrido_por_calles(grafo, [repartidor] + ruta)

        def terminado(resultado):
            ruta, metros, recorrido = resultado
            self._mostrar_resultado(repartidor, ruta, metros, recorrido)
            self._dibujar(recorrido)

        self._correr(self.boton, trabajo, terminado)

    def _mostrar_resultado(self, repartidor, ruta, metros, recorrido):
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        # Tabla: orden de visita y metros reales por calles de cada tramo
        carga = 0.0
        for orden, (p, tramo) in enumerate(zip(ruta, recorrido.tramos), start=1):
            self.tabla.insert("", "end", values=(
                orden, p.id, p.cliente, p.sector, f"{p.peso:g}", f"{tramo:,.0f}"))
            carga += p.peso

        self.var_total.set(f"Recorrido por calles: {recorrido.metros:,.0f} m  "
                           f"({recorrido.metros / 1000:.2f} km)")
        self.var_recta.set(f"En línea recta serían {metros:,.0f} m (con eso el algoritmo decide el orden).")
        self.var_carga.set(f"Pedidos en ruta: {len(ruta)}   |   "
                           f"Carga: {carga:g} / {repartidor.capacidad:g} kg")

        omitidos = len(self.app.pedidos) - len(ruta)
        avisos = []
        if omitidos > 0:
            avisos.append(f"{omitidos} pedido(s) no entraron por capacidad.")
        if recorrido.sin_camino > 0:
            avisos.append(f"{recorrido.sin_camino} tramo(s) sin camino por calles cerradas (se dibujan rectos).")
        self.var_omitidos.set(" ".join(avisos))

    def _dibujar(self, recorrido):
        canvas = getattr(self.app, "canvas", None)
        if canvas is None or len(recorrido.trazo) < 2:
            return
        canvas.limpiar_rutas()
        canvas.dibujar_ruta(recorrido.trazo)

    # ------------------------------------------------------------------
    # Pedido urgente -> repartidor más cercano con capacidad
    # ------------------------------------------------------------------
    def _asignar_urgente(self):
        indice = self.combo_pedido.current()
        repartidores = list(getattr(self.app, "repartidores", []))
        if indice < 0:
            messagebox.showwarning("Falta pedido", "Elige un pedido.")
            return
        if not repartidores:
            messagebox.showwarning("Sin repartidores", "No hay repartidores cargados.")
            return

        pedido = self._pedidos[indice]
        grafo = getattr(self.app, "grafo", None)

        def trabajo():
            elegido = asignar_urgente(pedido, repartidores)
            if elegido is None:
                return None, None
            return elegido, recorrido_por_calles(grafo, [elegido, pedido])

        def terminado(resultado):
            elegido, recorrido = resultado
            if elegido is None:
                self.var_urgente.set(f"Ningún repartidor tiene capacidad para el pedido "
                                     f"#{pedido.id} ({pedido.peso:g} kg).")
                return
            recta = distancia(elegido, pedido)
            self.var_urgente.set(
                f"Pedido #{pedido.id} ({pedido.cliente}) -> {elegido.nombre}: "
                f"{recorrido.metros:,.0f} m por calles ({recta:,.0f} m en línea recta). "
                f"Capacidad {elegido.capacidad:g} kg.")
            canvas = getattr(self.app, "canvas", None)
            if canvas is not None:
                canvas.limpiar_rutas()
                canvas.dibujar_ruta(recorrido.trazo, color=COLOR_URGENTE)

        self._correr(self.boton_urgente, trabajo, terminado)
