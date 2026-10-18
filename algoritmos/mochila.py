# algoritmos/mochila.py
# Programación Dinámica: problema de la mochila 0/1 para cargar al repartidor.

import math


def _a_enteros(pedidos, capacidad):
    """La tabla de PD se indexa por peso, así que los pesos deben ser enteros.
    Como los pesos están en kg y pueden tener decimales (2.5 kg), se multiplican
    por un factor (1, 10 o 100) hasta que queden exactos.
    Si ni así son exactos, se usa factor 100 redondeando el peso hacia ARRIBA y la
    capacidad hacia ABAJO: puede perder algo de óptimo, pero nunca se pasa del peso.
    Devuelve (pesos_enteros, capacidad_entera)."""
    for factor in (1, 10, 100):
        exactos = abs(capacidad * factor - round(capacidad * factor)) < 1e-9
        for p in pedidos:
            if abs(p.peso * factor - round(p.peso * factor)) > 1e-9:
                exactos = False
                break
        if exactos:
            return ([int(round(p.peso * factor)) for p in pedidos],
                    int(round(capacidad * factor)))

    factor = 100
    # Protección de memoria: si la tabla saldría enorme, se usa kg enteros
    if (len(pedidos) + 1) * (capacidad * factor + 1) > 3_000_000:
        factor = 1
    pesos = [int(math.ceil(p.peso * factor - 1e-9)) for p in pedidos]
    return pesos, int(math.floor(capacidad * factor + 1e-9))


def llenar_mochila(pedidos, capacidad):
    """Elige los pedidos que maximizan el valor total sin pasar de `capacidad` (kg).

    dp[i][w] = mayor valor usando solo los primeros i pedidos con capacidad w.
        dp[i][w] = dp[i-1][w]                                   (no lo llevo)
        dp[i][w] = max(dp[i-1][w], valor_i + dp[i-1][w - peso_i])  (si cabe)

    Se arma una tabla de (n+1) filas por (capacidad+1) columnas, empezando en
    ceros, y luego se RECONSTRUYE subiendo fila por fila desde dp[n][capacidad]:
    si dp[i][w] != dp[i-1][w], el pedido i fue elegido.

    Devuelve (lista_elegida, peso_total, valor_total).
    Costo: tiempo O(n * W) y espacio O(n * W)  (W = capacidad en unidades enteras).
    """
    n = len(pedidos)
    if n == 0 or capacidad <= 0:
        return [], 0.0, 0.0

    pesos, cap = _a_enteros(pedidos, capacidad)

    # Tabla (n+1) x (cap+1) en ceros
    dp = [[0.0] * (cap + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        peso_i = pesos[i - 1]
        valor_i = pedidos[i - 1].valor
        fila_prev = dp[i - 1]
        fila = dp[i]
        for w in range(cap + 1):
            fila[w] = fila_prev[w]                        # no llevarlo
            if peso_i <= w:
                con_pedido = valor_i + fila_prev[w - peso_i]
                if con_pedido > fila[w]:                  # llevarlo
                    fila[w] = con_pedido

    # Reconstrucción: subir fila por fila
    elegidos = []
    w = cap
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            elegidos.append(pedidos[i - 1])
            w -= pesos[i - 1]
    elegidos.reverse()                                    # volver al orden original

    peso_total = 0.0
    valor_total = 0.0
    for p in elegidos:
        peso_total += p.peso
        valor_total += p.valor
    return elegidos, peso_total, valor_total
