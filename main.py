"Daniel - main.py"
# main.py
# Persona 4 (Daniel): punto de entrada. Crea la ventana, carga el grafo y los pedidos de ejemplo
# y llama a mainloop().
#
# Ejecutar desde la carpeta del proyecto:   python main.py
# Antes hay que tener herramientas/grafo.json (se genera una vez con herramientas/mapacusco.py).

import os
import sys
import tkinter as tk
from tkinter import messagebox

# Carpeta del proyecto: así los imports (mapa, algoritmos, gui...) funcionan desde cualquier lado
CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)

from mapa.grafo import Grafo
from modelos import Repartidor, cargar_pedidos
from gui.ventana_principal import App
from pruebas.benchmark import generar_pedidos

RUTA_GRAFO = os.path.join(CARPETA, "herramientas", "grafo.json")
RUTA_PEDIDOS = os.path.join(CARPETA, "datos", "pedidos_ejemplo.json")


def repartidores_de_ejemplo():
    # Tres repartidores con distinta capacidad (moto, camioneta y bicicleta)
    return [
        Repartidor(1, "Juan (moto)", -13.5164, -71.9785, 40),
        Repartidor(2, "María (camioneta)", -13.5346, -71.9490, 80),
        Repartidor(3, "Luis (bici)", -13.5270, -71.9896, 25),
    ]


def main():
    # 1) Cargar el mapa. Si falta grafo.json se avisa qué hacer en lugar de dejar un error feo
    if not os.path.exists(RUTA_GRAFO):
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror("Falta el mapa",
                             f"No existe {RUTA_GRAFO}\n\n"
                             "Ejecuta primero herramientas/mapacusco.py para descargarlo.")
        return
    grafo = Grafo()
    grafo.cargar(RUTA_GRAFO)

    # 2) Cargar los pedidos de ejemplo; si no existe el JSON se generan 20 aleatorios
    if os.path.exists(RUTA_PEDIDOS):
        pedidos = cargar_pedidos(RUTA_PEDIDOS)
    else:
        pedidos = generar_pedidos(20, semilla=1)

    # 3) Crear la ventana y empezar
    App(grafo, pedidos, repartidores_de_ejemplo()).mainloop()


if __name__ == "__main__":
    main()
