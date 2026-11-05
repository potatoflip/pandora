"""Cronómetro reutilizable para mostrar tiempos de las etapas Pandora."""

from contextlib import contextmanager
from time import perf_counter


def _formatear_duracion(segundos):
    horas, restante = divmod(segundos, 3600)
    minutos, segundos = divmod(restante, 60)
    return f"{int(horas):02}:{int(minutos):02}:{segundos:05.2f}"


@contextmanager
def medir_duracion(etapa):
    inicio = perf_counter()
    print(f"\n[TIEMPO] Inicia: {etapa}")
    try:
        yield
    finally:
        duracion = perf_counter() - inicio
        print(f"[TIEMPO] Termina: {etapa} | Duración: {_formatear_duracion(duracion)}")
