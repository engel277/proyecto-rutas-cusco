"Daniel - pruebas/test_algoritmos.py"
# pruebas/test_algoritmos.py
# Persona 4 (JC): pruebas unitarias (unittest) de todos los algoritmos del proyecto.
#
# Ejecutar desde la carpeta del proyecto:   python -m unittest pruebas.test_algoritmos -v
#
# Cada prueba tiene un caso y un resultado esperado, para copiarlos al informe en la sección
# "Casos y datos de prueba". Las pruebas del mapa NO usan grafo.json: arman una cuadrícula
# pequeña de 3x3 esquinas en memoria, así corren rápido y en cualquier computador.

import heapq
import itertools
import os
import random
import sys
import threading
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos import Pedido, Repartidor
from mapa import distancias
from mapa.distancias import distancia, distancia_recta
from mapa.grafo import Grafo
from mapa.caminos import a_estrella
from algoritmos.ordenacion_busqueda import (
    merge_sort, busqueda_binaria, agrupar_por_sector, normalizar_texto)
from algoritmos import greedy
from algoritmos.greedy import vecino_mas_cercano, asignar_urgente
from algoritmos.divide_venceras import dividir_en_zonas, rutas_por_zona
from algoritmos.mochila import llenar_mochila
from algoritmos.backtracking import buscar_rutas
from pruebas.benchmark import generar_pedidos

INF = float("inf")


def pedido(id_, lat=-13.5, lon=-71.98, prioridad=2, peso=1.0, valor=10.0, sector="Cusco"):
    """Atajo para crear un Pedido con solo los datos que importan en cada prueba."""
    return Pedido(id_, f"Cliente {id_}", lat, lon, sector, prioridad, peso, valor)


# ===========================================================================
# 1. Ordenación y búsqueda
# ===========================================================================
class TestOrdenacionBusqueda(unittest.TestCase):
    def test_merge_sort_ordena_por_prioridad(self):
        # Caso: prioridades desordenadas. Esperado: 1, 1, 2, 3
        pedidos = [pedido(1, prioridad=3), pedido(2, prioridad=1),
                   pedido(3, prioridad=2), pedido(4, prioridad=1)]
        resultado = merge_sort(pedidos, lambda p: p.prioridad)
        self.assertEqual([p.prioridad for p in resultado], [1, 1, 2, 3])

    def test_merge_sort_es_estable(self):
        # Los pedidos 2 y 4 tienen la misma prioridad: deben quedar en su orden original (2 antes que 4)
        pedidos = [pedido(1, prioridad=3), pedido(2, prioridad=1),
                   pedido(3, prioridad=2), pedido(4, prioridad=1)]
        resultado = merge_sort(pedidos, lambda p: p.prioridad)
        self.assertEqual([p.id for p in resultado], [2, 4, 3, 1])

    def test_merge_sort_no_modifica_la_lista_original(self):
        pedidos = [pedido(2), pedido(1)]
        merge_sort(pedidos, lambda p: p.id)
        self.assertEqual([p.id for p in pedidos], [2, 1])

    def test_merge_sort_coincide_con_sorted_en_datos_aleatorios(self):
        pedidos = generar_pedidos(200, semilla=3)
        propio = merge_sort(pedidos, lambda p: (p.prioridad, p.id))
        python = sorted(pedidos, key=lambda p: (p.prioridad, p.id))
        self.assertEqual([p.id for p in propio], [p.id for p in python])

    def test_merge_sort_lista_vacia_y_de_un_elemento(self):
        self.assertEqual(merge_sort([]), [])
        self.assertEqual(merge_sort([5]), [5])

    def test_busqueda_binaria_encuentra_y_no_encuentra(self):
        por_id = [pedido(i) for i in (2, 4, 6, 8, 10)]
        self.assertEqual(busqueda_binaria(por_id, 8).id, 8)      # existe
        self.assertEqual(busqueda_binaria(por_id, 2).id, 2)      # primer elemento
        self.assertEqual(busqueda_binaria(por_id, 10).id, 10)    # último elemento
        self.assertIsNone(busqueda_binaria(por_id, 5))           # no existe
        self.assertIsNone(busqueda_binaria([], 1))               # lista vacía

    def test_agrupar_por_sector(self):
        pedidos = [pedido(1, sector="Cusco"), pedido(2, sector="Poroy"), pedido(3, sector="Cusco")]
        grupos = agrupar_por_sector(pedidos)
        self.assertEqual([p.id for p in grupos["Cusco"]], [1, 3])
        self.assertEqual([p.id for p in grupos["Poroy"]], [2])

    def test_normalizar_texto_ignora_tildes_y_mayusculas(self):
        self.assertEqual(normalizar_texto("  Wánchaq "), "wanchaq")
        self.assertEqual(normalizar_texto("San Jerónimo"), "san jeronimo")


# ===========================================================================
# 2. Greedy
# ===========================================================================
class TestGreedy(unittest.TestCase):
    def setUp(self):
        distancias.usar_grafo(None)      # distancias en línea recta, sin depender del mapa

    def test_vecino_mas_cercano_visita_en_orden_de_cercania(self):
        # Pedidos sobre una línea (mismo lat). Repartidor en lon=0.000. Distancias: 1 -> 0.001, 2 -> 0.003, 3 -> 0.002
        rep = Repartidor(1, "R", -13.5, -71.980, 100)
        pedidos = [pedido(1, lon=-71.979), pedido(2, lon=-71.977), pedido(3, lon=-71.978)]
        ruta, metros = vecino_mas_cercano(rep, pedidos)
        self.assertEqual([p.id for p in ruta], [1, 3, 2])      # esperado: 1, luego 3, luego 2
        self.assertAlmostEqual(metros, distancia_recta(-13.5, -71.980, -13.5, -71.977), delta=0.5)

    def test_vecino_mas_cercano_respeta_la_capacidad(self):
        # Capacidad 10 kg. El más cercano pesa 6, el siguiente (6) ya no cabe, el último (3) sí
        rep = Repartidor(1, "R", -13.5, -71.980, 10)
        pedidos = [pedido(1, lon=-71.979, peso=6), pedido(2, lon=-71.978, peso=6),
                   pedido(3, lon=-71.977, peso=3)]
        ruta, _ = vecino_mas_cercano(rep, pedidos)
        self.assertEqual([p.id for p in ruta], [1, 3])
        self.assertLessEqual(sum(p.peso for p in ruta), rep.capacidad)

    def test_vecino_mas_cercano_no_modifica_los_pedidos_recibidos(self):
        rep = Repartidor(1, "R", -13.5, -71.980, 100)
        pedidos = [pedido(1, lon=-71.979), pedido(2, lon=-71.978)]
        vecino_mas_cercano(rep, pedidos)
        self.assertEqual(len(pedidos), 2)

    def test_vecino_mas_cercano_salta_pedidos_inalcanzables(self):
        # Si distancia() da infinito (calles cerradas) el pedido se deja fuera y los metros siguen finitos
        rep = Repartidor(1, "R", -13.5, -71.980, 100)
        pedidos = [pedido(1, lon=-71.979), pedido(2, lon=-71.978)]
        original = greedy.distancia
        greedy.distancia = lambda a, b: float("inf") if getattr(b, "id", 0) == 2 else original(a, b)
        try:
            ruta, metros = vecino_mas_cercano(rep, pedidos)
        finally:
            greedy.distancia = original
        self.assertEqual([p.id for p in ruta], [1])
        self.assertLess(metros, float("inf"))

    def test_asignar_urgente_elige_el_mas_cercano_con_capacidad(self):
        cerca_chico = Repartidor(1, "Cerca", -13.5, -71.979, 5)
        lejos_grande = Repartidor(2, "Lejos", -13.5, -71.900, 50)
        p = pedido(1, lon=-71.980, peso=10)
        self.assertEqual(asignar_urgente(p, [cerca_chico, lejos_grande]).id, 2)   # el cercano no carga 10 kg
        self.assertIsNone(asignar_urgente(pedido(2, peso=99), [cerca_chico, lejos_grande]))

    def test_vecino_mas_cercano_sin_pedidos(self):
        ruta, metros = vecino_mas_cercano(Repartidor(1, "R", -13.5, -71.98, 10), [])
        self.assertEqual((ruta, metros), ([], 0.0))

    def test_asignar_urgente_elige_al_mas_cercano_con_capacidad(self):
        urgente = pedido(1, lon=-71.980, peso=20, prioridad=1)
        cerca_sin_capacidad = Repartidor(1, "Cerca", -13.5, -71.9801, 10)     # el más cercano, pero no carga 20 kg
        lejos_con_capacidad = Repartidor(2, "Lejos", -13.5, -71.9700, 50)
        mas_lejos = Repartidor(3, "Más lejos", -13.5, -71.9500, 50)
        elegido = asignar_urgente(urgente, [cerca_sin_capacidad, lejos_con_capacidad, mas_lejos])
        self.assertEqual(elegido.id, 2)

    def test_asignar_urgente_devuelve_none_si_nadie_puede(self):
        urgente = pedido(1, peso=100)
        self.assertIsNone(asignar_urgente(urgente, [Repartidor(1, "R", -13.5, -71.98, 10)]))


# ===========================================================================
# 3. Divide y Vencerás
# ===========================================================================
class TestDivideVenceras(unittest.TestCase):
    def setUp(self):
        distancias.usar_grafo(None)

    def repartidores(self, k):
        return [Repartidor(i, f"R{i}", -13.52 - 0.01 * i, -71.98 + 0.02 * i, 10 ** 6)
                for i in range(1, k + 1)]

    def test_cada_pedido_queda_en_una_sola_zona(self):
        pedidos = generar_pedidos(40, semilla=5)
        zonas = dividir_en_zonas(pedidos, self.repartidores(3))
        ids = sorted(p.id for _, lista in zonas for p in lista)
        self.assertEqual(ids, sorted(p.id for p in pedidos))     # ni se pierde ni se repite ninguno

    def test_hay_una_zona_por_repartidor(self):
        for k in (1, 2, 3, 4, 5):
            zonas = dividir_en_zonas(generar_pedidos(30, semilla=k), self.repartidores(k))
            self.assertEqual(len(zonas), k)

    def test_un_repartidor_se_lleva_todo(self):
        pedidos = generar_pedidos(10, semilla=1)
        zonas = dividir_en_zonas(pedidos, self.repartidores(1))
        self.assertEqual(len(zonas[0][1]), 10)

    def test_sin_repartidores(self):
        self.assertEqual(dividir_en_zonas(generar_pedidos(5, semilla=1), []), [])

    def test_las_zonas_estan_separadas(self):
        # Dos grupos claros: 5 pedidos al oeste y 5 al este. Con 2 repartidores cada zona debe ser un grupo
        oeste = [pedido(i, lon=-72.05 + 0.001 * i) for i in range(1, 6)]
        este = [pedido(i, lon=-71.85 + 0.001 * i) for i in range(6, 11)]
        zonas = dividir_en_zonas(oeste + este, self.repartidores(2))
        grupos = sorted(sorted(p.id for p in lista) for _, lista in zonas)
        self.assertEqual(grupos, [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])

    def test_rutas_por_zona(self):
        zonas = dividir_en_zonas(generar_pedidos(20, semilla=2), self.repartidores(2))
        resultado = rutas_por_zona(zonas)
        self.assertEqual(len(resultado), 2)
        for (rep, lista), (rep2, ruta, metros) in zip(zonas, resultado):
            self.assertIs(rep, rep2)
            self.assertEqual(sorted(p.id for p in ruta), sorted(p.id for p in lista))
            self.assertGreaterEqual(metros, 0)


# ===========================================================================
# 4. Programación Dinámica (mochila)
# ===========================================================================
def mochila_fuerza_bruta(pedidos, capacidad):
    """Referencia: prueba TODOS los subconjuntos y se queda con el de mayor valor que cabe."""
    mejor = 0.0
    for k in range(len(pedidos) + 1):
        for combo in itertools.combinations(pedidos, k):
            if sum(p.peso for p in combo) <= capacidad:
                mejor = max(mejor, sum(p.valor for p in combo))
    return mejor


class TestMochila(unittest.TestCase):
    def test_caso_clasico_donde_el_voraz_falla(self):
        # (peso, valor) = (10, 60), (20, 100), (30, 120) con capacidad 50.
        # Por valor/peso un voraz toma 10 y 20 -> 160. Lo óptimo es 20 y 30 -> 220
        pedidos = [pedido(1, peso=10, valor=60), pedido(2, peso=20, valor=100),
                   pedido(3, peso=30, valor=120)]
        elegidos, peso, valor = llenar_mochila(pedidos, 50)
        self.assertEqual(valor, 220)
        self.assertEqual(sorted(p.id for p in elegidos), [2, 3])
        self.assertEqual(peso, 50)

    def test_coincide_con_fuerza_bruta(self):
        for semilla in range(8):
            azar = random.Random(semilla)
            pedidos = [pedido(i, peso=round(azar.uniform(1, 9), 1), valor=azar.randint(10, 100))
                       for i in range(1, 11)]
            capacidad = 25
            _, _, valor = llenar_mochila(pedidos, capacidad)
            self.assertAlmostEqual(valor, mochila_fuerza_bruta(pedidos, capacidad), places=6,
                                   msg=f"semilla {semilla}")

    def test_nunca_se_pasa_de_la_capacidad(self):
        pedidos = generar_pedidos(60, semilla=9)
        for capacidad in (5, 25, 80):
            _, peso, _ = llenar_mochila(pedidos, capacidad)
            self.assertLessEqual(peso, capacidad + 1e-9)

    def test_casos_limite(self):
        self.assertEqual(llenar_mochila([], 50), ([], 0.0, 0.0))                 # sin pedidos
        self.assertEqual(llenar_mochila([pedido(1, peso=5)], 0), ([], 0.0, 0.0))  # capacidad 0
        self.assertEqual(llenar_mochila([pedido(1, peso=5)], 4)[0], [])           # no cabe ni uno

    def test_todo_cabe(self):
        pedidos = [pedido(1, peso=2, valor=5), pedido(2, peso=3, valor=7)]
        elegidos, _, valor = llenar_mochila(pedidos, 100)
        self.assertEqual(len(elegidos), 2)
        self.assertEqual(valor, 12)


# ===========================================================================
# 5. Mapa: A*, distancias por calles y Backtracking
# ===========================================================================
def crear_cuadricula(filas=3, columnas=3):
    """Mapa de juguete: esquinas en cuadrícula, calles de doble sentido.
    Las calles horizontales se llaman 'Fila r' y las verticales 'Columna c'.
    Esquina (r, c) tiene id str(r * columnas + c): en 3x3 va de '0' (arriba izq.) a '8' (abajo der.)."""
    g = Grafo()
    g.limites = {"norte": -13.50, "sur": -13.50 - 0.001 * (filas - 1),
                 "oeste": -71.98, "este": -71.98 + 0.001 * (columnas - 1)}
    g.distritos = [("Cusco", -13.50, -71.98)]
    for r in range(filas):
        for c in range(columnas):
            idx = str(r * columnas + c)
            g.nodos[idx] = (-13.50 - 0.001 * r, -71.98 + 0.001 * c)
            g.calles[idx] = []
    id_arista = 0

    def unir(a, b, nombre):
        nonlocal id_arista
        metros = distancia_recta(*g.nodos[a], *g.nodos[b])
        g.calles[a].append((b, metros, nombre, id_arista))
        g.calles[b].append((a, metros, nombre, id_arista + 1))
        id_arista += 2

    for r in range(filas):
        for c in range(columnas):
            idx = str(r * columnas + c)
            if c + 1 < columnas:
                unir(idx, str(r * columnas + c + 1), f"Fila {r}")
            if r + 1 < filas:
                unir(idx, str((r + 1) * columnas + c), f"Columna {c}")
    g.nombres_calles = sorted({c[2] for lista in g.calles.values() for c in lista})
    return g


def dijkstra(grafo, origen, destino):
    """Referencia sencilla (sin heurística) para comprobar que A* da el mismo resultado."""
    mejor = {origen: 0.0}
    cola = [(0.0, origen)]
    while cola:
        costo, u = heapq.heappop(cola)
        if u == destino:
            return costo
        if costo > mejor.get(u, INF):
            continue
        for v, metros, _n, _i in grafo.vecinos(u):
            if costo + metros < mejor.get(v, INF):
                mejor[v] = costo + metros
                heapq.heappush(cola, (costo + metros, v))
    return INF


def usa_calle(grafo, camino, nombre):
    return any(grafo.nombre_tramo(u, v) == nombre for u, v in zip(camino[:-1], camino[1:]))


class TestMapa(unittest.TestCase):
    def setUp(self):
        distancias.usar_grafo(None)
        self.g = crear_cuadricula()

    def tearDown(self):
        distancias.usar_grafo(None)

    def test_astar_coincide_con_dijkstra_en_todos_los_pares(self):
        for a in self.g.nodos:
            for b in self.g.nodos:
                _, metros = a_estrella(self.g, a, b)
                self.assertAlmostEqual(metros, dijkstra(self.g, a, b), places=6, msg=f"{a}->{b}")

    def test_astar_ruta_valida(self):
        camino, metros = a_estrella(self.g, "0", "8")
        self.assertEqual(camino[0], "0")
        self.assertEqual(camino[-1], "8")
        self.assertEqual(len(camino), 5)                  # 4 tramos: 2 horizontales y 2 verticales

    def test_astar_mismo_origen_y_destino(self):
        self.assertEqual(a_estrella(self.g, "4", "4"), (["4"], 0.0))

    def test_astar_evita_la_calle_cerrada(self):
        # Esquina 0 -> 2 normalmente va por 'Fila 0'. Cerrada, debe bajar por la fila 1
        directo, metros_directo = a_estrella(self.g, "0", "2")
        self.assertTrue(usa_calle(self.g, directo, "Fila 0"))
        self.g.cerrar_calle("Fila 0")
        desvio, metros_desvio = a_estrella(self.g, "0", "2")
        self.assertFalse(usa_calle(self.g, desvio, "Fila 0"))
        self.assertGreater(metros_desvio, metros_directo)

    def test_astar_sin_camino_si_todo_esta_cerrado(self):
        for nombre in self.g.nombres_calles:
            self.g.cerrar_calle(nombre)
        self.assertEqual(a_estrella(self.g, "0", "8"), (None, INF))

    def test_abrir_todas_restaura_el_camino(self):
        self.g.cerrar_calle("Fila 0")
        self.g.abrir_todas()
        camino, _ = a_estrella(self.g, "0", "2")
        self.assertTrue(usa_calle(self.g, camino, "Fila 0"))

    def test_calles_sin_nombre_no_se_cierran_por_nombre(self):
        with self.assertRaises(ValueError):
            self.g.cerrar_calle("Sin nombre")

    def test_distancia_por_calles_y_cache_se_actualiza_al_cerrar(self):
        a = SimpleNamespace(lat=self.g.nodos["0"][0], lon=self.g.nodos["0"][1])
        b = SimpleNamespace(lat=self.g.nodos["2"][0], lon=self.g.nodos["2"][1])
        distancias.usar_grafo(self.g)
        antes = distancia(a, b)
        self.assertAlmostEqual(antes, a_estrella(self.g, "0", "2")[1], places=6)
        self.g.cerrar_calle("Fila 0")                      # la versión del grafo sube y la memoria se vacía
        despues = distancia(a, b)
        self.assertGreater(despues, antes)

    def test_distancia_infinita_si_no_hay_camino(self):
        a = SimpleNamespace(lat=self.g.nodos["0"][0], lon=self.g.nodos["0"][1])
        b = SimpleNamespace(lat=self.g.nodos["8"][0], lon=self.g.nodos["8"][1])
        distancias.usar_grafo(self.g)
        for nombre in self.g.nombres_calles:
            self.g.cerrar_calle(nombre)
        self.assertEqual(distancia(a, b), INF)

    def test_backtracking_encuentra_la_ruta_mas_corta(self):
        # Con poda y memoria (lo normal) busca la ruta más corta y debe coincidir con A*
        r = buscar_rutas(self.g, "0", "8")
        self.assertTrue(r.completo)
        self.assertEqual(r.camino[0], "0")
        self.assertEqual(r.camino[-1], "8")
        self.assertAlmostEqual(r.metros, a_estrella(self.g, "0", "8")[1], places=6)

    def test_backtracking_puro_encuentra_todas_las_rutas(self):
        # Sin poda ni memoria es el backtracking puro: en la cuadrícula de 3x3 hay 12 caminos
        # sin repetir esquinas de la 0 a la 8 (6 que solo avanzan y 6 con algún desvío)
        r = buscar_rutas(self.g, "0", "8", poda=False, memo=False)
        self.assertEqual(r.encontradas, 12)
        self.assertEqual(r.podas, 0)
        self.assertAlmostEqual(r.metros, a_estrella(self.g, "0", "8")[1], places=6)

    def test_backtracking_rutas_ordenadas_y_sin_repetir_esquinas(self):
        r = buscar_rutas(self.g, "0", "8", poda=False, memo=False)
        self.assertGreater(len(r.rutas), 6)
        metros = [m for m, _ in r.rutas]
        self.assertEqual(metros, sorted(metros))                 # de menor a mayor
        for _, camino in r.rutas:
            self.assertEqual(camino[0], "0")
            self.assertEqual(camino[-1], "8")
            self.assertEqual(len(camino), len(set(camino)))      # ninguna esquina se repite

    def test_backtracking_poda_descarta_ramas_y_da_la_misma_ruta(self):
        pura = buscar_rutas(self.g, "0", "8", poda=False, memo=False)
        podada = buscar_rutas(self.g, "0", "8")
        self.assertGreater(podada.podas, 0)
        self.assertLess(podada.visitadas, pura.visitadas)
        self.assertAlmostEqual(podada.metros, pura.metros, places=6)

    def test_backtracking_evita_calles_cerradas(self):
        self.g.cerrar_calle("Fila 0")
        r = buscar_rutas(self.g, "0", "2", tolerancia=1.0)
        self.assertGreaterEqual(r.encontradas, 1)
        for _, camino in r.rutas:
            self.assertFalse(usa_calle(self.g, camino, "Fila 0"))
        self.assertAlmostEqual(r.metros, a_estrella(self.g, "0", "2")[1], places=6)

    def test_backtracking_casos_sin_ruta(self):
        for nombre in self.g.nombres_calles:
            self.g.cerrar_calle(nombre)
        r = buscar_rutas(self.g, "0", "8")
        self.assertIsNone(r.camino)
        self.assertEqual(r.encontradas, 0)
        self.assertIsNone(buscar_rutas(self.g, "0", "no_existe").camino)
        self.assertEqual(buscar_rutas(self.g, "3", "3").metros, 0.0)

    def test_backtracking_se_puede_detener_desde_afuera(self):
        # El botón "Detener" activa un threading.Event; la búsqueda para y avisa que no terminó
        grande = crear_cuadricula(5, 5)
        parar = threading.Event()
        parar.set()
        r = buscar_rutas(grande, "0", "24", poda=False, memo=False, detener=parar)
        self.assertFalse(r.completo)


# ===========================================================================
# 6. Generador de datos de prueba (usado por main.py y el benchmark)
# ===========================================================================
class TestGeneradorDePedidos(unittest.TestCase):
    def test_misma_semilla_mismos_pedidos(self):
        self.assertEqual(generar_pedidos(15, semilla=4), generar_pedidos(15, semilla=4))

    def test_cantidad_ids_y_rangos(self):
        pedidos = generar_pedidos(100, semilla=1)
        self.assertEqual([p.id for p in pedidos], list(range(1, 101)))
        for p in pedidos:
            self.assertIn(p.prioridad, (1, 2, 3))
            self.assertGreater(p.peso, 0)
            self.assertTrue(-13.5919 <= p.lat <= -13.4799 and -72.0704 <= p.lon <= -71.8181)


if __name__ == "__main__":
    unittest.main(verbosity=2)
