#!/usr/bin/env python3
"""Genera los PNG del splash de Plymouth de BookOS en plymouth/.

Los PNG SE COMMITEAN: el build de la ISO copia plymouth/ tal cual
(BookOS-ISO/rpm/collect-branding.sh) y no necesita Pillow ni librsvg. Este
script es para rehacerlos cuando cambie el logo.

    python3 build-plymouth.py

Requisitos: Pillow y rsvg-convert (librsvg2-tools).
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE / "plymouth"
# El logo es el mismo que pinta el escritorio (bookos-shell/src/marca.rs), no
# una copia: si el splash y el panel usaran ficheros distintos acabarían
# divergiendo. Repos hermanos: BookOS-Loading-System y BookOS-Envoiroment
# cuelgan del mismo directorio.
LOGO_SVG = HERE.parent / "BookOS-Envoiroment" / "bookos-desktop" / "crates" / "bookos-shell" / "assets" / "bookos.svg"

WHITE = (255, 255, 255)
SS = 4  # supermuestreo: ImageDraw no aplica antialias a elipses

# Plymouth reescala muestreando 4 vecinos por píxel de destino, sin promediar
# el resto (ply_pixel_buffer_resize): al reducir a menos de la mitad se salta
# píxeles y los bordes redondos dientan. Cada pieza va en tamaños separados por
# ~√2 y bookos.script reduce desde el menor que no quede por debajo, así que
# nunca reduce por debajo del 70 %. Medido emulando ese reescalado, error medio
# frente a LANCZOS: en 1080p (disco de 153 px) 2,32 reduciendo desde 640 y 1,21
# desde 160; en 1440p (204 px) 1,61 frente a 0,81. Si cambias estas listas,
# cambia las funciones pick_* de bookos.script.
LOGO_SIZES = (160, 224, 320, 448, 640)
CAP_SIZES = (4, 8, 12, 16)
BULLET_SIZES = (8, 12, 16, 24)


def aa_disc(size):
    big = Image.new("L", (size * SS, size * SS), 0)
    ImageDraw.Draw(big).ellipse((0, 0, size * SS - 1, size * SS - 1), fill=255)
    return big.resize((size, size), Image.LANCZOS)


def white_with_alpha(mask):
    img = Image.new("RGBA", mask.size, WHITE + (0,))
    img.putalpha(mask)
    return img


def main():
    if not LOGO_SVG.exists():
        raise SystemExit(f"✗ no encuentro el logo: {LOGO_SVG}")

    # Todos los PNG de plymouth/ salen de aquí; se borran para no dejar huérfanos
    # que acabarían metidos en el initramfs.
    for old in OUT.glob("*.png"):
        old.unlink()

    # Cada tamaño se rasteriza desde el vector, no reduciendo uno grande.
    for size in LOGO_SIZES:
        subprocess.run(
            ["rsvg-convert", "-w", str(size), "-h", str(size), str(LOGO_SVG), "-o", str(OUT / f"logo-{size}.png")],
            check=True,
        )

    # Puntas de la barra: medio círculo cada una. La barra va en tres piezas
    # porque Image.Scale deforma las puntas al estirar una píldora entera.
    for h in CAP_SIZES:
        cap = aa_disc(h)
        white_with_alpha(cap.crop((0, 0, h // 2, h))).save(OUT / f"bar-l-{h}.png", optimize=True)
        white_with_alpha(cap.crop((h // 2, 0, h, h))).save(OUT / f"bar-r-{h}.png", optimize=True)
    Image.new("RGBA", (2, 2), WHITE + (255,)).save(OUT / "bar-body.png", optimize=True)

    for d in BULLET_SIZES:
        white_with_alpha(aa_disc(d)).save(OUT / f"bullet-{d}.png", optimize=True)

    total = sum(p.stat().st_size for p in OUT.glob("*.png"))
    print(f"[✓] {len(list(OUT.glob('*.png')))} PNG, {total / 1024:.0f} KiB en {OUT}")


if __name__ == "__main__":
    main()
