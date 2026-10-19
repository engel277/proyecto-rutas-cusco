# gui/pestana_mochila.py
# Pestaña "Mochila": Programación Dinámica. Elige qué pedidos cargar en el
# vehículo de un repartidor maximizando el valor sin pasar su capacidad.
#
# Lo que espera del objeto `app` (igual que pestana_greedy.py):
#     app.pedidos       -> lista de Pedido
#     app.repartidores  -> lista de Repartidor
#     app.canvas        -> CanvasMapa con limpiar_rutas() y dibujar_ruta(puntos)  (opcional)
#     app.grafo         -> Grafo (para dibujar el recorrido por las calles reales)
#     app.ejecutar_en_hilo(trabajo, al_terminar, al_error)   (opcional: evita congelar la ventana)

import tkinter as tk
from tkinter import ttk, messagebox

from algoritmos.mochila import llenar_mochila
from algoritmos.greedy import vecino_mas_cercano
from mapa.recorridos import recorrido_por_calles


class PestanaMochila(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._repartidores = []

        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=8, pady=8)
        ttk.Label(barra, text="Repartidor:").pack(side="left")
        self.var_repartidor = tk.StringVar()
        self.combo = ttk.Combobox(barra, textvariable=self.var_repartidor,
                                  state="readonly", width=38)
        self.combo.pack(side="left", padx=6)
        self.boton = ttk.Button(barra, text="Cargar", command=self._cargar)
        self.boton.pack(side="left")

        self.var_peso = tk.StringVar(value="Peso total: -")
        self.var_valor = tk.StringVar(value="Valor total: -")
        self.var_resto = tk.StringVar()
        self.var_recorrido = tk.StringVar()
        ttk.Label(self, textvariable=self.var_peso,
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=8)
        ttk.Label(self, textvariable=self.var_valor,
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=8)
        ttk.Label(self, textvariable=self.var_recorrido).pack(anchor="w", padx=8)
        ttk.Label(self, textvariable=self.var_resto, foreground="#b34700").pack(
            anchor="w", padx=8, pady=(0, 6))

        columnas = ("id", "cliente", "sector", "prioridad", "peso", "valor")
        titulos = ("ID", "Cliente", "Sector", "Prioridad", "Peso (kg)", "Valor (S/)")
        anchos = (40, 200, 110, 80, 80, 90)
        self.tabla = ttk.Treeview(self, columns=columnas, show="headings", height=12)
        for col, titulo, ancho in zip(columnas, titulos, anchos):
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, width=ancho, anchor="center")
        self.tabla.column("cliente", anchor="w")
        self.tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.bind("<Map>", lambda e: self._cargar_repartidores())
        self._cargar_repartidores()

    # ------------------------------------------------------------------
    def _cargar_repartidores(self):
        self._repartidores = list(getattr(self.app, "repartidores", []))
        textos = [f"{r.id} - {r.nombre} (capacidad {r.capacidad:g} kg)"
                  for r in self._repartidores]
        self.combo["values"] = textos
        if textos and self.var_repartidor.get() not in textos:
            self.combo.current(0)

    def _cargar(self):
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

        # Mochila (PD); luego el orden de visita de lo elegido y su recorrido real por calles
        def trabajo():
            elegidos, peso_total, valor_total = llenar_mochila(pedidos, repartidor.capacidad)
            ruta, _ = vecino_mas_cercano(repartidor, elegidos)
            return elegidos, peso_total, valor_total, recorrido_por_calles(grafo, [repartidor] + ruta)

        def terminado(resultado):
            self.boton.state(["!disabled"])
            elegidos, peso_total, valor_total, recorrido = resultado
            self._mostrar(repartidor, elegidos, peso_total, valor_total, recorrido)
            self._dibujar(recorrido)

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

    def _mostrar(self, repartidor, elegidos, peso_total, valor_total, recorrido):
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)
        for p in elegidos:
            self.tabla.insert("", "end", values=(
                p.id, p.cliente, p.sector, p.prioridad, f"{p.peso:g}", f"{p.valor:g}"))

        self.var_peso.set(f"Peso total: {peso_total:g} / {repartidor.capacidad:g} kg")
        self.var_valor.set(f"Valor total: S/ {valor_total:g}")
        if elegidos:
            self.var_recorrido.set(f"Recorrido para entregarlos: {recorrido.metros:,.0f} m por calles "
                                   f"({recorrido.metros / 1000:.2f} km).")
        else:
            self.var_recorrido.set("")
        dejados = len(self.app.pedidos) - len(elegidos)
        self.var_resto.set(f"{len(elegidos)} pedido(s) cargados, {dejados} se quedan en el almacén.")

    def _dibujar(self, recorrido):
        """Dibuja el recorrido por calles de los pedidos elegidos."""
        canvas = getattr(self.app, "canvas", None)
        if canvas is None or len(recorrido.trazo) < 2:
            return
        canvas.limpiar_rutas()
        canvas.dibujar_ruta(recorrido.trazo)
