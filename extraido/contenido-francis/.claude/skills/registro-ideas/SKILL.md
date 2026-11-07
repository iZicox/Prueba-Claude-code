---
name: registro-ideas
description: Cómo consultar y actualizar el registro de ideas de @francismangano sin leerlo entero y sin repetir contenido. Úsala siempre que propongas, elijas, cambies de estado, publiques o midas una idea.
---

# Registro de ideas

`registro-ideas.csv` es la memoria del sistema. **Nunca lo leas ni lo edites directamente** (un hook lo bloquea): todo pasa por `python3 scripts/registro.py`, que imprime solo las filas necesarias.

## Comandos
| Para | Comando |
| --- | --- |
| ¿Ya existe algo parecido? | `registro.py buscar "tema ángulo palabras clave"` |
| Registrar idea nueva | `registro.py nuevo --tema "..." --angulo "..." --gancho "..." --pilar tecnica --publico manicuristas --formato "Mito o realidad" --cta CALOR --fuente "DM alumna" --etiquetas "gel;calor;curado"` |
| Ver una idea | `registro.py ver 0012` |
| Cambiar estado | `registro.py estado 0012 aprobado` |
| Marcar publicada | `registro.py estado 0012 publicada --fecha 2026-11-09` |
| Métricas a los 7 días | `registro.py metricas 0012 --vistas 1850 --comentarios 42 --guardados 60 --compartidos 9 --dms 15` |
| Ideas en un estado | `registro.py listar --estado propuesta` |
| Métricas pendientes | `registro.py pendientes` |
| Ganadoras para rehacer | `registro.py ganadoras` |
| Resumen para el mes | `registro.py resumen --semanas 4` |
| Archivar un año | `registro.py archivar --anio 2026` |

Pilares: `tecnica`, `duran`, `negocio`, `camino`, `actualidad`. Públicos: `manicuristas`, `clientas`, `ambos`.
Estados: `propuesta` → `elegida` → `aprobado` → `grabada` → `editada` → `publicada`, o `descartada`.

## Cómo leer `buscar`
- `DUPLICADA 0.6+` → no la propongas. Cambia el ángulo de verdad (otra causa, otro público, otro formato) o descártala.
- `PARECIDA 0.35–0.6` → solo si el ángulo es claramente distinto. Dilo en la propuesta: "parecida a #0012, pero aquí...".
- `SIN COINCIDENCIAS` → idea nueva.
- `nuevo` comprueba solo y se niega a registrar duplicadas (sale con código 2). Nunca uses `--forzar`.
- Los estados `elegida`, `aprobado`, `grabada` y `publicada` los pone el motor (`scripts/pipeline.py`). Los agentes solo registran ideas nuevas (`nuevo`) y marcan `editada` al terminar un paquete.

## Reglas anti-repetición
1. Busca **por tema + ángulo + etiquetas**, no por título. Prueba también con sinónimos ("levanta", "despega", "adherencia").
2. Registra también las ideas descartadas, con estado `descartada`, para no volver a proponerlas.
3. **Remix de ganadoras:** una pieza que dobla la mediana de su pilar se puede rehacer a partir de 6 semanas, con otro gancho (y mejor otro formato). Se registra con `--remix-de ID`. `registro.py ganadoras` dice cuáles están listas.
4. Una pieza que queda por debajo de la mitad de la mediana no se repite; si el tema interesa, se prueba con otro ángulo.
5. Etiquetas: 3–5 palabras en minúscula separadas por `;`, del tema concreto (no "uñas" ni "manicura").

## Contexto barato
Para saber qué se ha cubierto, lee `temas-cubiertos.md` (1 página) y `aprendizajes.md` (máx. 30 líneas). No necesitas más.
