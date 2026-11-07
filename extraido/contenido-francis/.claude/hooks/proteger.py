#!/usr/bin/env python3
"""Hook PreToolUse de la agencia.

1. Impide leer o editar el registro de ideas a mano: se usa scripts/registro.py.
   Así el registro puede crecer sin gastar tokens.
2. Impide modificar o borrar los brutos de Francis (brutos/): se trabaja con copias.
3. Impide que los agentes publiquen o abran redes sociales.
4. Con --solo-escribir PREFIJO (hook del revisor), solo deja escribir dentro de ese prefijo.

Exit 2 = bloquea la herramienta y el mensaje de stderr le llega a Claude.
"""
import json
import os
import re
import sys


def bloquear(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


try:
    datos = json.load(sys.stdin)
except Exception:
    sys.exit(0)

herramienta = datos.get("tool_name", "")
entrada = datos.get("tool_input", {}) or {}
ruta = str(entrada.get("file_path") or entrada.get("notebook_path") or entrada.get("path") or "")
comando = str(entrada.get("command") or "")
url = str(entrada.get("url") or "")

# 4. Escritura limitada (revisor)
if "--solo-escribir" in sys.argv and herramienta in ("Write", "Edit", "MultiEdit"):
    prefijo = sys.argv[sys.argv.index("--solo-escribir") + 1]
    raiz = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    relativa = os.path.relpath(os.path.abspath(os.path.join(raiz, ruta)), raiz)
    if not relativa.startswith(prefijo.rstrip("/") + "/"):
        bloquear(f"Bloqueado: este agente solo puede escribir en {prefijo}")

# 1. Registro
REGISTRO = re.compile(r"(registro-ideas\.csv|archivo/[^\s'\"]*\.csv)")
MENSAJE_REGISTRO = (
    "Bloqueado: el registro de ideas no se lee ni se edita directamente. "
    "Usa `python3 scripts/registro.py` (buscar, ver, nuevo, estado, metricas, listar, resumen). "
    "Para contexto general lee temas-cubiertos.md y aprendizajes.md."
)
if herramienta in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit") and REGISTRO.search(ruta):
    bloquear(MENSAJE_REGISTRO)
if herramienta == "Bash" and REGISTRO.search(comando) and not re.search(r"scripts/(registro|pipeline)\.py", comando):
    bloquear(MENSAJE_REGISTRO)

# 2. Brutos
if herramienta in ("Edit", "Write", "MultiEdit") and re.search(r"(^|/)brutos/", ruta):
    bloquear("Bloqueado: los brutos de Francis no se modifican. Trabaja con copias en video/public/.")
if herramienta == "Bash" and re.search(r"\b(rm|mv|truncate)\b[^|;&]*brutos/", comando):
    bloquear("Bloqueado: los brutos no se mueven ni se borran.")

# 3. Nada de publicar
REDES = re.compile(r"(instagram\.com|graph\.facebook\.com|tiktok\.com/.*(post|upload)|api\.metricool)", re.I)
if herramienta in ("WebFetch",) and REDES.search(url) and re.search(r"(upload|publish|media_publish)", url, re.I):
    bloquear("Bloqueado: la agencia no publica. Francis publica a mano.")
if herramienta == "Bash" and REDES.search(comando) and re.search(r"\b(curl|wget|http)\b", comando):
    bloquear("Bloqueado: la agencia no publica ni llama a APIs de redes. Francis publica a mano.")

sys.exit(0)
