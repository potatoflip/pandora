"""Interfaz de escritorio para ejecutar los procesos principales de Pandora."""

from __future__ import annotations

import os
import queue
import re
import sys
import threading
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk

import pythoncom
from proceso_excel.cancelacion import (
    ProcesoCancelado,
    comprobar_detencion,
    reiniciar_solicitud_detencion,
    solicitar_detencion,
)


TAREAS = {
    "main.py": {
        "titulo": "Generar Pandora · main.py",
        "descripcion": "Descarga los datos, genera los archivos de revisión y ejecuta en SAP las decisiones automáticas.",
        "confirmacion": "main.py consultará SAP y ejecutará las liberaciones y bloqueos automáticos. ¿Deseas continuar?",
    },
    "aplicar_decisiones_pandora.py": {
        "titulo": "Aplicar decisiones",
        "descripcion": "Lee el JSON guardado en la carpeta configurada y reemplaza las listas manuales.",
        "confirmacion": None,
    },
    "ejecuta_liberaciones.py": {
        "titulo": "Ejecutar liberaciones y bloqueos",
        "descripcion": "Procesa en SAP los documentos de liberar.xlsx y escalado.xlsx.",
        "confirmacion": "Se ejecutarán en SAP las liberaciones y los bloqueos de las listas manuales. ¿Deseas continuar?",
    },
}


def _raiz_proyecto():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _carpeta_datos():
    ruta = os.environ.get("PANDORA_DATA_DIR", "").strip()
    if ruta:
        return ruta
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as clave:
                return str(winreg.QueryValueEx(clave, "PANDORA_DATA_DIR")[0])
        except (ImportError, OSError):
            pass
    return ""


class _SalidaConsola:
    def __init__(self, eventos):
        self.eventos = eventos

    def write(self, texto):
        if texto:
            self.eventos.put(("salida", texto))
        return len(texto)

    def flush(self):
        return None

    def isatty(self):
        return False


class LanzadorPandora:
    def __init__(self, ventana):
        self.ventana = ventana
        self.eventos = queue.Queue()
        self.ejecutando = False
        self.detencion_enviada = False
        self.botones = []
        self._buffer_salida = ""
        self._claves_tiempo = {
            "Parte 1 · Extracción y preparación de Pandora": "preparacion",
            "Parte 2 · Liberaciones y bloqueos automáticos VA14L": "automatico",
            "Liberaciones y bloqueos manuales VA14L": "manual",
        }
        self._titulos_tiempo = {
            "preparacion": "Preparación de Pandora",
            "automatico": "Liberaciones automáticas VA14L",
            "manual": "Liberaciones y bloqueos manuales",
        }
        self._tiempo_actual = None
        ventana.title("Pandora · Centro de ejecución")
        ventana.geometry("1220x780")
        ventana.minsize(980, 650)
        ventana.configure(bg="#100D13")
        ventana.protocol("WM_DELETE_WINDOW", self._cerrar)

        estilo = ttk.Style(ventana)
        estilo.theme_use("clam")
        estilo.configure("TFrame", background="#100D13")
        estilo.configure("Panel.TFrame", background="#1D1724")
        estilo.configure("TLabel", background="#100D13", foreground="#E8DDBF", font=("Segoe UI", 10))
        estilo.configure("Title.TLabel", font=("Georgia", 25, "bold"), foreground="#E0B85A")
        estilo.configure("Subtitle.TLabel", foreground="#B5A9BC")
        estilo.configure("PanelTitle.TLabel", background="#1D1724", foreground="#E0B85A", font=("Georgia", 13, "bold"))
        estilo.configure("Muted.TLabel", background="#1D1724", foreground="#B5A9BC", font=("Segoe UI", 9))
        estilo.configure("Time.TLabel", background="#1D1724", foreground="#F4EAD0", font=("Cascadia Mono", 12, "bold"))
        estilo.configure("Task.TButton", font=("Segoe UI", 10, "bold"), padding=(10, 10), background="#352342", foreground="#F4EAD0")
        estilo.map("Task.TButton", background=[("active", "#50345F"), ("disabled", "#28212D")], foreground=[("disabled", "#81778A")])
        estilo.configure("Small.TButton", font=("Segoe UI", 9), padding=(7, 5), background="#352342", foreground="#E0B85A")
        estilo.map("Small.TButton", background=[("active", "#50345F")])
        estilo.configure("Stop.TButton", font=("Segoe UI", 9, "bold"), padding=(7, 5), background="#6D263D", foreground="#FFF0F3")
        estilo.map("Stop.TButton", background=[("active", "#93334F"), ("disabled", "#33232A")], foreground=[("disabled", "#8B7B80")])
        estilo.configure("Gold.Horizontal.TProgressbar", troughcolor="#382546", background="#E0B85A", bordercolor="#62477A", lightcolor="#F5D98F", darkcolor="#A77924", thickness=12)

        encabezado = ttk.Frame(ventana, padding=(24, 18, 24, 9))
        encabezado.pack(fill="x")
        ttk.Label(encabezado, text="♛  PANDORA", style="Title.TLabel").pack(anchor="w")
        ttk.Label(encabezado, text="Centro de operaciones · Automatización comercial", style="Subtitle.TLabel").pack(anchor="w", pady=(3, 0))
        self.estado = tk.StringVar(value="Listo para iniciar")
        ttk.Label(encabezado, textvariable=self.estado, style="Subtitle.TLabel").pack(anchor="e", pady=(0, 2))
        self.progreso = ttk.Progressbar(
            encabezado,
            mode="determinate",
            maximum=100,
            value=0,
            style="Gold.Horizontal.TProgressbar",
        )
        self.progreso.pack(fill="x", pady=(8, 0))
        ttk.Frame(ventana, height=2, style="Panel.TFrame").pack(fill="x", padx=24, pady=(2, 0))

        contenido = ttk.Frame(ventana, padding=(24, 14, 24, 20))
        contenido.pack(fill="both", expand=True)
        contenido.columnconfigure(1, weight=1)
        contenido.rowconfigure(0, weight=1)

        panel_tareas = ttk.Frame(contenido, style="Panel.TFrame", width=330)
        panel_tareas.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        panel_tareas.grid_propagate(False)
        canvas_lateral = tk.Canvas(
            panel_tareas,
            bg="#1D1724",
            highlightthickness=0,
            bd=0,
        )
        scroll_lateral = ttk.Scrollbar(
            panel_tareas,
            orient="vertical",
            command=canvas_lateral.yview,
        )
        canvas_lateral.configure(yscrollcommand=scroll_lateral.set)
        canvas_lateral.pack(side="left", fill="both", expand=True)
        scroll_lateral.pack(side="right", fill="y")
        contenido_lateral = ttk.Frame(canvas_lateral, style="Panel.TFrame", padding=16)
        ventana_lateral = canvas_lateral.create_window(
            (0, 0),
            window=contenido_lateral,
            anchor="nw",
        )
        contenido_lateral.bind(
            "<Configure>",
            lambda _evento: canvas_lateral.configure(
                scrollregion=canvas_lateral.bbox("all")
            ),
        )
        canvas_lateral.bind(
            "<Configure>",
            lambda evento: canvas_lateral.itemconfigure(
                ventana_lateral,
                width=evento.width,
            ),
        )
        ttk.Label(contenido_lateral, text="Procesos", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(contenido_lateral, text="Algunas acciones conectan con SAP y modifican documentos.", style="Muted.TLabel", wraplength=285, justify="left").pack(anchor="w", pady=(5, 13))

        for nombre, tarea in TAREAS.items():
            boton = ttk.Button(contenido_lateral, text=tarea["titulo"], style="Task.TButton", command=lambda script=nombre: self._iniciar(script))
            boton.pack(fill="x", pady=(0, 5))
            ttk.Label(contenido_lateral, text=tarea["descripcion"], style="Muted.TLabel", wraplength=285, justify="left").pack(anchor="w", pady=(0, 10))
            self.botones.append(boton)

        ttk.Frame(contenido_lateral, height=1, style="TFrame").pack(fill="x", pady=(2, 10))
        ttk.Label(contenido_lateral, text="Tiempos de ejecución", style="PanelTitle.TLabel").pack(anchor="w", pady=(0, 7))
        self.etiquetas_tiempo = {}
        for clave, titulo in self._titulos_tiempo.items():
            tarjeta = ttk.Frame(contenido_lateral, style="Panel.TFrame", padding=(9, 6))
            tarjeta.pack(fill="x", pady=3)
            ttk.Label(tarjeta, text=titulo, style="Muted.TLabel", wraplength=270).pack(anchor="w")
            valor = ttk.Label(tarjeta, text="Aún sin ejecutar", style="Time.TLabel")
            valor.pack(anchor="w", pady=(3, 0))
            self.etiquetas_tiempo[clave] = valor

        carpeta = _carpeta_datos()
        color = "#D6B75A" if carpeta else "#CF796F"
        texto_carpeta = f"Carpeta de datos\n{carpeta}" if carpeta else "PANDORA_DATA_DIR no está configurada."
        ttk.Label(contenido_lateral, text=texto_carpeta, background="#1D1724", foreground=color, wraplength=285, justify="left").pack(anchor="w", pady=(12, 0))

        panel_consola = ttk.Frame(contenido, style="Panel.TFrame", padding=14)
        panel_consola.grid(row=0, column=1, sticky="nsew")
        panel_consola.columnconfigure(0, weight=1)
        panel_consola.rowconfigure(1, weight=1)
        barra = ttk.Frame(panel_consola, style="Panel.TFrame")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        ttk.Label(barra, text="Registro del proceso", style="PanelTitle.TLabel").pack(side="left")
        self.boton_detener = ttk.Button(
            barra,
            text="Detener proceso",
            style="Stop.TButton",
            command=self._solicitar_detencion,
            state="disabled",
        )
        self.boton_detener.pack(side="right", padx=(8, 0))
        ttk.Button(barra, text="Limpiar", style="Small.TButton", command=self._limpiar).pack(side="right")

        marco_texto = ttk.Frame(panel_consola, style="Panel.TFrame")
        marco_texto.grid(row=1, column=0, sticky="nsew")
        marco_texto.rowconfigure(0, weight=1)
        marco_texto.columnconfigure(0, weight=1)
        self.consola = tk.Text(marco_texto, wrap="word", state="disabled", bg="#0D0A10", fg="#E9DFC8", insertbackground="#E0B85A", selectbackground="#50345F", font=("Cascadia Mono", 9), padx=12, pady=10, relief="flat")
        barra_desplazamiento = ttk.Scrollbar(marco_texto, orient="vertical", command=self.consola.yview)
        self.consola.configure(yscrollcommand=barra_desplazamiento.set)
        self.consola.grid(row=0, column=0, sticky="nsew")
        barra_desplazamiento.grid(row=0, column=1, sticky="ns")
        self._escribir("Selecciona un proceso para comenzar.\n")
        ventana.after(100, self._leer_eventos)

    def _escribir(self, texto):
        self.consola.configure(state="normal")
        self.consola.insert("end", texto)
        self.consola.see("end")
        self.consola.configure(state="disabled")

    def _limpiar(self):
        self.consola.configure(state="normal")
        self.consola.delete("1.0", "end")
        self.consola.configure(state="disabled")

    def _solicitar_detencion(self):
        if not self.ejecutando or self.detencion_enviada:
            return
        solicitar_detencion()
        self.detencion_enviada = True
        self.boton_detener.configure(state="disabled")
        self.estado.set("Detención solicitada · esperando un punto seguro")
        self._escribir(
            "\nSe solicitó detener el proceso. Pandora terminará la acción SAP "
            "que está en curso y se detendrá en el siguiente punto seguro. "
            "Si ya comenzó a guardar un documento, completará ese guardado.\n"
        )

    def _limpiar_tiempos(self, nombre_script):
        if nombre_script == "main.py":
            claves = ("preparacion", "automatico")
        elif nombre_script == "ejecuta_liberaciones.py":
            claves = ("manual",)
        else:
            claves = ()
        for clave in claves:
            self.etiquetas_tiempo[clave].configure(text="En curso…")

    def _leer_linea_tiempo(self, linea):
        avance = re.search(r"^\[PROGRESO\]\s*(\d{1,3})\|(.+)$", linea)
        if avance:
            porcentaje = max(0, min(100, int(avance.group(1))))
            self.progreso.configure(value=porcentaje)
            self.estado.set(f"{porcentaje}% · {avance.group(2).strip()}")
            return True
        inicio = re.search(r"\[TIEMPO\] Inicia: (.+)", linea)
        if inicio:
            titulo = inicio.group(1).strip()
            self._tiempo_actual = self._claves_tiempo.get(titulo)
            self.estado.set(f"En curso · {self._titulos_tiempo.get(self._tiempo_actual, titulo)}")
            return False
        fin = re.search(r"\[TIEMPO\] Termina: (.+?) \| Duración: (\d{2}:\d{2}:\d{2}\.\d{2})", linea)
        if fin:
            clave = self._claves_tiempo.get(fin.group(1).strip()) or self._tiempo_actual
            if clave:
                duracion = fin.group(2)
                self.etiquetas_tiempo[clave].configure(text=duracion)
            self._tiempo_actual = None
        return False

    def _procesar_salida(self, texto):
        self._buffer_salida += texto
        lineas = self._buffer_salida.split("\n")
        self._buffer_salida = lineas.pop()
        for linea in lineas:
            if not self._leer_linea_tiempo(linea.strip()):
                self._escribir(f"{linea}\n")

    def _iniciar(self, nombre_script):
        if self.ejecutando:
            return
        confirmacion = TAREAS[nombre_script]["confirmacion"]
        if confirmacion and not messagebox.askyesno("Confirmar ejecución", confirmacion, parent=self.ventana):
            return
        ruta_script = _raiz_proyecto() / nombre_script
        if not getattr(sys, "frozen", False) and not ruta_script.is_file():
            messagebox.showerror("No se encontró el proceso", str(ruta_script), parent=self.ventana)
            return
        self.ejecutando = True
        self.detencion_enviada = False
        reiniciar_solicitud_detencion()
        self._buffer_salida = ""
        self._tiempo_actual = None
        self._limpiar_tiempos(nombre_script)
        self.estado.set(f"Preparando {nombre_script}…")
        self.progreso.configure(value=0)
        for boton in self.botones:
            boton.configure(state="disabled")
        self.boton_detener.configure(state="normal")
        self._escribir(f"\n{'=' * 72}\nIniciando {nombre_script}\n{'=' * 72}\n")
        threading.Thread(target=self._ejecutar, args=(nombre_script, ruta_script), daemon=True).start()

    def _ejecutar(self, nombre_script, ruta_script):
        salida = _SalidaConsola(self.eventos)
        correcto = False
        cancelado = False
        try:
            pythoncom.CoInitialize()
            raiz = str(_raiz_proyecto())
            if raiz not in sys.path:
                sys.path.insert(0, raiz)
            with redirect_stdout(salida), redirect_stderr(salida):
                comprobar_detencion()
                if nombre_script == "main.py":
                    from main import main
                    main()
                elif nombre_script == "aplicar_decisiones_pandora.py":
                    from aplicar_decisiones_pandora import aplicar_decisiones
                    aplicar_decisiones()
                else:
                    from ejecuta_liberaciones import main
                    main()
            correcto = True
        except ProcesoCancelado as error:
            cancelado = True
            salida.write(f"\nProceso detenido de forma segura: {error}\n")
        except BaseException as error:
            salida.write("\nEl proceso terminó con un error:\n")
            traceback.print_exception(type(error), error, error.__traceback__, file=salida)
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
            self.eventos.put(
                (
                    "finalizado",
                    nombre_script,
                    correcto,
                    cancelado,
                )
            )

    def _leer_eventos(self):
        try:
            while True:
                evento = self.eventos.get_nowait()
                if evento[0] == "salida":
                    self._procesar_salida(evento[1])
                else:
                    _, nombre_script, correcto, cancelado = evento
                    if self._buffer_salida:
                        linea_final = self._buffer_salida.strip()
                        if not self._leer_linea_tiempo(linea_final):
                            self._escribir(linea_final)
                        self._buffer_salida = ""
                    self.ejecutando = False
                    self.detencion_enviada = False
                    if correcto:
                        self.progreso.configure(value=100)
                    for boton in self.botones:
                        boton.configure(state="normal")
                    self.boton_detener.configure(state="disabled")
                    resultado = (
                        "se detuvo de forma segura"
                        if cancelado
                        else "terminó correctamente" if correcto else "terminó con errores"
                    )
                    self.estado.set(f"{nombre_script} {resultado}")
                    self._escribir(f"\n{nombre_script} {resultado}.\n")
        except queue.Empty:
            pass
        self.ventana.after(100, self._leer_eventos)

    def _cerrar(self):
        if self.ejecutando:
            messagebox.showinfo(
                "Proceso en curso",
                "Usa ‘Detener proceso’ para solicitar una detención segura antes de cerrar Pandora.",
                parent=self.ventana,
            )
            return
        self.ventana.destroy()


def main():
    ventana = tk.Tk()
    LanzadorPandora(ventana)
    ventana.mainloop()


if __name__ == "__main__":
    main()
