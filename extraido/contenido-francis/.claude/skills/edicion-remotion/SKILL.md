---
name: edicion-remotion
description: Pipeline para convertir los brutos grabados por Francis en un reel vertical editado con la composición ReelFrancis de Remotion (cortes, subtítulos, textos en pantalla, b-roll, audio, render y paquete). La usa el editor de vídeo.
---

# Edición de reels con Remotion

La composición `ReelFrancis` y el script de transcripción los mantiene el ingeniero (skill `plantilla-remotion`). Tú preparas los archivos de la pieza, escribes `props.json` y renderizas.
Estilo: `brand.json` → `video`. Guion: `guiones/ID.md`.

## 0. Comprobar
- `python3 scripts/registro.py ver ID` → estado `grabada` (o `editada` si es una corrección).
- `ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration:stream_tags=rotate -of json brutos/ID/ARCHIVO` para cada bruto.
- Los brutos no se tocan nunca.

## 1. Copias a 9:16
```
mkdir -p video/public/ID
ffmpeg -y -i brutos/ID/toma.mov -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" \
  -c:v libx264 -preset veryfast -crf 18 -c:a aac -b:a 192k video/public/ID/a-camara.mp4
```
- Si hay varias tomas a cámara, conviértelas todas (`a-camara-1.mp4`...).
- Los b-roll (`broll*`) igual, a `video/public/ID/broll-N.mp4` (el audio da igual).
- Si un vídeo es horizontal, recorta el centro y dilo en tu resumen.

## 2. Limpiar (cortes)
1. `node video/scripts/transcribir.mjs video/public/ID/a-camara.mp4 video/public/ID/bruto-captions.json`
2. Silencios: `ffmpeg -i video/public/ID/a-camara.mp4 -af silencedetect=noise=-35dB:d=0.4 -f null - 2>&1 | grep silence_`
3. Compara la transcripción con el texto hablado del guion:
   - Frases repetidas o empezadas dos veces → quédate con la **última completa**.
   - Silencios de más de 0,4 s → recórtalos dejando 0,1 s de aire.
   - Muletillas sueltas fuera.
4. Escribe los tramos que se quedan en `video/public/ID/cortes.json` (`[{"desde": s, "hasta": s}, ...]`) y genera `video/public/ID/cortado.mp4` con ffmpeg (`trim`/`atrim` + `concat`).
5. Normaliza el audio a −14 LUFS:
   `ffmpeg -y -i video/public/ID/cortado.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy video/public/ID/limpio.mp4`
6. **Transcribe otra vez `limpio.mp4`** → `video/public/ID/captions.json`. Estos son los tiempos de los subtítulos.
7. Corrige en `captions.json` las palabras mal transcritas comparando con el guion (sobre todo los términos técnicos). No cambies los tiempos.

## 3. props.json
Escribe `video/public/ID/props.json` con el formato de la skill `plantilla-remotion`:
- `duracionSegundos`: duración de `limpio.mp4` según ffprobe.
- `gancho`: texto en pantalla del guion para 0–3 s.
- `textos`: los textos en pantalla del guion, situados en el momento en que se dice la frase (búscala en `captions.json`).
- `broll`: donde lo pida el guion, tramos de 1,5–4 s que no tapen el gancho.
- `cierre`: palabra clave del guion (si la hay) desde 2–3 s antes del final.

## 4. Render
```
cp brand.json video/src/francis/brand.json
cd video
npx remotion render ReelFrancis ../publicar/ID/reel.mp4 --props=public/ID/props.json --codec=h264 --crf=18
npx remotion still ReelFrancis ../publicar/ID/portada.png --props=public/ID/props.json --frame=15
```
Usa timeout de Bash de 600000 ms.

## 5. Autocomprobación (nadie lo va a ver antes que el revisor)
- `ffprobe`: 1080×1920, 30 fps, duración ≈ `duracionSegundos`.
- Volumen: `ffmpeg -i publicar/ID/reel.mp4 -af ebur128 -f null - 2>&1 | grep -A2 "Integrated"` → unos −14 LUFS.
- Saca fotogramas en 0,5 s, a mitad y 1 s antes del final y míralos con Read: gancho legible, subtítulos sincronizados y dentro de la zona segura, cierre visible.
- Si algo falla, corrige `props.json` o los cortes y vuelve a renderizar (máximo 2 veces).

## 6. Paquete
`publicar/ID/texto.txt`:
```
CAPTION:
...
HASHTAGS:
...
UBICACIÓN: (solo clientas: Vallecas, Madrid)
PALABRA CLAVE: (si la hay, y qué recurso enviar)
PORTADA: portada.png (elígela como portada del reel al publicar)
MÚSICA: añade un audio en tendencia desde la app, a volumen bajo
PUBLICAR: día y fecha del plan
```
Después: `python3 scripts/registro.py estado ID editada`.

## Errores típicos
- Subtítulos desfasados → transcribiste antes de cortar. Repite el paso 2.6.
- Texto tapado por los botones → revisa la zona segura en `brand.json`.
- Vídeo del móvil girado → mira `rotate` en ffprobe; ffmpeg lo aplica solo salvo que uses `-noautorotate`.
- Falla `transcribir.mjs` o el render por un problema de la plantilla → no la toques: devuelve el error exacto.
