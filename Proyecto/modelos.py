# modelos.py
# Clases de datos del sistema. El resto de archivos hacen:
#     from modelos import Pedido, Repartidor

import json
from dataclasses import dataclass


@dataclass
class Pedido:
    id: int
    cliente: str
    lat: float
    lon: float
    sector: str
    prioridad: int      # 1 = urgente, 2 = normal, 3 = baja
    peso: float         # kg
    valor: float        # soles


@dataclass
class Repartidor:
    id: int
    nombre: str
    lat: float
    lon: float
    capacidad: float    # kg


def cargar_pedidos(ruta_json):
    """Lee un JSON (lista de pedidos) y devuelve una lista de objetos Pedido.
    Lo puede usar main.py (Persona 4) para cargar datos/pedidos_ejemplo.json."""
    with open(ruta_json, "r", encoding="utf-8") as f:
        datos = json.load(f)
    return [Pedido(**d) for d in datos]
