#!/usr/bin/env python3
"""Exporta un carrusel HTML a PNG de 1080×1350 (uno por slide).

Uso:
  python3 scripts/render_carrusel.py ID            # carruseles/ID/carrusel.html → carruseles/ID/png/
  python3 scripts/render_carrusel.py ID --publicar # además copia los PNG a publicar/ID/

Cada slide del HTML es un elemento con la clase "slide".
Requisitos (una vez): pip install playwright && python3 -m playwright install chromium
"""
import argparse
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ANCHO, ALTO = 1080, 1350


def main():
    p = argparse.ArgumentParser()
    p.add_argument("id")
    p.add_argument("--publicar", action="store_true")
    a = p.parse_args()

    carpeta = RAIZ / "carruseles" / a.id
    html = carpeta / "carrusel.html"
    if not html.exists():
        sys.exit(f"No existe {html.relative_to(RAIZ)}")
    salida = carpeta / "png"
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Falta Playwright: pip install playwright && python3 -m playwright install chromium")

    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        pagina = navegador.new_page(viewport={"width": ANCHO, "height": ALTO}, device_scale_factor=1)
        pagina.goto(html.resolve().as_uri())
        pagina.wait_for_load_state("networkidle")
        pagina.evaluate("document.fonts.ready")
        slides = pagina.query_selector_all(".slide")
        if not slides:
            sys.exit("El HTML no tiene elementos con la clase 'slide'.")
        if not 2 <= len(slides) <= 20:
            print(f"Aviso: {len(slides)} slides. Instagram admite de 2 a 20.")
        problemas = []
        for i, slide in enumerate(slides, 1):
            caja = slide.bounding_box()
            if not caja or round(caja["width"]) != ANCHO or round(caja["height"]) != ALTO:
                problemas.append(f"slide {i} mide {caja and round(caja['width'])}×{caja and round(caja['height'])}")
            # Texto que se sale de su caja
            desbordado = slide.evaluate(
                "el => [...el.querySelectorAll('*')].some(n => n.scrollHeight > n.clientHeight + 2 "
                "&& getComputedStyle(n).overflow === 'hidden')"
            )
            if desbordado:
                problemas.append(f"slide {i}: hay texto cortado")
            slide.screenshot(path=str(salida / f"{i:02d}.png"))
        navegador.close()

    print(f"OK {len(slides)} PNG en carruseles/{a.id}/png/")
    for prob in problemas:
        print(f"REVISAR: {prob}")

    if a.publicar:
        destino = RAIZ / "publicar" / a.id
        destino.mkdir(parents=True, exist_ok=True)
        for png in sorted(salida.glob("*.png")):
            shutil.copy(png, destino / png.name)
        print(f"Copiados a publicar/{a.id}/")


if __name__ == "__main__":
    main()
