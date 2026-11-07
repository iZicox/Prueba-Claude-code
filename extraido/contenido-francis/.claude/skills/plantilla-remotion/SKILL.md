---
name: plantilla-remotion
description: Especificación técnica del entorno de vídeo y carruseles de la agencia - proyecto Remotion en video/, composición ReelFrancis guiada por props.json, script de transcripción local y pruebas de verificación. La usa el ingeniero para montar y arreglar el entorno.
---

# Plantilla técnica de la agencia

El editor de vídeo **no programa**: prepara archivos y llama a herramientas que monta el ingeniero. Esta skill define esas herramientas. Para la API concreta de Remotion, usa las skills oficiales (`remotion-best-practices`, `remotion-captions`, `remotion-render`), instaladas con el plugin de Remotion o con `npx skills add remotion-dev/skills`.

## 1. Proyecto
- Si `video/package.json` no existe: `npx create-video@latest --tiktok video` (plantilla con subtítulos y Whisper) y `cd video && npm install`.
- Si el instalador hace preguntas, usa las respuestas por defecto. Si no puede ejecutarse sin interacción, crea un proyecto Remotion mínimo a mano (`remotion`, `@remotion/cli`, `@remotion/captions`, `@remotion/media-utils`, `@remotion/google-fonts`, `@remotion/install-whisper-cpp`, `react`, `react-dom`) siguiendo la skill oficial.
- Versión: todos los paquetes `remotion` y `@remotion/*` en la misma versión exacta.

## 2. Composición `ReelFrancis`
Archivo `video/src/francis/ReelFrancis.tsx`, registrado en `Root.tsx` con id `ReelFrancis`, 1080×1920, 30 fps.
La duración sale de `props.duracionSegundos` con `calculateMetadata`.

### props.json (lo escribe el editor en `video/public/ID/props.json`)
```json
{
  "id": "0031",
  "video": "0031/limpio.mp4",
  "duracionSegundos": 42.5,
  "gancho": {"texto": "¿Te han dicho que el torno daña las uñas?", "desde": 0, "hasta": 3},
  "textos": [{"texto": "Exotermia = el calor que suelta el gel", "desde": 8.2, "hasta": 11.0}],
  "broll": [{"src": "0031/broll-1.mp4", "desde": 12.0, "hasta": 15.5, "inicio": 0}],
  "captions": "0031/captions.json",
  "cierre": {"palabra": "CALOR", "texto": "Comenta CALOR y te la mando", "desde": 39.5}
}
```
- Rutas relativas a `video/public/` (se leen con `staticFile`).
- Tiempos en segundos sobre el vídeo limpio.
- `captions.json` en el formato `Caption[]` de `@remotion/captions` (`text`, `startMs`, `endMs`, `timestampMs`, `confidence`).
- `textos`, `broll` y `cierre` son opcionales.
- Valida las props con un esquema zod y da un error claro si falta algo.

### Capas (de abajo arriba)
1. Vídeo limpio a pantalla completa (`OffthreadVideo`, `objectFit: cover`).
2. B-roll: cada clip en su `Sequence`, sin audio (el audio es siempre el de la toma principal).
3. Gancho de `desde` a `hasta`: fuente de títulos, grande, con fondo semitransparente, dentro de la zona segura superior.
4. Textos en pantalla: misma familia, más pequeños, con entrada suave (spring de 6–8 fotogramas).
5. Subtítulos estilo TikTok: `createTikTokStyleCaptions()`, páginas de unos 1200 ms, máximo de palabras por línea de la marca, palabra activa con el color `color_palabra_activa`.
6. Cierre: la palabra clave grande sobre el color de acento desde `cierre.desde` hasta el final.

### Marca
- Lee los valores de `video/src/francis/brand.json`. El editor lo copia desde la raíz antes de cada render (`cp brand.json video/src/francis/brand.json`). Que el ingeniero deje también una copia inicial.
- Fuentes con `@remotion/google-fonts` (las de `brand.json` → `fuentes`).
- Zona segura de `brand.json` → `video.zona_segura`: ningún texto en esos márgenes.

## 3. Transcripción local
`video/scripts/transcribir.mjs <entrada.mp4> <salida.json>`:
1. Convierte la entrada a WAV de 16 kHz mono con ffmpeg.
2. Usa `@remotion/install-whisper-cpp`: `installWhisperCpp` y `downloadWhisperModel` (modelo `medium`; si el equipo es lento, `small`) en `video/whisper/` la primera vez, y después `transcribe` con `language: "es"` y marcas de tiempo por palabra.
3. Convierte el resultado con `toCaptions` y lo guarda como `Caption[]` en `salida.json`.
4. Imprime una línea: número de palabras y duración.

## 4. Render
El editor usa:
```
cd video
npx remotion render ReelFrancis ../publicar/ID/reel.mp4 --props=public/ID/props.json --codec=h264 --crf=18
npx remotion still ReelFrancis ../publicar/ID/portada.png --props=public/ID/props.json --frame=15
```
Comprueba que estos dos comandos funcionan tal cual.

## 5. Carruseles
- `python3 -c "import playwright"`. Si falla: `pip install playwright` (o `pip install --user playwright`) y `python3 -m playwright install chromium`.
- Prueba: copia `.claude/skills/carrusel/plantilla.html` a `carruseles/prueba/carrusel.html` y ejecuta `python3 scripts/render_carrusel.py prueba`. Deben salir 6 PNG. Borra `carruseles/prueba/` al terminar.

## 6. Prueba de vídeo (obligatoria antes de marcar el entorno como listo)
```
mkdir -p video/public/prueba
ffmpeg -y -f lavfi -i testsrc2=s=1080x1920:r=30:d=6 -f lavfi -i sine=frequency=440:d=6 \
  -shortest -c:v libx264 -preset veryfast -c:a aac video/public/prueba/limpio.mp4
```
- `node video/scripts/transcribir.mjs video/public/prueba/limpio.mp4 video/public/prueba/captions.json` (con un tono no habrá palabras: basta con que no falle y escriba un array).
- Escribe un `props.json` de prueba con gancho, un texto y cierre, renderiza los fotogramas 0–90 a `video/out/prueba.mp4` y saca un still.
- Mira el still con Read: gancho visible, fuentes de la marca, nada fuera de la zona segura.
- Borra `video/public/prueba` y `video/out` al terminar.

Si todo pasa: `python3 scripts/pipeline.py marcar entorno-listo`.
