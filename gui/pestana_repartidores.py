# gui/pestana_repartidores.py
# Pestaña "Repartidores": agregar y eliminar repartidores (nombre, capacidad y posición inicial).
#
# Lo que espera del objeto `app` (lo entrega ventana_principal.py):
#     app.repartidores  -> lista de Repartidor (compartida por todas las pestañas; se modifica en el sitio)
#     app.grafo         -> Grafo (para decir en qué sector queda cada repartidor)
#     app.canvas        -> CanvasMapa con dibujar_repartidores(repartidores)   (opcional)
#
# Para poner la posición basta hacer clic en el mapa: la ventana principal copia la latitud y
# la longitud a esta pestaña (usa los nombres var_lat y var_lon, igual que la pestaña Pedidos).

import tkinter as tk
from tkinter import ttk, messagebox

from modelos import Repartidor
from gui.pestana_pedidos import LAT_MIN, LAT_MAX, LON_MIN, LON_MAX


class PestanaRepartidores(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._crear_formulario()
        self._crear_tabla()
        self.mostrar()

    # ------------------------------------------------------------------
    def _crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Nuevo repartidor", padding=6)
        marco.pack(fill="x", padx=8, pady=6)

        self.var_nombre = tk.StringVar()
        self.var_capacidad = tk.StringVar()
        self.var_lat = tk.StringVar()
        self.var_lon = tk.StringVar()

        campos = [
            ("Nombre (ej. Pedro - moto)", self.var_nombre, 24),
            ("Capacidad (kg)", self.var_capacidad, 10),
            ("Latitud", self.var_lat, 12),
            ("Longitud", self.var_lon, 12),
        ]
        for columna, (texto, variable, ancho) in enumerate(campos):
            ttk.Label(marco, text=texto).grid(row=0, column=columna, padx=4, sticky="w")
            ttk.Entry(marco, textvariable=variable, width=ancho).grid(
                row=1, column=columna, padx=4, pady=(0, 4), sticky="w")

        ttk.Label(marco, foreground="#555555",
                  text="Tip: haz clic en el mapa para llenar la latitud y la longitud "
                       "(ahí empieza su recorrido).").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=4)

        botones = ttk.Frame(self)
        botones.pack(fill="x", padx=8)
        ttk.Button(botones, text="Agregar repartidor", command=self._agregar).pack(side="left")
        ttk.Button(botones, text="Eliminar seleccionado",
                   command=self._eliminar).pack(side="left", padx=8)
        self.var_estado = tk.StringVar()
        ttk.Label(botones, textvariable=self.var_estado).pack(side="right")

    def _crear_tabla(self):
        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True, padx=8, pady=8)

        columnas = ("id", "nombre", "capacidad", "lat", "lon", "sector")
        titulos = ("ID", "Nombre", "Capacidad (kg)", "Latitud", "Longitud", "Sector")
        anchos = (40, 190, 105, 90, 90, 100)
        self.tabla = ttk.Treeview(marco, columns=columnas, show="headings", height=12)
        for col, titulo, ancho in zip(columnas, titulos, anchos):
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, width=ancho, anchor="center")
        self.tabla.column("nombre", anchor="w")

        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

    # ------------------------------------------------------------------
    def mostrar(self):
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)
        for r in self.app.repartidores:
            sector = self.app.grafo.sector_de(r.lat, r.lon)
            self.tabla.insert("", "end", iid=str(r.id), values=(
                r.id, r.nombre, f"{r.capacidad:g}", f"{r.lat:.5f}", f"{r.lon:.5f}", sector))
        self.var_estado.set(f"{len(self.app.repartidores)} repartidor(es)")

    def _actualizar_mapa(self):
        canvas = getattr(self.app, "canvas", None)
        if canvas is not None:
            canvas.dibujar_repartidores(self.app.repartidores)

    # ------------------------------------------------------------------
    def _agregar(self):
        nombre = self.var_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Falta el nombre", "Escribe el nombre del repartidor.")
            return
        try:
            capacidad = float(self.var_capacidad.get().replace(",", "."))
        except ValueError:
            messagebox.showwarning("Capacidad no válida", "La capacidad debe ser un número, en kg.")
            return
        if capacidad <= 0:
            messagebox.showwarning("Capacidad no válida", "La capacidad debe ser mayor que 0.")
            return
        try:
            lat = float(self.var_lat.get().replace(",", "."))
            lon = float(self.var_lon.get().replace(",", "."))
        except ValueError:
            messagebox.showwarning("Falta la posición",
                                   "Haz clic en el mapa para elegir dónde empieza, "
                                   "o escribe la latitud y la longitud.")
            return
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            messagebox.showwarning("Fuera del mapa",
                                   "Esa posición queda fuera del mapa de Cusco.")
            return

        nuevo_id = max((r.id for r in self.app.repartidores), default=0) + 1
        self.app.repartidores.append(Repartidor(nuevo_id, nombre, lat, lon, capacidad))
        self._actualizar_mapa()
        self.mostrar()
        for variable in (self.var_nombre, self.var_capacidad, self.var_lat, self.var_lon):
            variable.set("")
        self.var_estado.set(f"Repartidor #{nuevo_id} agregado. Total: {len(self.app.repartidores)}")

    def _eliminar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Eliminar", "Selecciona un repartidor de la tabla.")
            return
        ids = {int(i) for i in seleccion}
        if not messagebox.askyesno("Eliminar", f"¿Eliminar {len(ids)} repartidor(es)?"):
            return
        self.app.repartidores[:] = [r for r in self.app.repartidores if r.id not in ids]
        self._actualizar_mapa()
        self.mostrar()
