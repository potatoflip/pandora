"""Mensajes estructurados de avance para el lanzador de escritorio."""


def reportar_progreso(porcentaje, descripcion):
    porcentaje = max(0, min(100, int(porcentaje)))
    print(f"[PROGRESO] {porcentaje}|{descripcion}")


def progreso_por_rango(inicio, fin, etapa):
    """Crea un callback que traduce el avance de documentos a un rango global."""
    def actualizar(actual, total, detalle=""):
        fraccion = min(1, actual / total) if total else 1
        porcentaje = inicio + round((fin - inicio) * fraccion)
        descripcion = f"{etapa}: {detalle} ({actual}/{total})" if detalle else f"{etapa} ({actual}/{total})"
        reportar_progreso(porcentaje, descripcion)

    return actualizar
