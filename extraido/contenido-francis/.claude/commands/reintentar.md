---
description: Desbloquea una pieza parada (reinicia sus revisiones e intentos) o todas las acciones paradas
argument-hint: ID | todo
---

1. `python3 scripts/pipeline.py desbloquear $ARGUMENTS`
2. Dile a Francis que se volverá a intentar en el siguiente ciclo y pregúntale si lo lanza ya con `/ciclo`.
   Si la pieza se paró por el revisor, sugiérele que antes pida el cambio que quiere con `/cambio`.
