"MODELO 2 Daniel - pruebas/benchmark.py"
# pruebas/benchmark.py
# Persona 4 (Daniel): mide el rendimiento de los algoritmos con pedidos aleatorios de
# 10, 50, 100, 500 y 1000 pedidos usando time.perf_counter().
#
# Genera los datos para la parte "Comparación de rendimiento" del informe:
#   Tabla 1: tiempos de ordenación, búsqueda, Greedy, Divide y Vencerás y Mochila (PD)
#   Tabla 2: Mochila exacta (PD) frente a una mochila voraz: ¿cuánto valor se pierde?
#   Tabla 3: Vecino más cercano (Greedy) frente a la ruta óptima por fuerza bruta
#   Tabla 4: Backtracking puro frente a Backtracking con poda y con poda + memoria
#            (4a en cuadrículas armadas en memoria; 4b en el mapa real si existe herramientas/grafo.json)
#
# Ejecutar desde la carpeta del proyecto:   python -m pruebas.benchmark
# Con gráfico (necesita matplotlib):        python -m pruebas.benchmark --grafico

import itertools
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelos import Pedido, Repartidor
from mapa.distancias import distancia, distancia_recta
from mapa.grafo import Grafo
from algoritmos.ordenacion_busqueda import merge_sort, busqueda_binaria
from algoritmos.greedy import vecino_mas_cercano
from algoritmos.divide_venceras import dividir_en_zonas, rutas_por_zona
from algoritmos.mochila import llenar_mochila
from algoritmos.backtracking import buscar_rutas

TAMANOS = (10, 50, 100, 500, 1000)

# Distritos de mapacusco.py (nombre, lat, lon). Se copian aquí para poder generar pedidos
# sin cargar el mapa; si cambian en mapacusco.py hay que cambiarlos también aquí
DISTRITOS = [
    ("Santiago", -13.576680, -71.987841),
    ("Ccorca", -13.581894, -72.060401),
    ("Poroy", -13.499018, -72.040873),
    ("San Jerónimo", -13.525301, -71.869658),
    ("San Sebastián", -13.552615, -71.940278),
    ("Saylla", -13.549021, -71.828137),
    ("Wánchaq", -13.534596, -71.949054),
    ("Cusco", -13.489926, -71.987573),
]

# Área del mapa (la misma que usa pestana_pedidos.py para validar coordenadas)
LAT_MIN, LAT_MAX = -13.5919, -13.4799
LON_MIN, LON_MAX = -72.0704, -71.8181


# ---------------------------------------------------------------------------
# Datos de prueba
# ---------------------------------------------------------------------------
def generar_pedidos(n, semilla=None):
    """Genera `n` pedidos aleatorios cerca de los distritos de Cusco.
    Con la misma `semilla` siempre salen los mismos pedidos (así los resultados se pueden repetir)."""
    azar = random.Random(semilla)
    pedidos = []
    for i in range(1, n + 1):
        distrito, lat0, lon0 = azar.choice(DISTRITOS)
        # Se reparten alrededor del distrito (~1 km) sin salirse del área del mapa
        lat = min(max(azar.gauss(lat0, 0.008), LAT_MIN), LAT_MAX)
        lon = min(max(azar.gauss(lon0, 0.008), LON_MIN), LON_MAX)
        pedidos.append(Pedido(
            id=i, cliente=f"Cliente {i}", lat=lat, lon=lon, sector=distrito,
            prioridad=azar.choices([1, 2, 3], weights=[2, 5, 3])[0],   # pocos urgentes
            peso=round(azar.uniform(0.5, 12), 1),                      # kg
            valor=azar.randint(20, 300)))                              # soles
    return pedidos


def medir(funcion, repeticiones=1):
    """Ejecuta `funcion()` varias veces y devuelve el MEJOR tiempo en milisegundos
    (el mejor tiempo es el menos afectado por lo que haga el computador en ese momento)."""
    mejor = float("inf")
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion()
        mejor = min(mejor, time.perf_counter() - inicio)
    return mejor * 1000


def imprimir_tabla(titulo, columnas, filas):
    print(f"\n{titulo}")
    anchos = [max(len(str(c)), *(len(str(f[i])) for f in filas)) for i, c in enumerate(columnas)]
    print("  ".join(str(c).rjust(a) for c, a in zip(columnas, anchos)))
    print("  ".join("-" * a for a in anchos))
    for fila in filas:
        print("  ".join(str(v).rjust(a) for v, a in zip(fila, anchos)))


# ---------------------------------------------------------------------------
# Tabla 1: tiempos por algoritmo
# ---------------------------------------------------------------------------
def tabla_tiempos():
    repartidor_grande = Repartidor(1, "Prueba", -13.5164, -71.9785, 10 ** 9)   # sin límite de carga
    cuatro = [Repartidor(i, f"R{i}", la, lo, 10 ** 9) for i, (_, la, lo) in
              enumerate(DISTRITOS[:4], start=1)]
    centro = Repartidor(0, "Centro", -13.5164, -71.9785, 0)
    filas = []
    for n in TAMANOS:
        pedidos = generar_pedidos(n, semilla=n)
        rep = 3 if n <= 100 else 1                    # los casos grandes ya son lentos de por sí
        por_id = merge_sort(pedidos, lambda p: p.id)
        ids = [random.Random(n).randint(1, n) for _ in range(1000)]

        t_prioridad = medir(lambda: merge_sort(pedidos, lambda p: (p.prioridad, p.id)), rep)
        t_distancia = medir(lambda: merge_sort(pedidos, lambda p: distancia(centro, p)), rep)
        t_binaria = medir(lambda: [busqueda_binaria(por_id, i) for i in ids], rep)
        t_lineal = medir(lambda: [next((p for p in pedidos if p.id == i), None) for i in ids], rep)
        t_greedy = medir(lambda: vecino_mas_cercano(repartidor_grande, pedidos), rep)
        t_zonas = medir(lambda: rutas_por_zona(dividir_en_zonas(pedidos, cuatro)), rep)
        t_mochila = medir(lambda: llenar_mochila(pedidos, 80), 1)
        filas.append((n, f"{t_prioridad:.2f}", f"{t_distancia:.2f}", f"{t_binaria:.2f}",
                      f"{t_lineal:.2f}", f"{t_greedy:.2f}", f"{t_zonas:.2f}", f"{t_mochila:.2f}"))
    imprimir_tabla("TABLA 1 - Tiempo en ms (búsquedas: 1000 consultas; mochila: capacidad 80 kg)",
                   ("n", "sort prioridad", "sort distancia", "búsq. binaria", "búsq. lineal",
                    "greedy", "div. y venc.", "mochila PD"), filas)
    return filas


# ---------------------------------------------------------------------------
# Tabla 2: mochila exacta (PD) frente a una mochila voraz
# ---------------------------------------------------------------------------
def mochila_voraz(pedidos, capacidad):
    """Mochila voraz: ordena por valor/peso y toma todo lo que quepa. Es rápida pero NO es óptima."""
    carga, valor = 0.0, 0.0
    for p in sorted(pedidos, key=lambda p: p.valor / p.peso, reverse=True):
        if carga + p.peso <= capacidad:
            carga += p.peso
            valor += p.valor
    return valor


def tabla_mochila():
    filas = []
    for n in (10, 20, 50, 100):
        pedidos = generar_pedidos(n, semilla=n)
        capacidad = round(0.3 * sum(p.peso for p in pedidos))     # la mochila lleva ~30% del peso total
        _, _, valor_pd = llenar_mochila(pedidos, capacidad)
        valor_voraz = mochila_voraz(pedidos, capacidad)
        perdida = 100 * (valor_pd - valor_voraz) / valor_pd if valor_pd else 0
        t_pd = medir(lambda: llenar_mochila(pedidos, capacidad), 3)
        t_voraz = medir(lambda: mochila_voraz(pedidos, capacidad), 3)
        filas.append((n, capacidad, f"{valor_pd:.0f}", f"{valor_voraz:.0f}", f"{perdida:.1f}%",
                      f"{t_pd:.2f}", f"{t_voraz:.3f}"))
    imprimir_tabla("TABLA 2 - Mochila: Programación Dinámica (óptima) vs voraz",
                   ("n", "cap. kg", "valor PD", "valor voraz", "se pierde", "t PD ms", "t voraz ms"), filas)
    return filas


# ---------------------------------------------------------------------------
# Tabla 3: vecino más cercano frente a la ruta óptima por fuerza bruta
# ---------------------------------------------------------------------------
def ruta_optima(repartidor, pedidos):
    """Prueba TODOS los órdenes de visita (n! posibilidades) y devuelve los metros del mejor.
    Solo sirve para n pequeño (n=8 son 40 320 órdenes)."""
    mejor = float("inf")
    for orden in itertools.permutations(pedidos):
        metros, actual = 0.0, repartidor
        for p in orden:
            metros += distancia(actual, p)
            actual = p
        mejor = min(mejor, metros)
    return mejor


def tabla_greedy_vs_optimo():
    filas = []
    for n in (5, 6, 7, 8):
        # Pesos de 1 kg para que la capacidad no influya: se compara solo el orden de visita
        pedidos = [Pedido(p.id, p.cliente, p.lat, p.lon, p.sector, p.prioridad, 1.0, p.valor)
                   for p in generar_pedidos(n, semilla=100 + n)]
        rep = Repartidor(1, "Prueba", -13.5164, -71.9785, 10 ** 9)
        _, metros_greedy = vecino_mas_cercano(rep, pedidos)
        t_greedy = medir(lambda: vecino_mas_cercano(rep, pedidos), 3)
        inicio = time.perf_counter()
        metros_optimo = ruta_optima(rep, pedidos)
        t_optimo = (time.perf_counter() - inicio) * 1000
        extra = 100 * (metros_greedy - metros_optimo) / metros_optimo
        filas.append((n, f"{metros_greedy:.0f}", f"{metros_optimo:.0f}", f"{extra:.1f}%",
                      f"{t_greedy:.3f}", f"{t_optimo:.1f}"))
    imprimir_tabla("TABLA 3 - Ruta: Greedy (vecino más cercano) vs óptimo por fuerza bruta",
                   ("n", "greedy m", "óptimo m", "greedy recorre de más", "t greedy ms", "t exhaustivo ms"), filas)
    return filas


# ---------------------------------------------------------------------------
# Tabla 4: Backtracking puro, con poda y con poda + memoria
# ---------------------------------------------------------------------------
def crear_cuadricula(filas=3, columnas=3):
    """Mapa de juguete armado en memoria: esquinas en cuadrícula con calles de doble sentido.
    Las horizontales se llaman 'Fila r' y las verticales 'Columna c'; el costo de cada tramo es
    su distancia de Haversine. La esquina (r, c) tiene id str(r * columnas + c), así que en 3x3
    va de '0' (arriba a la izquierda) a '8' (abajo a la derecha).
    La usan este benchmark y las pruebas unitarias, así no hace falta descargar el mapa real."""
    g = Grafo()
    g.limites = {"norte": -13.50, "sur": -13.50 - 0.001 * (filas - 1),
                 "oeste": -71.98, "este": -71.98 + 0.001 * (columnas - 1)}
    g.distritos = [("Cusco", -13.50, -71.98)]
    for r in range(filas):
        for c in range(columnas):
            idx = str(r * columnas + c)
            g.nodos[idx] = (-13.50 - 0.001 * r, -71.98 + 0.001 * c)
            g.calles[idx] = []
    contador = [0]                                  # contador de ids de tramos

    def unir(a, b, nombre):
        metros = distancia_recta(*g.nodos[a], *g.nodos[b])
        g.calles[a].append((b, metros, nombre, contador[0]))
        g.calles[b].append((a, metros, nombre, contador[0] + 1))
        contador[0] += 2

    for r in range(filas):
        for c in range(columnas):
            idx = str(r * columnas + c)
            if c + 1 < columnas:
                unir(idx, str(r * columnas + c + 1), f"Fila {r}")
            if r + 1 < filas:
                unir(idx, str((r + 1) * columnas + c), f"Columna {c}")
    g.nombres_calles = sorted({t[2] for lista in g.calles.values() for t in lista})
    return g


# Las tres variantes del Backtracking que se comparan (poda, memo)
VARIANTES = (("puro", False, False), ("poda", True, False), ("poda + memoria", True, True))


def tabla_backtracking_cuadriculas():
    """Tabla 4a: de una esquina a la opuesta en cuadrículas de lado 3 a 12.
    El Backtracking puro prueba TODOS los caminos sin repetir esquinas (8 512 en 5x5, más de
    un millón en 6x6), por eso solo se mide hasta 5x5."""
    filas = []
    for lado in (3, 4, 5, 8, 12):
        grafo = crear_cuadricula(lado, lado)
        destino = str(lado * lado - 1)
        fila = [f"{lado}x{lado}", lado * lado]
        for _nombre, poda, memo in VARIANTES:
            if not poda and not memo and lado > 5:
                fila += ["--", "--"]
                continue
            inicio = time.perf_counter()
            r = buscar_rutas(grafo, "0", destino, poda=poda, memo=memo, max_segundos=30)
            ms = (time.perf_counter() - inicio) * 1000
            fila += [r.visitadas, f"{ms:.1f}"]
        filas.append(tuple(fila))
    imprimir_tabla("TABLA 4a - Backtracking en cuadrículas: llamadas recursivas y tiempo (ms)",
                   ("mapa", "esquinas", "puro llam.", "puro ms", "poda llam.", "poda ms",
                    "poda+mem llam.", "poda+mem ms"), filas)
    return filas


def tabla_backtracking_mapa_real(ruta_grafo=None, pares=5):
    """Tabla 4b: pares de esquinas del mapa real a entre 0,5 y 1,5 km (solo si existe grafo.json).
    Cada variante tiene un tope de 3 s; 'completo' dice si terminó antes del tope."""
    carpeta = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_grafo = ruta_grafo or os.path.join(carpeta, "herramientas", "grafo.json")
    if not os.path.exists(ruta_grafo):
        print(f"\nTABLA 4b omitida: no existe {ruta_grafo}")
        return []
    grafo = Grafo()
    grafo.cargar(ruta_grafo)
    azar = random.Random(7)
    ids = list(grafo.nodos)
    filas, intentos = [], 0
    while len(filas) < pares and intentos < 5000:
        intentos += 1
        a, b = azar.choice(ids), azar.choice(ids)
        if not 500 <= distancia_recta(*grafo.nodos[a], *grafo.nodos[b]) <= 1500:
            continue
        fila = [len(filas) + 1]
        for _nombre, poda, memo in VARIANTES:
            inicio = time.perf_counter()
            r = buscar_rutas(grafo, a, b, poda=poda, memo=memo, max_segundos=3)
            ms = (time.perf_counter() - inicio) * 1000
            fila += [r.visitadas, f"{ms:.0f}", "sí" if r.completo else "no"]
            if poda and memo:
                metros, zona = r.metros, r.esquinas_zona
        fila[1:1] = [f"{metros:.0f}", zona]
        filas.append(tuple(fila))
    imprimir_tabla("TABLA 4b - Mapa real: Backtracking puro vs poda vs poda + memoria (tope 3 s)",
                   ("par", "metros", "zona", "puro llam.", "puro ms", "compl.", "poda llam.",
                    "poda ms", "compl.", "p+m llam.", "p+m ms", "compl."), filas)
    return filas


# ---------------------------------------------------------------------------
# Gráfico opcional para el informe
# ---------------------------------------------------------------------------
def graficar(filas, nombre_archivo="benchmark.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nPara el gráfico instala matplotlib:  pip install matplotlib")
        return
    ns = [f[0] for f in filas]
    nombres = ("sort prioridad", "sort distancia", "búsq. binaria", "búsq. lineal",
               "greedy", "div. y venc.", "mochila PD")
    plt.figure(figsize=(8, 5))
    for i, nombre in enumerate(nombres, start=1):
        plt.plot(ns, [float(f[i]) for f in filas], marker="o", label=nombre)
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("n (pedidos)")
    plt.ylabel("tiempo (ms)")
    plt.title("Tiempo de ejecución según el número de pedidos")
    plt.legend()
    plt.grid(True, which="both", alpha=0.3)
    plt.savefig(nombre_archivo, dpi=150, bbox_inches="tight")
    print(f"\nGráfico guardado en {nombre_archivo}")


def ejecutar(con_grafico=False):
    filas = tabla_tiempos()
    tabla_mochila()
    tabla_greedy_vs_optimo()
    tabla_backtracking_cuadriculas()
    tabla_backtracking_mapa_real()
    if con_grafico:
        graficar(filas)


if __name__ == "__main__":
    ejecutar(con_grafico="--grafico" in sys.argv)
