---
name: carrusel
description: Cómo maquetar un carrusel de Instagram de @francismangano en HTML con su marca y exportarlo a PNG de 1080×1350. La usa el diseñador de carruseles.
---

# Carruseles de @francismangano

## Proceso
1. `python3 scripts/registro.py ver ID` → estado `aprobado` (o `editada` si es una corrección). Si no, para.
2. Lee `guiones/ID.md` (plantilla de carrusel) y `brand.json`.
3. Copia `.claude/skills/carrusel/plantilla.html` a `carruseles/ID/carrusel.html`.
4. Sustituye los slides de ejemplo por los del guion, usando los tipos de slide de la plantilla:

| Tipo | Clase | Para |
| --- | --- | --- |
| Portada | `slide portada` (+ `oscura` si quieres contraste) | Gancho de máx. 10 palabras. Resalta 2–3 palabras con `<em>` |
| Contenido | `slide contenido` | Número + titular + 1 idea (máx. 35 palabras) |
| Comparativa | `slide comparativa` | Esto o aquello; marca la opción de Francis con `col elegida` |
| Lista | `slide lista` | 3–4 puntos cortos |
| Frase | `slide frase` | Resumen o frase de Francis |
| CTA | `slide cta oscura` | Acción + palabra clave (`.palabra`) + firma opcional |

5. Actualiza la numeración del pie (`2/8`) y la etiqueta del pilar de la portada.
6. Si los colores o fuentes de `brand.json` cambiaron, actualiza las variables de `:root`.
7. Exporta: `python3 scripts/render_carrusel.py ID`.
8. **Mira los PNG** (lee 2–3 con la herramienta Read): texto cortado, saltos de línea feos, viudas, contraste. El script avisa con `REVISAR:` si algo se sale. Corrige y vuelve a exportar.
9. Con todo bien: `python3 scripts/render_carrusel.py ID --publicar`, escribe `publicar/ID/texto.txt` (caption hasta 120 palabras, hashtags, palabra clave) y `python3 scripts/registro.py estado ID editada`.

## Reglas de diseño
- 6 a 10 slides. Una idea por slide.
- Máx. 35 palabras por slide de contenido; si no cabe, divide en dos slides, no reduzcas la letra.
- Tamaños mínimos: titular 72 px, texto 36 px. Se lee en un móvil.
- Alterna fondo claro y oscuro solo en portada y CTA; el resto claro, para que se lea como una serie.
- Sin fotos de stock ni imágenes generadas que aparenten ser trabajos reales de Francis. Si el guion pide foto, debe ser suya: búscala en `assets/` o `brutos/ID/` y colócala con `<img>` (cópiala a `carruseles/ID/`). Si no está, portada solo tipográfica.
- El primer slide tiene que funcionar solo en la cuadrícula del perfil.

## Requisito (una vez)
`pip install playwright && python3 -m playwright install chromium`
