"Daniel - pruebas/test_algoritmos.py"
# pruebas/test_algoritmos.py
# Persona 4 (Daniel): pruebas unitarias (unittest) de todos los algoritmos del proyecto.
#
# Ejecutar desde la carpeta del proyecto:   python -m unittest pruebas.test_algoritmos -v
#
# Cada prueba tiene un caso y un resultado esperado, para copiarlos al informe en la sección
# "Casos y datos de prueba". Las pruebas del mapa NO usan grafo.json: arman cuadrículas
# pequeñas en memoria (crear_cuadricula, definida en pruebas/benchmark.py), así corren rápido
# y en cualquier computador.

import heapq
import itertools
import os
import random
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos import Pedido, Repartidor
from mapa.distancias import distancia, distancia_recta
from algoritmos.ordenacion_busqueda import (
    merge_sort, busqueda_binaria, agrupar_por_sector, normalizar_texto)
from algoritmos.greedy import vecino_mas_cercano, asignar_urgente
from algoritmos.divide_venceras import dividir_en_zonas, rutas_por_zona
from algoritmos.mochila import llenar_mochila
from algoritmos.backtracking import buscar_rutas, zona_por_divide_venceras
from pruebas.benchmark import generar_pedidos, crear_cuadricula

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
# 5. Mapa: distancias, grafo y Backtracking
# ===========================================================================
def dijkstra(grafo, origen, destino):
    """Referencia sencilla para comprobar que el Backtracking encuentra la ruta más corta real."""
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


class TestDistancias(unittest.TestCase):
    def test_un_grado_de_latitud_mide_unos_111_km(self):
        self.assertAlmostEqual(distancia_recta(-13.0, -72.0, -14.0, -72.0), 111195, delta=100)

    def test_es_simetrica_y_cero_entre_el_mismo_punto(self):
        a, b = (-13.5164, -71.9785), (-13.5346, -71.9490)
        self.assertAlmostEqual(distancia_recta(*a, *b), distancia_recta(*b, *a), places=6)
        self.assertEqual(distancia_recta(*a, *a), 0.0)

    def test_distancia_entre_objetos_usa_sus_coordenadas(self):
        p = pedido(1, lat=-13.5, lon=-71.98)
        r = Repartidor(1, "R", -13.51, -71.97, 10)
        self.assertAlmostEqual(distancia(p, r), distancia_recta(-13.5, -71.98, -13.51, -71.97), places=6)


class TestGrafo(unittest.TestCase):
    def setUp(self):
        self.g = crear_cuadricula()

    def test_vecinos_de_una_esquina_y_del_centro(self):
        self.assertEqual(len(self.g.vecinos("0")), 2)      # esquina: 2 calles
        self.assertEqual(len(self.g.vecinos("4")), 4)      # centro: 4 calles

    def test_cerrar_y_abrir_calle_por_nombre(self):
        self.g.cerrar_calle("Fila 0")
        self.assertEqual([v[0] for v in self.g.vecinos("0")], ["3"])      # solo queda bajar
        self.g.abrir_calle("Fila 0")
        self.assertEqual(len(self.g.vecinos("0")), 2)

    def test_cerrar_un_solo_tramo_por_id(self):
        id_tramo = next(v[3] for v in self.g.calles["0"] if v[0] == "1")
        self.g.cerrar_tramo(id_tramo)
        self.assertEqual([v[0] for v in self.g.vecinos("0")], ["3"])
        self.assertIn("0", [v[0] for v in self.g.vecinos("1")])           # la vuelta (otro id) sigue abierta
        self.g.abrir_tramo(id_tramo)
        self.assertEqual(len(self.g.vecinos("0")), 2)

    def test_abrir_todas(self):
        self.g.cerrar_calle("Fila 0")
        self.g.cerrar_calle("Columna 1")
        self.g.abrir_todas()
        self.assertEqual(len(self.g.vecinos("0")), 2)
        self.assertEqual(len(self.g.vecinos("4")), 4)

    def test_la_version_sube_en_cada_cambio(self):
        v0 = self.g.version
        self.g.cerrar_calle("Fila 0")
        self.g.abrir_calle("Fila 0")
        self.g.abrir_todas()
        self.assertEqual(self.g.version, v0 + 3)

    def test_calles_sin_nombre_no_se_cierran_por_nombre(self):
        with self.assertRaises(ValueError):
            self.g.cerrar_calle("Sin nombre")

    def test_esquina_mas_cercana(self):
        lat, lon = self.g.nodos["4"]
        self.assertEqual(self.g.esquina_mas_cercana(lat + 0.0001, lon - 0.0001), "4")

    def test_sector_de_elige_el_distrito_mas_cercano(self):
        self.g.distritos = [("Norte", -13.50, -71.98), ("Sur", -13.60, -71.90)]
        self.assertEqual(self.g.sector_de(-13.501, -71.979), "Norte")
        self.assertEqual(self.g.sector_de(-13.59, -71.91), "Sur")

    def test_nombre_del_tramo(self):
        self.assertEqual(self.g.nombre_tramo("0", "1"), "Fila 0")
        self.assertEqual(self.g.nombre_tramo("0", "3"), "Columna 0")
        self.assertEqual(self.g.nombre_tramo("0", "8"), "Sin nombre")     # no están unidas


class TestBacktracking(unittest.TestCase):
    def setUp(self):
        self.g = crear_cuadricula()

    def test_ruta_mas_corta_coincide_con_dijkstra_en_todos_los_pares(self):
        for a in self.g.nodos:
            for b in self.g.nodos:
                if a == b:
                    continue
                r = buscar_rutas(self.g, a, b)
                self.assertAlmostEqual(r.metros, dijkstra(self.g, a, b), places=6, msg=f"{a}->{b}")

    def test_la_ruta_empieza_y_termina_donde_debe(self):
        r = buscar_rutas(self.g, "0", "8")
        self.assertEqual(r.camino[0], "0")
        self.assertEqual(r.camino[-1], "8")
        self.assertEqual(len(r.camino), 5)                 # 4 tramos: 2 horizontales y 2 verticales
        self.assertTrue(r.completo)

    def test_evita_la_calle_cerrada(self):
        # De "0" a "2" lo más corto es por 'Fila 0'. Cerrada, hay que bajar por la fila 1
        directo = buscar_rutas(self.g, "0", "2")
        self.assertTrue(usa_calle(self.g, directo.camino, "Fila 0"))
        self.g.cerrar_calle("Fila 0")
        desvio = buscar_rutas(self.g, "0", "2")
        self.assertFalse(usa_calle(self.g, desvio.camino, "Fila 0"))
        self.assertGreater(desvio.metros, directo.metros)
        self.assertAlmostEqual(desvio.metros, dijkstra(self.g, "0", "2"), places=6)

    def test_sin_ruta_si_todo_esta_cerrado(self):
        for nombre in self.g.nombres_calles:
            self.g.cerrar_calle(nombre)
        r = buscar_rutas(self.g, "0", "8")
        self.assertIsNone(r.camino)
        self.assertEqual(r.rutas, [])
        self.assertEqual(r.mensaje, "No hay ruta posible con las calles cerradas.")

    def test_origen_o_destino_inexistente(self):
        r = buscar_rutas(self.g, "0", "no_existe")
        self.assertIsNone(r.camino)
        self.assertEqual(r.mensaje, "El origen o el destino no está en el mapa.")

    def test_mismo_origen_y_destino(self):
        r = buscar_rutas(self.g, "3", "3")
        self.assertEqual((r.camino, r.metros), (["3"], 0.0))

    def test_puro_encuentra_todas_las_rutas_sin_repetir_esquinas(self):
        # Caminos simples entre esquinas opuestas: 12 en 3x3 y 184 en 4x4 (valores conocidos)
        r3 = buscar_rutas(self.g, "0", "8", poda=False, memo=False)
        self.assertEqual(r3.encontradas, 12)
        r4 = buscar_rutas(crear_cuadricula(4, 4), "0", "15", poda=False, memo=False)
        self.assertEqual(r4.encontradas, 184)

    def test_rutas_ordenadas_y_validas(self):
        r = buscar_rutas(self.g, "0", "8", poda=False, memo=False)
        metros = [m for m, _ in r.rutas]
        self.assertEqual(len(r.rutas), 12)
        self.assertEqual(metros, sorted(metros))           # de menor a mayor
        self.assertAlmostEqual(r.metros, metros[0], places=9)
        for _, camino in r.rutas:
            self.assertEqual((camino[0], camino[-1]), ("0", "8"))
            self.assertEqual(len(camino), len(set(camino)))    # ninguna esquina se repite

    def test_poda_y_memoria_reducen_las_llamadas_sin_perder_la_mejor_ruta(self):
        g5 = crear_cuadricula(5, 5)
        puro = buscar_rutas(g5, "0", "24", poda=False, memo=False)
        poda = buscar_rutas(g5, "0", "24", poda=True, memo=False)
        ambas = buscar_rutas(g5, "0", "24", poda=True, memo=True)
        self.assertGreater(puro.visitadas, poda.visitadas)
        self.assertGreater(poda.visitadas, ambas.visitadas)
        self.assertAlmostEqual(puro.metros, poda.metros, places=6)
        self.assertAlmostEqual(puro.metros, ambas.metros, places=6)

    def test_tolerancia_agrega_alternativas(self):
        g4 = crear_cuadricula(4, 4)
        solo_corta = buscar_rutas(g4, "0", "15", tolerancia=0.0)
        con_alternativas = buscar_rutas(g4, "0", "15", tolerancia=0.6)
        self.assertGreater(len(con_alternativas.rutas), len(solo_corta.rutas))
        limite = con_alternativas.metros * 1.6 + 1e-6
        self.assertTrue(all(m <= limite for m, _ in con_alternativas.rutas))

    def test_detener_corta_la_busqueda(self):
        parar = threading.Event()
        parar.set()                                        # el botón Detener ya estaba pulsado
        r = buscar_rutas(crear_cuadricula(5, 5), "0", "24", poda=False, memo=False, detener=parar)
        self.assertFalse(r.completo)

    def test_tope_de_tiempo_corta_la_busqueda(self):
        r = buscar_rutas(crear_cuadricula(5, 5), "0", "24", poda=False, memo=False, max_segundos=1e-9)
        self.assertFalse(r.completo)

    def test_zona_de_divide_y_venceras_contiene_origen_y_destino(self):
        g = crear_cuadricula(10, 10)
        zona = zona_por_divide_venceras(g, "11", "33", max_esquinas=30)
        self.assertIn("11", zona)
        self.assertIn("33", zona)
        self.assertLess(len(zona), 100)                    # se descartó parte del mapa

    def test_busqueda_en_zona_reducida_da_la_ruta_correcta(self):
        g = crear_cuadricula(10, 10)
        r = buscar_rutas(g, "11", "33", max_esquinas=30)
        self.assertLess(r.esquinas_zona, 100)
        self.assertAlmostEqual(r.metros, dijkstra(g, "11", "33"), places=6)

    def test_amplia_la_zona_si_dentro_no_hay_ruta(self):
        # Con las filas 0 a 5 cerradas, ir de "0" a "9" obliga a bajar hasta la fila 6. La zona inicial
        # (filas 0 a 5) no la incluye, así que no hay ruta ahí: la zona se amplía y entonces se encuentra
        g = crear_cuadricula(10, 10)
        for fila in range(6):
            g.cerrar_calle(f"Fila {fila}")
        r = buscar_rutas(g, "0", "9", max_esquinas=20)
        self.assertIsNotNone(r.camino)
        self.assertGreaterEqual(r.ampliaciones, 1)
        self.assertAlmostEqual(r.metros, dijkstra(g, "0", "9"), places=6)


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
