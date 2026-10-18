# gui/pestana_greedy.py
# Pestaña "Greedy" (enfoque voraz). Tiene dos partes:
#   1) Vecino más cercano: el repartidor siempre visita el pedido más próximo que le quepa.
#   2) Pedido urgente: se asigna al repartidor más cercano que tenga capacidad para llevarlo.
#
# Lo que espera del objeto `app` (lo entrega ventana_principal.py):
#     app.pedidos       -> lista de Pedido
#     app.repartidores  -> lista de Repartidor
#     app.canvas        -> CanvasMapa con limpiar_rutas() y dibujar_ruta(puntos, color)

import tkinter as tk
from tkinter import ttk, messagebox

from algoritmos.greedy import vecino_mas_cercano, asignar_urgente, distancia

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
        ttk.Button(barra, text="Ejecutar", command=self._ejecutar).pack(side="left")

        # --- Resultados
        self.var_total = tk.StringVar(value="Metros totales: -")
        self.var_carga = tk.StringVar(value="")
        self.var_omitidos = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.var_total,
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=8)
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
        ttk.Button(fila, text="Asignar", command=self._asignar_urgente).pack(side="left")
        self.var_urgente = tk.StringVar(value="")
        ttk.Label(urgente, textvariable=self.var_urgente, wraplength=520).pack(
            anchor="w", pady=(6, 0))

        # --- Tabla con el orden de visita
        columnas = ("orden", "id", "cliente", "sector", "peso", "tramo")
        titulos = ("#", "ID", "Cliente", "Sector", "Peso (kg)", "Tramo (m)")
        anchos = (40, 40, 200, 110, 80, 90)
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
        ruta, metros = vecino_mas_cercano(repartidor, self.app.pedidos)

        self._mostrar_resultado(repartidor, ruta, metros)
        self._dibujar(repartidor, ruta)

    def _mostrar_resultado(self, repartidor, ruta, metros):
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        # Tabla: orden de visita y metros de cada tramo
        anterior = repartidor
        carga = 0.0
        for orden, p in enumerate(ruta, start=1):
            tramo = distancia(anterior, p)
            self.tabla.insert("", "end", values=(
                orden, p.id, p.cliente, p.sector, f"{p.peso:g}", f"{tramo:.0f}"))
            carga += p.peso
            anterior = p

        self.var_total.set(f"Metros totales: {metros:,.0f} m  ({metros / 1000:.2f} km)")
        self.var_carga.set(f"Pedidos en ruta: {len(ruta)}   |   "
                           f"Carga: {carga:g} / {repartidor.capacidad:g} kg")

        omitidos = len(self.app.pedidos) - len(ruta)
        if omitidos > 0:
            self.var_omitidos.set(f"{omitidos} pedido(s) no entraron por capacidad.")
        else:
            self.var_omitidos.set("")

    def _dibujar(self, repartidor, ruta):
        canvas = getattr(self.app, "canvas", None)
        if canvas is None or not ruta:
            return
        # Lista de puntos (lat, lon): primero el repartidor, luego cada pedido
        puntos = [(repartidor.lat, repartidor.lon)] + [(p.lat, p.lon) for p in ruta]
        canvas.limpiar_rutas()
        canvas.dibujar_ruta(puntos)

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
        elegido = asignar_urgente(pedido, repartidores)
        if elegido is None:
            self.var_urgente.set(f"Ningún repartidor tiene capacidad para el pedido "
                                 f"#{pedido.id} ({pedido.peso:g} kg).")
            return

        metros = distancia(elegido, pedido)
        self.var_urgente.set(f"Pedido #{pedido.id} ({pedido.cliente}) -> {elegido.nombre}, "
                             f"a {metros:,.0f} m  (capacidad {elegido.capacidad:g} kg).")
        canvas = getattr(self.app, "canvas", None)
        if canvas is not None:
            canvas.limpiar_rutas()
            canvas.dibujar_ruta([(elegido.lat, elegido.lon), (pedido.lat, pedido.lon)],
                                color=COLOR_URGENTE)
