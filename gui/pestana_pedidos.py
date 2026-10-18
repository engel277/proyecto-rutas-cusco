# gui/pestana_pedidos.py
# Pestaña "Pedidos": agregar pedidos, verlos en una tabla, ordenarlos y buscarlos.
#
# Lo que espera del objeto `app` (lo entrega la Persona 4 en ventana_principal.py):
#     app.pedidos       -> lista de Pedido (compartida por todas las pestañas)
#     app.repartidores  -> lista de Repartidor
#     app.canvas        -> CanvasMapa con dibujar_pedidos(pedidos)   (opcional)

import tkinter as tk
from tkinter import ttk, messagebox
from types import SimpleNamespace

from modelos import Pedido
from algoritmos.ordenacion_busqueda import (
    merge_sort, busqueda_binaria, agrupar_por_sector, normalizar_texto)
from algoritmos.greedy import distancia

# Sectores = distritos de mapacusco.py
SECTORES = ["Cusco", "Santiago", "Wánchaq", "San Sebastián",
            "San Jerónimo", "Saylla", "Poroy", "Ccorca"]

PRIORIDADES = {1: "1 - Urgente", 2: "2 - Normal", 3: "3 - Baja"}

# Área que cubre el mapa (la misma de mapacusco.py: distritos + BUFFER 0.01)
LAT_MIN, LAT_MAX = -13.5919, -13.4799
LON_MIN, LON_MAX = -72.0704, -71.8181

# Punto de referencia por defecto para "Ordenar por distancia": Plaza de Armas
CENTRO = SimpleNamespace(lat=-13.5164, lon=-71.9785)


class PestanaPedidos(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._crear_formulario()
        self._crear_botones_orden()
        self._crear_busqueda()
        self._crear_tabla()
        self.mostrar(self.app.pedidos)

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Nuevo pedido")
        marco.pack(fill="x", padx=8, pady=6)

        self.var_cliente = tk.StringVar()
        self.var_lat = tk.StringVar()
        self.var_lon = tk.StringVar()
        self.var_sector = tk.StringVar()
        self.var_prioridad = tk.StringVar(value=PRIORIDADES[2])
        self.var_peso = tk.StringVar()
        self.var_valor = tk.StringVar()

        campos = [
            ("Cliente", ttk.Entry(marco, textvariable=self.var_cliente, width=22)),
            ("Sector", ttk.Combobox(marco, textvariable=self.var_sector, values=SECTORES,
                                    state="readonly", width=14)),
            ("Prioridad", ttk.Combobox(marco, textvariable=self.var_prioridad,
                                       values=list(PRIORIDADES.values()),
                                       state="readonly", width=11)),
            ("Latitud", ttk.Entry(marco, textvariable=self.var_lat, width=12)),
            ("Longitud", ttk.Entry(marco, textvariable=self.var_lon, width=12)),
            ("Peso (kg)", ttk.Entry(marco, textvariable=self.var_peso, width=8)),
            ("Valor (S/)", ttk.Entry(marco, textvariable=self.var_valor, width=8)),
        ]
        # Dos filas de campos (así el botón Agregar siempre se ve, aunque el panel sea angosto)
        posiciones = [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (2, 2), (2, 3)]
        for (texto, widget), (fila, columna) in zip(campos, posiciones):
            ttk.Label(marco, text=texto).grid(row=fila, column=columna, padx=4, sticky="w")
            widget.grid(row=fila + 1, column=columna, padx=4, pady=(0, 6), sticky="w")

        ttk.Button(marco, text="Agregar pedido", command=self._agregar).grid(
            row=1, column=3, padx=8, pady=(0, 6), sticky="w")
        ttk.Label(marco, foreground="#555555",
                  text="Tip: haz clic en el mapa para llenar la latitud y la longitud.").grid(
            row=4, column=0, columnspan=4, sticky="w", padx=4)

    def _crear_botones_orden(self):
        marco = ttk.Frame(self)
        marco.pack(fill="x", padx=8)

        ttk.Button(marco, text="Ordenar por prioridad",
                   command=self._ordenar_por_prioridad).pack(side="left")

        ttk.Button(marco, text="Ordenar por distancia",
                   command=self._ordenar_por_distancia).pack(side="left", padx=(8, 4))
        ttk.Label(marco, text="desde:").pack(side="left")
        self.var_desde = tk.StringVar()
        self.combo_desde = ttk.Combobox(marco, textvariable=self.var_desde,
                                        state="readonly", width=28)
        self.combo_desde.pack(side="left", padx=4)
        self.combo_desde.bind("<Button-1>", lambda e: self._cargar_puntos_referencia())
        self._cargar_puntos_referencia()

    def _crear_busqueda(self):
        marco = ttk.LabelFrame(self, text="Buscar por ID o sector")
        marco.pack(fill="x", padx=8, pady=6)

        self.var_busqueda = tk.StringVar()
        caja = ttk.Entry(marco, textvariable=self.var_busqueda, width=25)
        caja.pack(side="left", padx=6, pady=4)
        caja.bind("<Return>", lambda e: self._buscar())
        ttk.Button(marco, text="Buscar", command=self._buscar).pack(side="left")
        ttk.Button(marco, text="Mostrar todos",
                   command=lambda: self.mostrar(self.app.pedidos)).pack(side="left", padx=6)

        self.var_estado = tk.StringVar()
        ttk.Label(marco, textvariable=self.var_estado).pack(side="right", padx=8)

    def _crear_tabla(self):
        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        columnas = ("id", "cliente", "sector", "prioridad", "peso", "valor",
                    "lat", "lon", "distancia")
        titulos = ("ID", "Cliente", "Sector", "Prioridad", "Peso (kg)", "Valor (S/)",
                   "Latitud", "Longitud", "Dist. (m)")
        anchos = (32, 140, 92, 82, 74, 80, 78, 80, 78)

        self.tabla = ttk.Treeview(marco, columns=columnas, show="headings", height=12)
        for col, titulo, ancho in zip(columnas, titulos, anchos):
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, width=ancho, anchor="center")
        self.tabla.column("cliente", anchor="w")

        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

    # ------------------------------------------------------------------
    # Mostrar datos en la tabla
    # ------------------------------------------------------------------
    def mostrar(self, pedidos, distancias=None):
        """Llena la tabla. `distancias` es un dict {id_pedido: metros} opcional."""
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        for p in pedidos:
            dist = "-"
            if distancias is not None and p.id in distancias:
                dist = f"{distancias[p.id]:.0f}"
            self.tabla.insert("", "end", values=(
                p.id, p.cliente, p.sector, PRIORIDADES.get(p.prioridad, p.prioridad),
                f"{p.peso:g}", f"{p.valor:g}", f"{p.lat:.5f}", f"{p.lon:.5f}", dist))

        self.var_estado.set(f"Mostrando {len(pedidos)} de {len(self.app.pedidos)} pedidos")

    def _refrescar_mapa(self):
        canvas = getattr(self.app, "canvas", None)
        if canvas is not None:
            canvas.dibujar_pedidos(self.app.pedidos)

    # ------------------------------------------------------------------
    # Agregar pedido (con validación)
    # ------------------------------------------------------------------
    def _agregar(self):
        pedido = self._leer_formulario()
        if pedido is None:
            return
        self.app.pedidos.append(pedido)
        self.mostrar(self.app.pedidos)
        self._refrescar_mapa()
        self._limpiar_formulario()

    def _leer_formulario(self):
        """Valida los campos. Si algo está mal muestra un messagebox y devuelve None."""
        cliente = self.var_cliente.get().strip()
        if cliente == "":
            messagebox.showwarning("Dato faltante", "Escribe el nombre del cliente.")
            return None

        try:
            lat = float(self.var_lat.get().replace(",", "."))
            lon = float(self.var_lon.get().replace(",", "."))
        except ValueError:
            messagebox.showwarning("Coordenadas inválidas",
                                   "Latitud y longitud deben ser números.\n"
                                   "Ejemplo: -13.5164 y -71.9785")
            return None
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            messagebox.showwarning("Fuera del mapa",
                                   "Esas coordenadas están fuera del área del mapa de Cusco.\n"
                                   f"Latitud entre {LAT_MIN} y {LAT_MAX}\n"
                                   f"Longitud entre {LON_MIN} y {LON_MAX}")
            return None

        sector = self.var_sector.get()
        if sector == "":
            messagebox.showwarning("Dato faltante", "Elige el sector del pedido.")
            return None

        try:
            peso = float(self.var_peso.get().replace(",", "."))
            if peso <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Peso inválido", "El peso debe ser un número mayor que 0.")
            return None

        try:
            valor = float(self.var_valor.get().replace(",", "."))
            if valor < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Valor inválido", "El valor debe ser un número (0 o más).")
            return None

        prioridad = int(self.var_prioridad.get()[0])     # "1 - Urgente" -> 1

        # Nuevo id = mayor id actual + 1
        nuevo_id = 1
        for p in self.app.pedidos:
            if p.id >= nuevo_id:
                nuevo_id = p.id + 1

        return Pedido(nuevo_id, cliente, lat, lon, sector, prioridad, peso, valor)

    def _limpiar_formulario(self):
        for var in (self.var_cliente, self.var_lat, self.var_lon, self.var_peso, self.var_valor):
            var.set("")
        self.var_prioridad.set(PRIORIDADES[2])

    # ------------------------------------------------------------------
    # Ordenar (usa merge_sort propio)
    # ------------------------------------------------------------------
    def _ordenar_por_prioridad(self):
        # Urgentes primero; en empate, por id
        ordenados = merge_sort(self.app.pedidos, lambda p: (p.prioridad, p.id))
        self.app.pedidos[:] = ordenados          # conserva la misma lista compartida
        self.mostrar(self.app.pedidos)

    def _cargar_puntos_referencia(self):
        """Llena el combo 'desde:' con el centro y los repartidores actuales."""
        self._puntos = [("Centro (Plaza de Armas)", CENTRO)]
        for r in getattr(self.app, "repartidores", []):
            self._puntos.append((f"Repartidor: {r.nombre}", r))
        nombres = [nombre for nombre, _ in self._puntos]
        self.combo_desde["values"] = nombres
        if self.var_desde.get() not in nombres:
            self.var_desde.set(nombres[0])

    def _ordenar_por_distancia(self):
        self._cargar_puntos_referencia()
        referencia = self._puntos[0][1]
        for nombre, punto in self._puntos:
            if nombre == self.var_desde.get():
                referencia = punto

        ordenados = merge_sort(self.app.pedidos, lambda p: distancia(referencia, p))
        self.app.pedidos[:] = ordenados
        distancias = {p.id: distancia(referencia, p) for p in ordenados}
        self.mostrar(self.app.pedidos, distancias)

    # ------------------------------------------------------------------
    # Buscar por ID (búsqueda binaria) o por sector (agrupar_por_sector)
    # ------------------------------------------------------------------
    def _buscar(self):
        texto = self.var_busqueda.get().strip()
        if texto == "":
            messagebox.showinfo("Buscar", "Escribe un ID (ej. 5) o un sector (ej. Wánchaq).")
            return

        if texto.isdigit():
            # La búsqueda binaria necesita la lista ordenada por id
            por_id = merge_sort(self.app.pedidos, lambda p: p.id)
            pedido = busqueda_binaria(por_id, int(texto))
            if pedido is None:
                messagebox.showinfo("Sin resultados", f"No existe un pedido con ID {texto}.")
                return
            self.mostrar([pedido])
        else:
            buscado = normalizar_texto(texto)
            encontrados = []
            grupos = agrupar_por_sector(self.app.pedidos)
            for sector, lista in grupos.items():
                if buscado in normalizar_texto(sector):
                    encontrados.extend(lista)
            if not encontrados:
                messagebox.showinfo("Sin resultados",
                                    f"No hay pedidos en un sector que coincida con '{texto}'.")
                return
            self.mostrar(merge_sort(encontrados, lambda p: p.id))
