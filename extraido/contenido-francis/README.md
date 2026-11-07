# Agencia automática de @francismangano

Agencia de contenido operada por agentes de Claude Code. Un **orquestador** pregunta al motor
qué toca y lanza a **9 agentes** especializados: investigador, estratega, guionista, revisor,
productor, editor de vídeo, diseñador de carruseles, analista e ingeniero.
Funciona con la suscripción de Claude (Pro o Max) y se ejecuta sola dos veces al día en tu Mac.

**Lo único que hace Francis:** grabar con la hoja que le preparan y publicar a mano.
Todo lo que tiene que hacer aparece en `bandeja/HOY.md` (y en una notificación del Mac).

```
          launchd 08:10 y 19:40
                   │
             ejecutar.sh ──► orquestador ──► pipeline.py "¿qué toca?"
                                 │
   ┌──────────┬──────────┬───────┼────────┬──────────┬───────────┬──────────┐
investigador estratega guionista revisor productor editor-video diseñador analista
                                 │                                         ingeniero
                      bandeja/HOY.md ◄── Francis graba / publica / entrada/
```

## Instalación (una vez, unos 30 minutos)

1. **Requisitos:** Claude Code con sesión iniciada con tu suscripción, Node 18+, Python 3.10+ y ffmpeg.
   En Mac: `brew install node python ffmpeg`.
2. **Descomprime** esta carpeta donde quieras trabajar (por ejemplo, `~/Agencia`) y entra en ella.
3. **Plugin oficial de Remotion** (lo usan el ingeniero y el editor):
   ```
   claude plugin marketplace add remotion-dev/claude-code-plugin
   claude plugin install remotion@remotion
   ```
4. **Marca:** cambia `brand.json` y las variables `:root` de `.claude/skills/carrusel/plantilla.html`
   por los colores, fuentes y logo reales de Francis.
5. **Recursos:** en `.claude/skills/voz-marca/recursos.md`, deja solo las palabras clave cuyo recurso ya existe.
6. **Primer ciclo, contigo delante:** `claude` dentro de la carpeta y escribe `/ciclo`.
   El ingeniero montará Remotion y Playwright, y el investigador hará la primera investigación.
   Acepta los permisos que pida esta primera vez.
7. **Token para que funcione sin ti** (dura un año):
   ```
   claude setup-token
   mkdir -p ~/.config/agencia-francis
   pbpaste > ~/.config/agencia-francis/token    # tras copiar el token que te muestra
   chmod 600 ~/.config/agencia-francis/token
   ```
8. **Programarlo** (dentro de la carpeta del proyecto):
   ```
   chmod +x scripts/ejecutar.sh
   sed "s#RUTA_DEL_PROYECTO#$(pwd)#g" scripts/com.francismangano.agencia.plist > ~/Library/LaunchAgents/com.francismangano.agencia.plist
   launchctl load ~/Library/LaunchAgents/com.francismangano.agencia.plist
   ```
   Prueba manual: `scripts/ejecutar.sh` y mira `logs/`.
   Para pararlo: `launchctl unload ~/Library/LaunchAgents/com.francismangano.agencia.plist`.

El Mac tiene que estar encendido (si está dormido a la hora programada, el ciclo se lanza al despertar).
Cada ciclo gasta del mismo límite de uso que tu suscripción.

## La semana, sin tocar nada

| Cuándo | Qué pasa solo | Qué hace Francis |
| --- | --- | --- |
| Primer ciclo de la semana | Investigación y plan de la **semana siguiente** | — |
| Mismo día | 5 guiones escritos, revisados y aprobados por el revisor | — |
| Mismo día | Hoja de grabación de los reels; carruseles terminados | — |
| Cuando ella quiera | — | Graba con `grabacion/semana-*.md` y deja los vídeos en `brutos/NÚMERO/` |
| Siguiente ciclo | Edición, revisión y paquete en `publicar/NÚMERO/` | — |
| Día de publicación | — | Publica desde la app con `texto.txt` y añade `NÚMERO,fecha` a `entrada/publicadas.csv` |
| 7 días después | — | Copia las cifras de Insights en `entrada/metricas.csv` |
| Siguiente ciclo | La analista actualiza los aprendizajes | — |
| Cada mes | Resumen de temas cubiertos, saturados y huecos | — |

## La carpeta `entrada/` (el buzón de Francis)

| Archivo | Para qué |
| --- | --- |
| `preguntas.md` | Preguntas reales de clientas y alumnas. Las mejores ideas salen de aquí |
| `referencias.md` | Enlaces o noticias que le gustaron |
| `cambios.md` | `0012: el gancho más directo`: se aplica solo en el siguiente ciclo |
| `aprobados.txt` | Solo si quiere aprobar ella (`config.json` → `"aprobacion": "francis"`) o desbloquear una pieza |
| `publicadas.csv` | `0012,2026-11-16` cuando publica |
| `metricas.csv` | `0012,1850,42,60,9,15` a los 7 días |

Desde Claude Code también puede usar los comandos `/pregunta`, `/cambio`, `/aprobar`, `/publicado`,
`/metricas`, `/descartar`, `/reintentar`, `/estado` y `/ciclo`.

## Control de calidad sin humanos

- **Revisor:** aprueba cada guion y cada paquete (mira fotogramas del vídeo y los PNG). Si pide cambios, el guionista o el editor corrigen. Tras 3 rondas sin aprobar, la pieza se para y aparece en la bandeja.
- **Motor:** si una acción se repite 3 veces sin avanzar, la para.
- **Ingeniero:** cuando falla algo técnico, el error queda apuntado y el ingeniero lo arregla en el siguiente turno.
- **Hooks:** ningún agente puede leer el registro entero, tocar los brutos ni publicar en redes.
- ¿Prefieres aprobar tú los guiones? `config.json` → `"aprobacion": "francis"`.

## Cómo no se repiten ideas

Toda idea pasa por `registro.py buscar` antes de proponerse y `registro.py nuevo` se niega a registrar duplicadas.
Las ganadoras (el doble de la mediana de su pilar) se pueden rehacer a partir de 6 semanas, con otro gancho, como remix.
El registro nunca se lee entero, así que crece sin gastar más tokens.

## Qué hay en cada sitio

| Ruta | Para qué |
| --- | --- |
| `CLAUDE.md` | Reglas y línea de producción |
| `config.json` | Modo de aprobación, reparto semanal, carruseles por semana, límites de revisión, formaciones |
| `.claude/agents/` | Orquestador + 9 agentes |
| `.claude/skills/` | voz-marca, guion, registro-ideas, edicion-remotion, plantilla-remotion, carrusel |
| `.claude/commands/` | Comandos para Francis |
| `scripts/pipeline.py` | Motor: estado de cada pieza y siguiente acción |
| `scripts/registro.py` | Única puerta al registro de ideas |
| `scripts/ejecutar.sh` + `.plist` | Ejecución programada |

## Pendiente de confirmar con Francis
Colores, fuentes y logo · qué recursos de palabra clave existen · fechas de formaciones (`config.json`) · fechas exactas de las piezas históricas.
