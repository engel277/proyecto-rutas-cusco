# probar_seccion3.py
# Lanzador TEMPORAL para probar la sección 3 (Zonas y Mochila) junto con las
# pestañas de la sección 2 (Pedidos y Greedy).
#
#   - Si existe herramientas/grafo.json, las distancias se calculan POR CALLES (A*).
#   - Si no existe, usa línea recta (Haversine) y todo funciona igual.
#
# Ejecutar desde la carpeta del proyecto:   python probar_seccion3.py

import os

from probar_seccion2 import AppFalsa
from gui.pestana_zonas import PestanaZonas
from gui.pestana_mochila import PestanaMochila

CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA_GRAFO = os.path.join(CARPETA, "herramientas", "grafo.json")


def activar_mapa():
    if not os.path.exists(RUTA_GRAFO):
        print("No hay herramientas/grafo.json -> distancias en LÍNEA RECTA.")
        return
    from mapa.grafo import Grafo
    from mapa import distancias
    print("Cargando grafo.json ...")
    grafo = Grafo()
    grafo.cargar(RUTA_GRAFO)
    distancias.usar_grafo(grafo)
    print(f"Grafo cargado ({len(grafo.nodos)} esquinas) -> distancias POR CALLES (A*).")
    print("Ojo: la primera vez cada botón puede tardar unos segundos (A* + caché).")


class AppFalsa3(AppFalsa):
    def __init__(self):
        super().__init__()
        self.title("Prueba sección 3 - Zonas y Mochila")
        cuaderno = self.winfo_children()[-1]          # el ttk.Notebook que creó AppFalsa
        cuaderno.add(PestanaZonas(cuaderno, self), text="Zonas")
        cuaderno.add(PestanaMochila(cuaderno, self), text="Mochila")


if __name__ == "__main__":
    activar_mapa()
    AppFalsa3().mainloop()
