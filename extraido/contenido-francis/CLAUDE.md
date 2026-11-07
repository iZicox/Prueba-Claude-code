# Agencia de contenido automática de @francismangano

Este proyecto es una agencia de contenido operada por agentes de Claude Code para @francismangano
(nail artist y formadora latina en Vallecas, Madrid). Produce reels y carruseles sin intervención:
el orquestador lanza a los agentes, el revisor aprueba y el motor lleva el estado.

Francis solo hace lo que no puede hacer una IA: **grabar** y **publicar** (a mano, decisión suya),
y deja lo que sabe en `entrada/`. Todo lo que tiene que hacer está en `bandeja/HOY.md`.

## Cómo funciona

- La sesión principal es el agente `orquestador` (`.claude/settings.json` → `agent`).
- El orquestador **no decide de memoria**: pregunta a `python3 scripts/pipeline.py siguiente --json`
  qué acciones tocan, las lanza con los agentes y repite hasta que no queden.
- `scripts/ejecutar.sh` lanza un ciclo sin nadie delante; launchd lo ejecuta dos veces al día.
- Se produce siempre para la **semana siguiente**: investigación y plan una vez por semana,
  guiones, revisión y edición en cuanto se puede.

## Línea de producción

| Fase | Agente | Sale | El motor pasa a |
| --- | --- | --- | --- |
| Investigación | `investigador` | `ideas/semana-AAAA-SS.md` + ideas en el registro | `propuesta` |
| Plan | `estratega` | `plan/semana-AAAA-SS.csv` | `elegida` |
| Guion | `guionista` | `guiones/ID.md` | — |
| Revisión del guion | `revisor` | `revisiones/ID-guion-vN.md` | `aprobado` si APROBADO (modo automático) |
| Hoja de grabación (reels) | `productor` | `grabacion/semana-AAAA-SS.md` | — |
| Grabación | **Francis** | `brutos/ID/` | `grabada` |
| Edición (reels) | `editor-video` | `publicar/ID/reel.mp4` + `portada.png` + `texto.txt` | `editada` |
| Diseño (carruseles) | `disenador-carruseles` | `publicar/ID/*.png` + `texto.txt` | `editada` |
| Revisión del paquete | `revisor` | `revisiones/ID-paquete-vN.md` | listo para publicar |
| Publicación | **Francis** | línea en `entrada/publicadas.csv` | `publicada` |
| Métricas | **Francis** → `analista` | `entrada/metricas.csv` → `aprendizajes.md` | — |
| Resumen mensual | `analista` | `temas-cubiertos.md`, `aprendizajes.md` | — |
| Entorno técnico y errores | `ingeniero` | `video/` (ReelFrancis), scripts | `entorno-listo` |

## Reglas que no se rompen

- **El motor manda.** Los estados del registro los cambia `pipeline.py` (y los agentes de edición, a `editada`). Nadie aprueba a mano salvo Francis vía `entrada/aprobados.txt`.
- **Aprobación.** `config.json` → `"aprobacion": "automatica"`: el APROBADO del revisor deja avanzar la pieza. `"francis"`: espera a Francis.
- **Nada se publica desde aquí.** Ningún agente publica, programa ni abre redes sociales. Un hook lo bloquea.
- **El registro nunca se lee entero.** `registro-ideas.csv` y `archivo/*.csv` solo con `python3 scripts/registro.py` (un hook lo bloquea). Contexto general: `temas-cubiertos.md` y `aprendizajes.md`.
- **Nada se repite.** Toda idea se comprueba con `registro.py buscar` antes de registrarse; `registro.py nuevo` se niega a registrar duplicadas. Ver la skill `registro-ideas`.
- **Los brutos no se tocan.** Se trabaja con copias en `video/public/ID/`.
- **Voz de marca.** Todo texto para el público usa la skill `voz-marca`. Sin cifras inventadas ni promesas de ingresos.
- **Otras cuentas.** Se toma la pregunta, el formato y la estructura del gancho; nunca el texto, el guion ni el diseño.
- **Trabajo sin supervisión.** Ningún agente se queda esperando una respuesta: decide lo razonable, lo deja escrito y sigue. Lo que de verdad necesita a Francis va a la bandeja.
- **Errores técnicos** → `python3 scripts/pipeline.py error "..."`. El ingeniero los arregla en el siguiente turno.

## Carpetas

| Carpeta | Contenido | Quién escribe |
| --- | --- | --- |
| `entrada/` | preguntas, referencias, cambios, aprobados, publicadas, métricas | Francis |
| `bandeja/HOY.md` | Lo que tiene que hacer Francis | el motor |
| `ideas/` `plan/` `guiones/` `revisiones/` `grabacion/` | Trabajo de los agentes | agentes |
| `brutos/ID/` | Vídeos de Francis | Francis |
| `video/` | Proyecto Remotion y archivos de trabajo | ingeniero y editor |
| `carruseles/ID/` | HTML y PNG de trabajo | diseñador |
| `publicar/ID/` | Paquete final | editor y diseñador |
| `.agencia/` | Estado del motor, errores | el motor |
| `scripts/` | `pipeline.py`, `registro.py`, `render_carrusel.py`, `ejecutar.sh` | ingeniero |
