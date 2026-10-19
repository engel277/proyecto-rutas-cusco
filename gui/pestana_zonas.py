# gui/pestana_zonas.py
# Pestaña "Zonas": Divide y Vencerás. Divide la ciudad entre los repartidores
# y dibuja la ruta de cada zona en un color distinto.
#
# Lo que espera del objeto `app` (igual que pestana_greedy.py):
#     app.pedidos       -> lista de Pedido
#     app.repartidores  -> lista de Repartidor
#     app.canvas        -> CanvasMapa con limpiar_rutas() y dibujar_ruta(puntos[, color])
#     app.grafo         -> Grafo (para dibujar las rutas por las calles reales)
#     app.ejecutar_en_hilo(trabajo, al_terminar, al_error)   (opcional: evita congelar la ventana)

import tkinter as tk
from tkinter import ttk, messagebox

from algoritmos.divide_venceras import dividir_en_zonas, rutas_por_zona
from mapa.recorridos import recorrido_por_calles

COLORES = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
           "#008080", "#9a6324", "#800000", "#808000", "#000075"]


class PestanaZonas(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=8, pady=8)
        self.boton = ttk.Button(barra, text="Dividir ciudad", command=self._dividir)
        self.boton.pack(side="left")
        self.var_info = tk.StringVar(value="Se usa a todos los repartidores y todos los pedidos.")
        ttk.Label(barra, textvariable=self.var_info).pack(side="left", padx=10)

        self.var_total = tk.StringVar(value="Recorrido por calles (todas las zonas): -")
        ttk.Label(self, textvariable=self.var_total,
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=8)
        self.var_aviso = tk.StringVar()
        ttk.Label(self, textvariable=self.var_aviso, foreground="#b34700").pack(
            anchor="w", padx=8, pady=(0, 6))

        columnas = ("color", "repartidor", "zona", "ruta", "carga", "metros")
        titulos = ("Color", "Repartidor", "Pedidos en zona", "Pedidos en ruta",
                   "Carga (kg)", "Por calles (m)")
        anchos = (60, 170, 105, 95, 105, 105)
        self.tabla = ttk.Treeview(self, columns=columnas, show="headings", height=10)
        for col, titulo, ancho in zip(columnas, titulos, anchos):
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, width=ancho, anchor="center")
        self.tabla.column("repartidor", anchor="w")
        self.tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Un tag por color para pintar la celda de la tabla
        for i, color in enumerate(COLORES):
            self.tabla.tag_configure(f"c{i}", foreground=color)

    # ------------------------------------------------------------------
    def _dividir(self):
        repartidores = list(getattr(self.app, "repartidores", []))
        if len(repartidores) == 0:
            messagebox.showwarning("Sin repartidores", "No hay repartidores cargados.")
            return
        if len(self.app.pedidos) == 0:
            messagebox.showwarning("Sin pedidos", "No hay pedidos cargados.")
            return

        pedidos = list(self.app.pedidos)
        grafo = getattr(self.app, "grafo", None)

        # Dividir y asignar zonas usa distancia recta; después se calcula el recorrido real por
        # calles de cada repartidor (puede tardar un poco, por eso va en un hilo)
        def trabajo():
            zonas = dividir_en_zonas(pedidos, repartidores)
            resultados = rutas_por_zona(zonas)
            recorridos = [recorrido_por_calles(grafo, [rep] + ruta) for rep, ruta, _ in resultados]
            return zonas, resultados, recorridos

        def terminado(resultado):
            self.boton.state(["!disabled"])
            zonas, resultados, recorridos = resultado
            self._mostrar(zonas, resultados, recorridos)
            self._dibujar(recorridos)

        def fallo(error):
            self.boton.state(["!disabled"])
            messagebox.showerror("Error", str(error))

        self.boton.state(["disabled"])
        en_hilo = getattr(self.app, "ejecutar_en_hilo", None)
        if en_hilo is None:
            try:
                terminado(trabajo())
            except Exception as error:
                fallo(error)
        else:
            en_hilo(trabajo, terminado, fallo)

    def _mostrar(self, zonas, resultados, recorridos):
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        total_metros = 0.0
        sin_entrar = 0
        sin_camino = 0
        for i, ((rep, pedidos_zona), (_, ruta, _), recorrido) in enumerate(zip(zonas, resultados, recorridos)):
            carga = sum(p.peso for p in ruta)
            self.tabla.insert("", "end", tags=(f"c{i % len(COLORES)}",), values=(
                "■■■", f"{rep.id} - {rep.nombre}", len(pedidos_zona), len(ruta),
                f"{carga:g} / {rep.capacidad:g}", f"{recorrido.metros:,.0f}"))
            total_metros += recorrido.metros
            sin_entrar += len(pedidos_zona) - len(ruta)
            sin_camino += recorrido.sin_camino

        self.var_total.set(f"Recorrido por calles (todas las zonas): {total_metros:,.0f} m  "
                           f"({total_metros / 1000:.2f} km)")
        avisos = []
        if sin_entrar > 0:
            avisos.append(f"{sin_entrar} pedido(s) no entraron por capacidad del repartidor de su zona.")
        if sin_camino > 0:
            avisos.append(f"{sin_camino} tramo(s) sin camino por calles cerradas (se dibujan rectos).")
        self.var_aviso.set(" ".join(avisos))

    def _dibujar(self, recorridos):
        canvas = getattr(self.app, "canvas", None)
        if canvas is None:
            return
        canvas.limpiar_rutas()
        for i, recorrido in enumerate(recorridos):
            if len(recorrido.trazo) < 2:
                continue
            color = COLORES[i % len(COLORES)]
            # >>> Si el dibujar_ruta del canvas no acepta `color`, solo se cambia aquí. <<<
            try:
                canvas.dibujar_ruta(recorrido.trazo, color=color)
            except TypeError:
                canvas.dibujar_ruta(recorrido.trazo)
