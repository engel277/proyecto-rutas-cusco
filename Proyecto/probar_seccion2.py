# probar_seccion2.py
# Lanzador TEMPORAL para probar tu parte sin esperar a la Persona 4.
# Crea una ventana con tus dos pestañas y un canvas falso que dibuja puntos y rutas.
# Ejecutar desde la carpeta del proyecto:   python probar_seccion2.py
# Cuando exista main.py / ventana_principal.py de la Persona 4, este archivo ya no hace falta.

import os
import tkinter as tk
from tkinter import ttk

from modelos import Repartidor, cargar_pedidos
from gui.pestana_pedidos import PestanaPedidos, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX
from gui.pestana_greedy import PestanaGreedy

COLORES = {1: "red", 2: "orange", 3: "gray"}


class CanvasFalso(tk.Canvas):
    """Imita lo mínimo del CanvasMapa de la Persona 4."""
    def __init__(self, parent, ancho=520, alto=520):
        super().__init__(parent, width=ancho, height=alto, bg="white")
        self.ancho, self.alto = ancho, alto

    def convertir(self, lat, lon):
        x = (lon - LON_MIN) / (LON_MAX - LON_MIN) * self.ancho
        y = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * self.alto
        return x, y

    def dibujar_pedidos(self, pedidos):
        self.delete("pedido")
        for p in pedidos:
            x, y = self.convertir(p.lat, p.lon)
            self.create_oval(x - 5, y - 5, x + 5, y + 5, fill=COLORES.get(p.prioridad, "black"),
                             tags="pedido")
            self.create_text(x + 8, y - 8, text=str(p.id), tags="pedido")

    def limpiar_rutas(self):
        self.delete("ruta")

    def dibujar_ruta(self, puntos, color="blue"):
        pixeles = []
        for lat, lon in puntos:
            pixeles.extend(self.convertir(lat, lon))
        if len(pixeles) >= 4:
            self.create_line(*pixeles, fill=color, width=2, arrow="last", tags="ruta")


class AppFalsa(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Prueba sección 2 - Pedidos y Greedy")

        carpeta = os.path.dirname(os.path.abspath(__file__))
        self.pedidos = cargar_pedidos(os.path.join(carpeta, "datos", "pedidos_ejemplo.json"))
        self.repartidores = [
            Repartidor(1, "Juan (moto)", -13.5164, -71.9785, 40),
            Repartidor(2, "María (camioneta)", -13.5346, -71.9490, 80),
            Repartidor(3, "Luis (bici)", -13.5270, -71.9896, 25),
        ]

        self.canvas = CanvasFalso(self)
        self.canvas.pack(side="right", padx=6, pady=6)

        cuaderno = ttk.Notebook(self)
        cuaderno.pack(side="left", fill="both", expand=True)
        cuaderno.add(PestanaPedidos(cuaderno, self), text="Pedidos")
        cuaderno.add(PestanaGreedy(cuaderno, self), text="Greedy")

        self.canvas.dibujar_pedidos(self.pedidos)


if __name__ == "__main__":
    AppFalsa().mainloop()
