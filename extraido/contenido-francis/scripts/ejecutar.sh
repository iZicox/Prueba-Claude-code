#!/bin/bash
# Lanza un ciclo completo de la agencia sin intervención: el orquestador pregunta al motor
# qué toca, llama a los agentes y deja bandeja/HOY.md al día.
#
# Uso:   scripts/ejecutar.sh
# Lo llama launchd (Mac) o cron dos veces al día. Ver README.md.

set -u
cd "$(dirname "$0")/.." || exit 1
RAIZ="$(pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"

mkdir -p logs .agencia
LOG="logs/ciclo-$(date +%Y%m%d-%H%M).log"

# --- Un solo ciclo a la vez
CANDADO=".agencia/ejecutando"
if ! mkdir "$CANDADO" 2>/dev/null; then
  if [ -n "$(find "$CANDADO" -maxdepth 0 -mmin +240 2>/dev/null)" ]; then
    rmdir "$CANDADO"; mkdir "$CANDADO"   # candado de un ciclo que murió hace más de 4 h
  else
    echo "$(date) Ya hay un ciclo en marcha. Salgo." >> logs/agencia.log
    exit 0
  fi
fi
trap 'rmdir "$CANDADO" 2>/dev/null' EXIT

# --- Credenciales: la suscripción de Claude (Pro/Max), nunca una API key olvidada
unset ANTHROPIC_API_KEY
TOKEN_FILE="$HOME/.config/agencia-francis/token"
if [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && [ -f "$TOKEN_FILE" ]; then
  export CLAUDE_CODE_OAUTH_TOKEN="$(cat "$TOKEN_FILE")"
fi

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude)}"
if [ -z "$CLAUDE_BIN" ]; then
  echo "$(date) No encuentro claude en el PATH." >> logs/agencia.log
  exit 1
fi

echo "$(date) Ciclo iniciado" >> logs/agencia.log
"$CLAUDE_BIN" -p "Ejecuta un ciclo completo de la agencia." \
  --agent orquestador \
  --permission-mode acceptEdits \
  --max-turns 400 \
  --output-format text \
  > "$LOG" 2>&1
CODIGO=$?
echo "$(date) Ciclo terminado (código $CODIGO) → $LOG" >> logs/agencia.log

# --- Bandeja y aviso
python3 scripts/pipeline.py bandeja > /dev/null 2>&1
RESUMEN="$(grep -E '^## ' bandeja/HOY.md | sed 's/## //' | paste -sd '·' - | cut -c1-180)"
[ -z "$RESUMEN" ] && RESUMEN="Nada pendiente para ti"
[ $CODIGO -ne 0 ] && RESUMEN="El ciclo terminó con errores. Mira $LOG"

if command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"$RESUMEN\" with title \"Agencia @francismangano\" subtitle \"Abre bandeja/HOY.md\"" 2>/dev/null
elif command -v notify-send >/dev/null 2>&1; then
  notify-send "Agencia @francismangano" "$RESUMEN" 2>/dev/null
fi

# Logs de más de 30 días fuera
find logs -name 'ciclo-*.log' -mtime +30 -delete 2>/dev/null
exit $CODIGO
