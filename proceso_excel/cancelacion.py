"""Señal cooperativa para detener los procesos del lanzador en puntos seguros."""

from threading import Event


_solicitud_detencion = Event()


class ProcesoCancelado(Exception):
    """El usuario solicitó detener el flujo en un punto seguro."""


def reiniciar_solicitud_detencion():
    _solicitud_detencion.clear()


def solicitar_detencion():
    _solicitud_detencion.set()


def detencion_solicitada():
    return _solicitud_detencion.is_set()


def comprobar_detencion():
    if detencion_solicitada():
        raise ProcesoCancelado(
            "Detención solicitada. El proceso paró en un punto seguro."
        )
