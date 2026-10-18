"FAUSTO: MODELO 2 - algoritmos/backtracking.py"
# backtracking.py
# Rutas con restricciones: busca rutas de un origen a un destino evitando las calles cerradas (grafo.vecinos() ya las salta) y se queda con la más corta.

# El Backtracking recorre todos los caminos posibles sin pasar dos veces por la misma
# esquina, y eso crece de forma exponencial con el tamaño del mapa. Para que sea viable
# se combina con otras dos técnicas del curso:
#  1. Divide y Vencerás: el mapa se parte por la mitad (eje de mayor dispersión, igual que en divide_venceras.py) y se descarta la mitad que no contiene al origen ni al
#  destino. Se repite hasta que la zona tenga pocas esquinas. El Backtracking solo trabaja dentro de esa zona.
#  2. Poda (ramificación y poda): se abandona una rama si lo recorrido más la distancia en línea recta que falta hasta el destino ya supera la mejor ruta encontrada.
#  3. Programación Dinámica (memoria de estados): se guarda el menor costo con el que se ha llegado a cada esquina; si otra rama llega a la misma esquina con más costo,
#  se descarta.
# Con poda=False y memo=False se obtiene el Backtracking puro (todas las rutas de la zona), útil para comparar tiempos en el informe.
#
# tolerancia=0 busca solo la ruta más corta (la memoria la hace muy rápida).
# Si en la zona no hay ruta (calles cerradas o una zona demasiado chica), la zona se amplía al doble y se vuelve a buscar, hasta 3 veces.
# El tiempo máximo es opcional (None o 0 = sin tope) y la búsqueda se puede cortar desde afuera con un threading.Event (botón "Detener").

import math  # Trae cos y radians, que se usan para convertir el margen de metros a grados
import sys   # Para subir el límite de recursión
import time  # Para medir cuántos segundos lleva la búsqueda

from mapa.distancias import distancia_recta

# Se usa el merge_sort del equipo (Divide y Vencerás); si ese archivo aún no existe, se usa esta copia de respaldo
try:
    from algoritmos.ordenacion_busqueda import merge_sort
except ImportError:
    def merge_sort(lista, clave):
        # Copia de respaldo: ordena de menor a mayor sin modificar la lista recibida
        if len(lista) <= 1:  # Caso base: con 0 o 1 elementos ya está ordenada
            return list(lista)
        medio = len(lista) // 2
        izq = merge_sort(lista[:medio], clave)  # Ordena cada mitad por separado
        der = merge_sort(lista[medio:], clave)
        mezcla, i, j = [], 0, 0  # i y j: posición actual en cada mitad
        while i < len(izq) and j < len(der):  # Mezcla: siempre toma el menor de los dos frentes
            if clave(izq[i]) <= clave(der[j]):
                mezcla.append(izq[i])
                i += 1
            else:
                mezcla.append(der[j])
                j += 1
        return mezcla + izq[i:] + der[j:]  # Una mitad se agota antes; lo que sobra de la otra ya está ordenado

INF = float("inf")            # Infinito: "todavía no hay ruta", valor inicial de la mejor distancia
METROS_POR_GRADO = 111320     # metros que mide un grado de latitud
GUARDAR = 30                  # cuántas rutas (las más cortas) se conservan para mostrar


# Guarda todo lo que devuelve la búsqueda, para que la interfaz pueda mostrarlo
class ResultadoBacktracking:
    def __init__(self):
        self.camino = None         # mejor ruta: lista de esquinas
        self.metros = INF
        self.rutas = []            # mejores rutas reunidas: (metros, camino), de menor a mayor
        self.encontradas = 0       # cantidad de rutas completas que se encontraron
        self.podas = 0             # ramas descartadas por la poda o por la memoria
        self.visitadas = 0         # llamadas recursivas
        self.completo = True       # False si se detuvo antes de terminar
        self.mensaje = ""
        self.esquinas_zona = 0     # esquinas de la zona donde se buscó
        self.ampliaciones = 0      # veces que hubo que ampliar la zona
        self.segundos = 0.0


# ----------------------------------------------------------------------
# DIVIDIR EL MAPA EN UNA ZONA
# ----------------------------------------------------------------------
# Esta función reduce el mapa a una zona pequeña que contiene al origen y al destino, para que el Backtracking no explore toda la ciudad
def zona_por_divide_venceras(grafo, origen, destino, max_esquinas, margen=150):
    # Devuelve la lista de esquinas de la zona que contiene al origen y al destino.
    #   DIVIDIR : se elige el eje (latitud o longitud) con mayor dispersión, se ordenan las
    #             esquinas por ese eje con merge_sort y se cortan por la mitad.
    #   VENCER  : caso base = la zona ya tiene max_esquinas o menos esquinas.
    #   COMBINAR: no hay nada que combinar; solo se sigue con la mitad que sirve.
    # Si el origen y el destino quedan en mitades distintas, se conserva la franja entre
    # los dos. A cada zona se le agrega una banda de `margen` metros pegada al corte, para
    # que la ruta pueda rodear un poco.
    # Costo: T(n) = T(n/2) + O(n log n) = O(n log n)
    lat_ref = grafo.nodos[origen][0]  # Latitud del origen, referencia para convertir metros a grados de longitud
    banda = [margen / METROS_POR_GRADO,
             margen / (METROS_POR_GRADO * math.cos(math.radians(lat_ref)))]  # Margen en grados: [latitud, longitud]. En longitud se divide entre cos porque un grado mide menos metros lejos del ecuador

    # Función recursiva: en cada llamada se queda con la parte del mapa que sirve, hasta que cabe en max_esquinas
    def dividir(ids):
        if len(ids) <= max_esquinas:  # Caso base: la zona ya es lo bastante pequeña
            return ids

        lats = [grafo.nodos[e][0] for e in ids]
        lons = [grafo.nodos[e][1] for e in ids]
        eje = 0 if (max(lats) - min(lats)) >= (max(lons) - min(lons)) else 1  # 0 = latitud, 1 = longitud; se corta por donde las esquinas están más dispersas
        valor = lambda e: grafo.nodos[e][eje]  # Coordenada de la esquina e en el eje elegido

        ordenadas = merge_sort(ids, valor)  # Esquinas ordenadas de menor a mayor en ese eje
        mitad = len(ordenadas) // 2
        izquierda, derecha = ordenadas[:mitad], ordenadas[mitad:]
        corte = valor(ordenadas[mitad])  # Posición de la línea que separa las dos mitades
        en_izquierda = set(izquierda)  # Conjunto para saber rápido si una esquina está en la mitad izquierda

        # Se decide con qué parte seguir según dónde caen el origen y el destino
        if origen in en_izquierda and destino in en_izquierda:  # Ambos a la izquierda: se descarta la derecha (menos la banda pegada al corte)
            nueva = izquierda + [e for e in derecha if valor(e) <= corte + banda[eje]]
        elif origen not in en_izquierda and destino not in en_izquierda:  # Ambos a la derecha: se descarta la izquierda (menos la banda)
            nueva = derecha + [e for e in izquierda if valor(e) >= corte - banda[eje]]
        else:  # Uno en cada mitad: se conserva solo la franja que va del uno al otro
            desde = min(valor(origen), valor(destino)) - banda[eje]
            hasta = max(valor(origen), valor(destino)) + banda[eje]
            nueva = [e for e in ordenadas if desde <= valor(e) <= hasta]

        if len(nueva) >= len(ids):     # ya no se puede achicar más
            return ids  # Evita repetir la recursión sin fin
        return dividir(nueva)

    return dividir(list(grafo.nodos))  # Arranca con todas las esquinas del mapa


# ----------------------------------------------------------------------
# BACKTRACKING
# ----------------------------------------------------------------------
# Busca la ruta más corta de origen a destino dentro de una zona del mapa, con poda y memoria para que sea rápida
def buscar_rutas(grafo, origen, destino, max_esquinas=150, margen=150, tolerancia=0.0,
                 max_segundos=300, poda=True, memo=True, detener=None):
    # detener: un threading.Event; si se activa, la búsqueda para y devuelve lo reunido.
    resultado = ResultadoBacktracking()

    # Casos que no necesitan buscar nada
    if origen not in grafo.nodos or destino not in grafo.nodos:  # Evita un KeyError más abajo
        resultado.mensaje = "El origen o el destino no está en el mapa."
        return resultado
    if origen == destino:  # La ruta es solo esa esquina, 0 metros
        resultado.camino, resultado.metros = [origen], 0.0
        resultado.rutas = [(0.0, [origen])]
        resultado.encontradas = 1
        resultado.mensaje = "El origen y el destino son la misma esquina."
        return resultado

    # La recursión puede ser profunda (una esquina por nivel)
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))  # Python corta en 1000 niveles por defecto; solo se sube, nunca se baja

    # Datos con los que trabaja la búsqueda
    inicio = time.time()  # Para saber cuántos segundos lleva
    limite_tiempo = inicio + max_segundos if max_segundos else None  # Con None o 0 no hay tope de tiempo
    lat_d, lon_d = grafo.nodos[destino]  # Coordenadas del destino, para la línea recta que falta
    parada = ""          # "tiempo", "usuario" o "" si la búsqueda terminó sola
    rutas = []           # Rutas completas encontradas: (metros, camino)
    mejor = INF          # Metros de la mejor ruta encontrada hasta ahora

    # Cada intento busca en una zona; si no hay ruta, el siguiente intento usa una zona más grande
    for intento in range(4):
        zona = zona_por_divide_venceras(grafo, origen, destino, max_esquinas * 2 ** intento, margen)  # Cada intento duplica el tamaño máximo de la zona
        en_zona = set(zona)  # Conjunto para saber rápido si una esquina está dentro de la zona
        resultado.esquinas_zona = len(zona)
        resultado.ampliaciones = intento

        # Distancia en línea recta de cada esquina de la zona hasta el destino
        falta = {e: distancia_recta(grafo.nodos[e][0], grafo.nodos[e][1], lat_d, lon_d) for e in zona}  # Se calcula una vez por esquina, no en cada llamada recursiva

        # Cada intento empieza de cero
        costo = {origen: 0.0}      # memoria: menor costo con el que se llegó a cada esquina
        camino = [origen]          # Camino que se está probando ahora
        visitado = {origen}        # Esquinas del camino actual; evita dar vueltas en círculo
        rutas = []
        mejor = INF
        parada = ""

        # ------------------------ NUCLEO DEL BACKTRACKING ------------------------
        # Función recursiva: prueba seguir por cada calle desde "actual"; si no sirve, retrocede
        def explorar(actual, metros):
            nonlocal mejor, parada  # Se reasignan aquí; sin nonlocal serían variables nuevas (rutas solo se modifica con append, no hace falta)
            if parada:  # Cuando alguna llamada detecta un tope o el botón Detener, las siguientes regresan sin explorar
                return
            resultado.visitadas += 1  # Cada entrada a explorar() cuenta como una llamada recursiva
            # Revisar el tiempo y el botón Detener cada 1000 llamadas para no frenar la búsqueda
            if resultado.visitadas % 1000 == 0:
                if detener is not None and detener.is_set():  # is_set() es True si el usuario pulsó Detener
                    parada = "usuario"
                    return
                if limite_tiempo is not None and time.time() > limite_tiempo:
                    parada = "tiempo"
                    return

            # Caso base: se llegó al destino, se guarda una copia de la ruta
            if actual == destino:
                resultado.encontradas += 1
                rutas.append((metros, list(camino)))  # list(camino) es una copia; el original sigue cambiando al retroceder
                if len(rutas) > GUARDAR * 4:      # se dejan solo las más cortas
                    rutas.sort(key=lambda r: r[0])
                    del rutas[GUARDAR:]  # Evita que la lista crezca sin límite
                if metros < mejor:  # Actualiza la mejor distancia, que es la que usa la poda
                    mejor = metros
                return

            # Vecinos permitidos dentro de la zona; con poda se prueban primero los más prometedores
            opciones = []
            for vecino, tramo, _nombre, _id in grafo.vecinos(actual):
                if vecino in en_zona and vecino not in visitado:  # Debe estar en la zona y no repetirse en este camino (no dar vueltas en círculo)
                    opciones.append((tramo + falta[vecino], vecino, tramo))  # Lo mínimo que costaría pasar por este vecino hasta el destino
            if poda:
                opciones.sort()  # Los más prometedores primero, así la mejor ruta aparece antes y la poda descarta más

            for minimo, vecino, tramo in opciones:
                nuevo = metros + tramo  # Metros recorridos si se avanza a este vecino
                # -------------------- PODA: ni en el mejor caso esta rama entra en el límite --------------------
                if poda and metros + minimo > mejor * (1 + tolerancia):  # Lo recorrido + lo mínimo que falta ya pasa la mejor ruta
                    resultado.podas += 1
                    continue
                # Memoria: otra rama ya llegó a esta esquina con bastante menos costo
                if memo:
                    if nuevo > costo.get(vecino, INF) * (1 + tolerancia):  # Llegar aquí por esta rama cuesta más que por otra: no puede dar una ruta mejor
                        resultado.podas += 1
                        continue
                    if nuevo < costo.get(vecino, INF):  # Es el nuevo menor costo para esta esquina: se anota
                        costo[vecino] = nuevo
                camino.append(vecino)         # avanzar
                visitado.add(vecino)
                explorar(vecino, nuevo)
                camino.pop()                  # ----------- RETROCEDER: elimina la última esquina del recorrido -----------
                visitado.discard(vecino)      # Se libera la esquina para que otros caminos puedan usarla

        explorar(origen, 0.0)

        if rutas or parada:
            break            # hay ruta, o se detuvo la búsqueda: no se amplía la zona

    # Selección final: la más corta de todas las rutas reunidas
    rutas.sort(key=lambda r: r[0])  # Ordena por metros
    if poda and rutas:  # Con poda pueden quedar rutas guardadas antes de conocer la mejor; se descartan las que pasan la tolerancia
        rutas = [r for r in rutas if r[0] <= rutas[0][0] * (1 + tolerancia)]
    resultado.rutas = rutas[:GUARDAR]
    resultado.segundos = time.time() - inicio
    resultado.completo = not parada  # Completo = terminó sola, sin tope de tiempo ni botón Detener

    # No se encontró ninguna ruta: el mensaje depende del motivo
    if not rutas:
        if parada == "usuario":
            resultado.mensaje = "Búsqueda detenida antes de encontrar una ruta."
        elif parada == "tiempo":
            resultado.mensaje = "Se acabó el tiempo antes de encontrar una ruta."
        else:
            resultado.mensaje = "No hay ruta posible con las calles cerradas."
        return resultado

    resultado.metros, resultado.camino = resultado.rutas[0]  # La primera es la más corta
    # Mensaje según por qué terminó la búsqueda
    if parada == "usuario":
        resultado.mensaje = "Búsqueda detenida: puede haber rutas más cortas."
    elif parada == "tiempo":
        resultado.mensaje = "Se acabó el tiempo: puede haber rutas más cortas."
    elif resultado.ampliaciones:
        resultado.mensaje = f"Búsqueda completa (la zona se amplió {resultado.ampliaciones} vez/veces)."
    else:
        resultado.mensaje = "Búsqueda completa en la zona."
    return resultado
