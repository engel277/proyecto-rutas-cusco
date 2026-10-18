"FAUSTO: MODELO 2 - gui/pestaña_rutas.py"
# pestaña_rutas.py
# Pestaña "Rutas": Busca con Backtracking las rutas entre un origen y un destino, deja cerrar calles y dibuja el resultado en el mapa.
# Qué necesita de la ventana principal (app):
#   app.grafo   -> El Grafo cargado
#   app.canvas  -> Con dibujar_ruta(puntos, color) y limpiar_rutas(); puntos es una lista de (lat, lon)
# Para elegir origen y destino con un clic en el mapa, el canvas debe llamar a pestaña.al_hacer_clic(lat, lon); devuelve True si la pestaña usó el clic.

import queue      # Cola para pasar el resultado del hilo a la ventana
import threading  # Para correr la búsqueda sin congelar la ventana
import tkinter as tk
from tkinter import messagebox, ttk

from algoritmos.backtracking import buscar_rutas

COLOR_ELEGIDA = "#d62728"   # Ruta seleccionada en la tabla
COLOR_OTRAS = "#9e9e9e"     # Alternativas
MAX_ALTERNATIVAS = 5        # Cuántas alternativas se dibujan junto a la elegida


# Clase de la pestaña: guarda el estado de la búsqueda y contiene todos sus botones y listas
class PestañaRutas(ttk.Frame):
    # Guarda las referencias a la app y al grafo, crea las variables de estado y arma la pantalla
    def __init__(self, padre, app):
        super().__init__(padre)  # Inicializa el Frame de tkinter
        self.app = app
        self.grafo = app.grafo
        self.cola = queue.Queue()      # Aquí deja el hilo su resultado
        self.resultado = None          # Último ResultadoBacktracking
        self.clic_para = None          # "Origen", "destino" o None
        self.buscando = False          # True mientras corre el hilo; evita dos búsquedas a la vez
        self.detener = threading.Event()   # Bandera compartida con el hilo: el botón Detener la activa y el Backtracking la consulta para parar la búsqueda
        self.calles_filtradas = []     # Nombres que muestra la lista de calles
        self.nombres_ruta = []         # Nombres de la lista "calles de la ruta"
        self.armar()
        self.filtrar_calles()  # Llena la lista de calles por primera vez (sin filtro)

    # ------------------------------------------------------------------
    # Construcción de la pestaña
    # ------------------------------------------------------------------
    # Crea y coloca todos los elementos visuales: panel izquierdo (datos, búsqueda y calles) y panel derecho (resultados)
    def armar(self):
        self.columnconfigure(1, weight=1)  # La columna derecha se estira cuando se agranda la ventana
        self.rowconfigure(0, weight=1)

        izq = ttk.Frame(self, padding=6)
        izq.grid(row=0, column=0, sticky="ns")
        der = ttk.Frame(self, padding=6)
        der.grid(row=0, column=1, sticky="nsew")
        der.columnconfigure(0, weight=1)

        # --- Origen y destino: lista de distritos + latitud y longitud editables ---
        nombres = [d[0] for d in self.grafo.distritos]  # Solo los nombres, para la lista desplegable
        self.combo_origen, self.lat_origen, self.lon_origen = self.crear_punto(izq, "Origen", nombres, "origen", 0)
        self.combo_destino, self.lat_destino, self.lon_destino = self.crear_punto(izq, "Destino", nombres, "destino", 1)

        # --- Opciones de la búsqueda: el usuario elige cuánto puede tardar y si quiere alternativas ---
        opc = ttk.LabelFrame(izq, text="Búsqueda", padding=6)
        opc.grid(row=2, column=0, sticky="ew", pady=3)
        ttk.Label(opc, text="Tiempo máximo (s, 0 = sin tope):").grid(row=0, column=0, sticky="w")
        self.entrada_tiempo = ttk.Entry(opc, width=7)
        self.entrada_tiempo.insert(0, "300")  # Valor por defecto: 5 minutos
        self.entrada_tiempo.grid(row=0, column=1, sticky="e")
        ttk.Label(opc, text="Alternativas hasta (% más largas):").grid(row=1, column=0, sticky="w")
        self.entrada_tolerancia = ttk.Entry(opc, width=7)
        self.entrada_tolerancia.insert(0, "0")  # 0 = solo la ruta más corta, sin alternativas
        self.entrada_tolerancia.grid(row=1, column=1, sticky="e")

        self.boton_buscar = ttk.Button(izq, text="Buscar rutas", command=self.buscar)
        self.boton_buscar.grid(row=3, column=0, sticky="ew", pady=(6, 2))
        self.boton_detener = ttk.Button(izq, text="Detener", command=self.detener_busqueda, state="disabled")  # Empieza desactivado: solo tiene sentido mientras se busca
        self.boton_detener.grid(row=4, column=0, sticky="ew", pady=2)
        self.estado = ttk.Label(izq, text="", wraplength=260)  # Mensajes cortos para el usuario; wraplength parte el texto largo en líneas
        self.estado.grid(row=5, column=0, sticky="w")

        # --- Calles cerradas ---
        marco = ttk.LabelFrame(izq, text="Calles cerradas", padding=6)
        marco.grid(row=6, column=0, sticky="ew", pady=6)
        self.filtro = tk.StringVar()
        self.filtro.trace_add("write", lambda *args: self.filtrar_calles())  # Cada vez que se escribe en el cuadro, se vuelve a filtrar la lista (tkinter pasa 3 argumentos que aquí no se usan)
        ttk.Label(marco, text="Buscar calle:").grid(row=0, column=0, sticky="w")
        ttk.Entry(marco, textvariable=self.filtro, width=30).grid(row=1, column=0, columnspan=2, sticky="ew")
        self.lista_calles = tk.Listbox(marco, height=7, width=34, selectmode="extended", exportselection=False)  # extended = varias selecciones; exportselection=False evita que se pierda la selección al usar otra lista
        self.lista_calles.grid(row=2, column=0, columnspan=2, sticky="ew", pady=3)
        ttk.Button(marco, text="Cerrar seleccionadas", command=self.cerrar_seleccionadas).grid(row=3, column=0, sticky="ew")
        ttk.Label(marco, text="Cerradas:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.lista_cerradas = tk.Listbox(marco, height=4, width=34, selectmode="extended", exportselection=False)
        self.lista_cerradas.grid(row=5, column=0, columnspan=2, sticky="ew", pady=3)
        ttk.Button(marco, text="Abrir seleccionadas", command=self.abrir_seleccionadas).grid(row=6, column=0, sticky="ew")
        ttk.Button(marco, text="Abrir todas", command=self.abrir_todas).grid(row=6, column=1, sticky="ew")

        # --- Resultados ---
        self.resumen = tk.Text(der, height=8, width=60, wrap="word", state="disabled")  # disabled = el usuario no puede escribir; solo se habilita al actualizar el texto
        self.resumen.grid(row=0, column=0, sticky="ew")

        ttk.Label(der, text="Rutas encontradas (elige una para verla en el mapa):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.tabla = ttk.Treeview(der, columns=("n", "metros"), show="headings", height=7)  # show="headings" oculta la columna de árbol, queda como tabla simple
        self.tabla.heading("n", text="Ruta")
        self.tabla.heading("metros", text="Metros")
        self.tabla.column("n", width=70, anchor="center")
        self.tabla.column("metros", width=110, anchor="center")
        self.tabla.grid(row=2, column=0, sticky="ew")
        self.tabla.bind("<<TreeviewSelect>>", self.al_elegir_ruta)  # Al elegir una fila se dibuja esa ruta

        ttk.Label(der, text="Calles de la ruta elegida:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.lista_ruta = tk.Listbox(der, height=7, width=60, selectmode="extended", exportselection=False)
        self.lista_ruta.grid(row=4, column=0, sticky="ew")
        ttk.Button(der, text="Cerrar las calles seleccionadas de la ruta",
                   command=self.cerrar_de_la_ruta).grid(row=5, column=0, sticky="w", pady=4)

    # Crea el bloque de un punto (lista de distritos, latitud, longitud y botón de mapa); se usa una vez para origen y otra para destino
    def crear_punto(self, padre, titulo, nombres, clave, fila):
        marco = ttk.LabelFrame(padre, text=titulo, padding=6)
        marco.grid(row=fila, column=0, sticky="ew", pady=3)
        combo = ttk.Combobox(marco, values=nombres, state="readonly", width=28)  # readonly = solo se puede elegir de la lista
        combo.grid(row=0, column=0, columnspan=2, sticky="ew")
        combo.bind("<<ComboboxSelected>>", lambda e: self.poner_distrito(combo, clave))  # e es el evento, no se usa; al elegir un distrito se llenan lat y lon
        ttk.Label(marco, text="Latitud:").grid(row=1, column=0, sticky="w")
        lat = ttk.Entry(marco, width=16)
        lat.grid(row=1, column=1, sticky="w")
        ttk.Label(marco, text="Longitud:").grid(row=2, column=0, sticky="w")
        lon = ttk.Entry(marco, width=16)
        lon.grid(row=2, column=1, sticky="w")
        ttk.Button(marco, text="Elegir en el mapa",
                   command=lambda: self.pedir_clic(clave)).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))  # lambda para pasar "clave" al botón
        return combo, lat, lon

    # ------------------------------------------------------------------
    # Origen y destino
    # ------------------------------------------------------------------
    # Devuelve las dos cajas de texto (lat, lon) del origen o del destino
    def entradas_de(self, clave):
        if clave == "origen":
            return self.lat_origen, self.lon_origen
        return self.lat_destino, self.lon_destino

    # Escribe latitud y longitud en las cajas del origen o destino
    def poner_coordenadas(self, clave, lat, lon):
        entrada_lat, entrada_lon = self.entradas_de(clave)
        entrada_lat.delete(0, "end")  # Borra lo que había antes
        entrada_lat.insert(0, f"{lat:.6f}")  # 6 decimales ≈ 0.1 m
        entrada_lon.delete(0, "end")
        entrada_lon.insert(0, f"{lon:.6f}")

    # Al elegir un distrito de la lista, busca sus coordenadas y las pone en las cajas
    def poner_distrito(self, combo, clave):
        for nombre, lat, lon in self.grafo.distritos:
            if nombre == combo.get():
                self.poner_coordenadas(clave, lat, lon)

    # Se activa al pulsar "Elegir en el mapa": recuerda para quién es el siguiente clic
    def pedir_clic(self, clave):
        self.clic_para = clave
        self.estado.config(text=f"Haz clic en el mapa para elegir el {clave}.")

    # El canvas llama a esto en cada clic; devuelve True solo si la pestaña estaba esperando un clic
    def al_hacer_clic(self, lat, lon):
        # La ventana llama a este método cuando el usuario hace clic en el mapa
        if self.clic_para is None:  # No se pidió ningún clic: el canvas debe usarlo para otra cosa
            return False
        clave, self.clic_para = self.clic_para, None  # Guarda para quién era y deja de esperar clics
        self.poner_coordenadas(clave, lat, lon)
        self.estado.config(text=f"Se fijó el {clave}.")
        return True

    # Convierte lo escrito en las cajas en una esquina del grafo, validando que sea correcto
    def leer_esquina(self, clave, entrada_lat, entrada_lon):
        # Lee latitud y longitud, valida que sean números dentro del mapa y devuelve la esquina
        try:
            lat = float(entrada_lat.get().replace(",", "."))  # Acepta coma decimal, por si el usuario escribe "-13,52"
            lon = float(entrada_lon.get().replace(",", "."))
        except ValueError:  # Cajas vacías o con letras
            raise ValueError(f"El {clave} necesita latitud y longitud numéricas.")
        lim = self.grafo.limites
        if not (lim["sur"] - 0.01 <= lat <= lim["norte"] + 0.01 and lim["oeste"] - 0.01 <= lon <= lim["este"] + 0.01):  # 0.01° ≈ 1 km de margen alrededor del mapa
            raise ValueError(f"El {clave} está fuera del mapa de Cusco.")
        return self.grafo.esquina_mas_cercana(lat, lon)

    # ------------------------------------------------------------------
    # Búsqueda (en un hilo para que la ventana no se congele)
    # ------------------------------------------------------------------
    # Se ejecuta al pulsar "Buscar rutas": valida los datos y lanza la búsqueda en un hilo aparte
    def buscar(self):
        if self.buscando:  # Ya hay una búsqueda en marcha
            return
        try:
            origen = self.leer_esquina("origen", self.lat_origen, self.lon_origen)
            destino = self.leer_esquina("destino", self.lat_destino, self.lon_destino)
        except ValueError as error:  # Dato inválido: se avisa y no se busca
            messagebox.showwarning("Datos incompletos", str(error))
            return

        # Lee las opciones de la búsqueda: tiempo máximo y porcentaje de alternativas
        try:
            segundos = float(self.entrada_tiempo.get().replace(",", "."))
            tolerancia = float(self.entrada_tolerancia.get().replace(",", ".")) / 100  # El usuario escribe un porcentaje (15) y el Backtracking espera una fracción (0.15)
            if segundos < 0 or tolerancia < 0:  # Valores negativos no tienen sentido
                raise ValueError  # Se lanza a propósito para entrar al mismo aviso que las letras
        except ValueError:  # Cajas vacías, con letras o negativas
            messagebox.showwarning("Datos incorrectos", "El tiempo y el porcentaje deben ser números mayores o iguales a 0.")
            return

        self.buscando = True
        self.detener.clear()  # Baja la bandera por si quedó activada en una búsqueda anterior
        self.boton_buscar.config(state="disabled")  # Evita un segundo clic mientras busca
        self.boton_detener.config(state="normal")  # Ahora sí se puede detener
        self.estado.config(text="Buscando rutas...")

        # Lo que corre en el hilo: la búsqueda, y deja el resultado (o el error) en la cola
        def trabajo():
            try:
                bt = buscar_rutas(self.grafo, origen, destino, max_segundos=segundos,
                                  tolerancia=tolerancia, detener=self.detener)  # detener es la bandera que el Backtracking revisa para parar
                self.cola.put(("ok", bt))
            except Exception as error:  # Cualquier fallo se manda a la ventana; el hilo no puede mostrar mensajes por sí mismo
                self.cola.put(("error", str(error)))

        try:
            threading.stack_size(128 * 1024 * 1024)   # pila grande para la recursión
            # Un hilo nuevo tiene menos pila que el programa principal, y el Backtracking baja una esquina por nivel; 128 MB evita que se agote
        except (ValueError, RuntimeError):  # Si el sistema no permite ese tamaño, se sigue con el tamaño por defecto
            pass
        threading.Thread(target=trabajo, daemon=True).start()  # daemon=True: si se cierra la ventana, el hilo no la mantiene abierta
        self.after(100, self.revisar_cola)  # Empieza a revisar si el hilo ya terminó

    # Botón Detener: activa la bandera y el Backtracking para y devuelve lo que reunió hasta ese momento
    def detener_busqueda(self):
        # Botón Detener: la búsqueda para y se muestra lo que se reunió hasta ese momento
        self.detener.set()  # El hilo la revisa cada cierto número de llamadas, por eso la parada no es inmediata
        self.estado.config(text="Deteniendo...")

    # Revisa cada 100 ms si el hilo ya dejó su resultado; si no, se vuelve a programar
    def revisar_cola(self):
        # Se ejecuta cada 100 ms hasta que el hilo deja su resultado
        try:
            tipo, dato = self.cola.get_nowait()  # get_nowait no espera: si está vacía da error y la ventana sigue libre
        except queue.Empty:
            self.after(100, self.revisar_cola)
            return
        self.buscando = False
        self.boton_buscar.config(state="normal")
        self.boton_detener.config(state="disabled")  # Ya no hay nada que detener
        if tipo == "error":
            self.estado.config(text="Ocurrió un error.")
            messagebox.showerror("Error al buscar rutas", dato)
        else:
            self.estado.config(text="Búsqueda terminada.")
            self.mostrar(dato)

    # ------------------------------------------------------------------
    # Mostrar resultados
    # ------------------------------------------------------------------
    # Muestra el resultado de la búsqueda: resumen, tabla de rutas y la ruta más corta dibujada en el mapa
    def mostrar(self, bt):
        self.resultado = bt  # Se guarda para poder dibujar otras rutas al elegirlas en la tabla
        self.tabla.delete(*self.tabla.get_children())  # Limpia lo del resultado anterior
        self.lista_ruta.delete(0, "end")
        self.nombres_ruta = []

        lineas = []  # Líneas del resumen
        if bt.camino is None:  # No hubo ruta: solo se muestra el motivo
            self.app.canvas.limpiar_rutas()
            lineas.append(bt.mensaje)
            lineas.append(f"Zona de búsqueda: {bt.esquinas_zona} esquinas | tiempo: {bt.segundos:.2f} s")  # Sirve para ver si la zona era muy chica o si se acabó el tiempo
        else:
            lineas.append(f"Ruta más corta: {bt.metros:.0f} m")
            lineas.append(f"Zona de búsqueda (Divide y Vencerás): {bt.esquinas_zona} esquinas")  # Esquinas del mapa que quedaron después de dividir; solo ahí buscó el Backtracking
            lineas.append(f"Rutas completas encontradas: {bt.encontradas} | mostradas: {len(bt.rutas)}")  # Se encuentran más de las que se guardan para mostrar
            lineas.append(f"Ramas descartadas (podas): {bt.podas}")
            lineas.append(f"Llamadas recursivas: {bt.visitadas} | tiempo: {bt.segundos:.2f} s")
            lineas.append(f"Estado: {bt.mensaje}")
            for i, (metros, _camino) in enumerate(bt.rutas):
                self.tabla.insert("", "end", iid=str(i), values=(i + 1, f"{metros:.0f}"))  # iid = posición en bt.rutas, para saber cuál se eligió
            self.tabla.selection_set("0")  # Deja elegida la más corta (la primera)
            self.dibujar(0)

        self.resumen.config(state="normal")  # Se habilita solo para escribir el texto
        self.resumen.delete("1.0", "end")
        self.resumen.insert("1.0", "\n".join(lineas))
        self.resumen.config(state="disabled")

    # Convierte una ruta (lista de esquinas) en lista de (lat, lon), que es lo que dibuja el canvas
    def puntos_de(self, camino):
        return [self.grafo.nodos[e] for e in camino]

    # Dibuja en el mapa la ruta elegida en rojo y algunas alternativas en gris
    def dibujar(self, indice):
        rutas = self.resultado.rutas
        canvas = self.app.canvas
        canvas.limpiar_rutas()  # Quita lo dibujado antes
        for i in range(min(len(rutas), MAX_ALTERNATIVAS + 1)):  # Se limita para no llenar el mapa de líneas
            if i != indice:
                canvas.dibujar_ruta(self.puntos_de(rutas[i][1]), COLOR_OTRAS)
        canvas.dibujar_ruta(self.puntos_de(rutas[indice][1]), COLOR_ELEGIDA)  # La elegida se dibuja al final para quedar encima
        self.llenar_calles_de(rutas[indice][1])

    # Se ejecuta al elegir una fila de la tabla: dibuja esa ruta
    def al_elegir_ruta(self, evento=None):
        if self.resultado is None or not self.resultado.rutas:  # Nada que dibujar
            return
        elegidas = self.tabla.selection()
        if elegidas:
            self.dibujar(int(elegidas[0]))  # El iid de la fila es su posición en rutas

    # Llena la lista con las calles por las que pasa la ruta, juntando los tramos seguidos de la misma calle
    def llenar_calles_de(self, camino):
        # Junta los tramos seguidos de una misma calle y suma sus metros
        tramos = []   # lista de [nombre, metros]
        for u, v in zip(camino[:-1], camino[1:]):  # Pares de esquinas seguidas: (1ª,2ª), (2ª,3ª)...
            nombre = self.grafo.nombre_tramo(u, v)
            metros = min(c[1] for c in self.grafo.calles[u] if c[0] == v)  # Si hay varias calles entre las dos esquinas, la más corta
            if tramos and tramos[-1][0] == nombre:  # Misma calle que el tramo anterior: se suman los metros
                tramos[-1][1] += metros
            else:
                tramos.append([nombre, metros])
        self.lista_ruta.delete(0, "end")
        self.nombres_ruta = []  # Se guarda aparte para poder cerrar la calle al seleccionarla (el texto de la lista lleva los metros)
        for nombre, metros in tramos:
            self.lista_ruta.insert("end", f"{nombre} ({metros:.0f} m)")
            self.nombres_ruta.append(nombre)

    # ------------------------------------------------------------------
    # Calles cerradas
    # ------------------------------------------------------------------
    # Muestra en la lista solo las calles que contienen lo escrito en el cuadro de búsqueda
    def filtrar_calles(self):
        texto = self.filtro.get().lower()  # Minúsculas para no distinguir mayúsculas
        self.calles_filtradas = [c for c in self.grafo.nombres_calles if texto in c.lower()]  # Se guarda para saber qué calle es cada fila de la lista
        self.lista_calles.delete(0, "end")
        for c in self.calles_filtradas:
            self.lista_calles.insert("end", c)

    # Actualiza la lista de calles cerradas y avisa que las rutas mostradas pueden estar desactualizadas
    def refrescar_cerradas(self):
        self.lista_cerradas.delete(0, "end")
        for c in sorted(self.grafo.cerradas_nombre):
            self.lista_cerradas.insert("end", c)
        if self.resultado is not None:  # Ya había rutas en pantalla: se calcularon con las calles de antes
            self.estado.config(text="Las calles cambiaron: vuelve a buscar las rutas.")

    # Impide cambiar calles mientras corre una búsqueda, porque el hilo está leyendo esas mismas calles
    def puede_cambiar_calles(self):
        if self.buscando:
            messagebox.showinfo("Búsqueda en curso", "Espera a que termine la búsqueda para cambiar las calles.")
            return False
        return True

    # Cierra las calles elegidas en la lista de calles
    def cerrar_seleccionadas(self):
        if not self.puede_cambiar_calles():
            return
        for i in self.lista_calles.curselection():  # curselection da las posiciones elegidas
            self.grafo.cerrar_calle(self.calles_filtradas[i])  # La posición sirve porque la lista y calles_filtradas están en el mismo orden
        self.refrescar_cerradas()

    # Cierra las calles elegidas dentro de la lista "calles de la ruta" (así se prueba una ruta alternativa)
    def cerrar_de_la_ruta(self):
        if not self.puede_cambiar_calles():
            return
        sin_nombre = False  # Para avisar una sola vez al final
        for i in self.lista_ruta.curselection():
            nombre = self.nombres_ruta[i]
            if nombre == "Sin nombre":  # cerrar_calle lo rechaza: muchos tramos distintos comparten ese nombre
                sin_nombre = True
            else:
                self.grafo.cerrar_calle(nombre)
        if sin_nombre:
            messagebox.showinfo("Calle sin nombre", "Los tramos sin nombre no se pueden cerrar por nombre.")
        self.refrescar_cerradas()

    # Vuelve a abrir las calles elegidas en la lista de cerradas
    def abrir_seleccionadas(self):
        if not self.puede_cambiar_calles():
            return
        nombres = [self.lista_cerradas.get(i) for i in self.lista_cerradas.curselection()]  # Primero se leen los nombres: al abrir, la lista cambiaría de posiciones
        for nombre in nombres:
            self.grafo.abrir_calle(nombre)
        self.refrescar_cerradas()

    # Deja todas las calles abiertas
    def abrir_todas(self):
        if not self.puede_cambiar_calles():
            return
        self.grafo.abrir_todas()
        self.refrescar_cerradas()
