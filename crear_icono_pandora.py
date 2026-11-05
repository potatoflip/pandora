"""Convierte el arte PNG transparente de Pandora a un icono multirresolución."""

from pathlib import Path

from PIL import Image


RAIZ = Path(__file__).resolve().parent
ORIGEN = RAIZ / "assets" / "pandora-tesoro.png"
DESTINO = RAIZ / "assets" / "pandora-tesoro.ico"
TAMANOS = (256, 128, 64, 48, 32, 16)


def crear_icono():
    imagen = Image.open(ORIGEN).convert("RGBA")
    canal_alfa = imagen.getchannel("A")
    minimo, maximo = canal_alfa.getextrema()
    if minimo == 255:
        raise ValueError("El PNG no tiene transparencia; no se creó el icono.")

    imagen.save(
        DESTINO,
        format="ICO",
        sizes=[(tamano, tamano) for tamano in TAMANOS],
        bitmap_format="bmp",
    )
    print(f"Icono creado: {DESTINO}")


if __name__ == "__main__":
    crear_icono()
