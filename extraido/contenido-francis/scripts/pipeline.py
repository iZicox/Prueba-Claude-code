#!/usr/bin/env python3
"""Motor de la agencia automática de @francismangano.

El orquestador no decide de memoria qué toca: le pregunta a este script.
El script mira el registro, los archivos y config.json, avanza solo lo que es mecánico
(aprobaciones automáticas, brutos recibidos, publicaciones y métricas que deja Francis en entrada/)
y devuelve la lista de acciones para los agentes.

Uso:
  pipeline.py siguiente [--json]     # importa entrada/, avanza estados y lista las acciones de esta ronda
  pipeline.py bandeja                # escribe bandeja/HOY.md: lo que tiene que hacer Francis
  pipeline.py estado                 # una línea por pieza en marcha
  pipeline.py log "texto"            # el orquestador apunta lo que ha pasado
  pipeline.py error "texto"          # apunta un error técnico para el ingeniero
  pipeline.py errores [--limpiar]    # ver o vaciar los errores técnicos
  pipeline.py marcar entorno-listo   # el ingeniero confirma que Remotion y Playwright funcionan
  pipeline.py desbloquear ID         # reinicia revisiones e intentos de una pieza
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registro as R  # noqa: E402

RAIZ = R.RAIZ
CONFIG = RAIZ / "config.json"
AGENCIA = RAIZ / ".agencia"
ESTADO = AGENCIA / "estado.json"
ERRORES = AGENCIA / "errores.md"
ENTORNO_LISTO = AGENCIA / "entorno-listo"
ENTRADA = RAIZ / "entrada"
PROCESADO = ENTRADA / "procesado"
PLAN = RAIZ / "plan"
REVISIONES = RAIZ / "revisiones"
BANDEJA = RAIZ / "bandeja" / "HOY.md"

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
EXT_VIDEO = {".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".3gp"}
EN_MARCHA = ("propuesta", "elegida", "aprobado", "grabada", "editada")

PLANTILLAS = {
    "preguntas.md": "> Apunta aquí, una por línea, las preguntas reales de la semana (DMs, comentarios, clases, WhatsApp).\n"
                    "> Tal cual te las dijeron. El investigador las usa y luego se archivan solas.\n\n",
    "referencias.md": "> Pega aquí enlaces de reels o publicaciones que te llamaron la atención, con una línea de por qué.\n"
                      "> También noticias del sector. Se archivan solas tras la investigación.\n\n",
    "cambios.md": "> Pide cambios aquí, uno por línea, con el número de la pieza:\n"
                  ">   0012: el gancho más directo\n"
                  ">   0015: subtítulos más grandes\n"
                  "> Se procesan solos en la siguiente ejecución.\n\n",
    "aprobados.txt": "# Solo si config.json tiene \"aprobacion\": \"francis\". Un número de pieza por línea.\n",
    "publicadas.csv": "id,fecha\n",
    "metricas.csv": "id,vistas,comentarios,guardados,compartidos,dms\n",
}


# ---------------------------------------------------------------- utilidades

def cargar_config() -> dict:
    cfg = {"aprobacion": "automatica", "reparto": [], "carruseles_por_semana": 2,
           "ideas_por_investigacion": 15, "max_revisiones": 3, "max_reintentos_accion": 3,
           "formaciones_proximas": []}
    if CONFIG.exists():
        cfg.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8")).items()
                    if not k.startswith("_")})
    return cfg


def leer_estado() -> dict:
    if ESTADO.exists():
        try:
            return json.loads(ESTADO.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def guardar_estado(est: dict) -> None:
    AGENCIA.mkdir(parents=True, exist_ok=True)
    est["log"] = est.get("log", [])[-80:]
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ESTADO)


def apuntar(est: dict, texto: str) -> None:
    est.setdefault("log", []).append(f"{datetime.now():%Y-%m-%d %H:%M} {texto}")


def semana_de(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-{w:02d}"


def lunes_de(sem: str) -> date:
    y, w = sem.split("-")
    return date.fromisocalendar(int(y), int(w), 1)


def mtime(p: Path) -> float:
    """Fecha de modificación de un archivo, o la más reciente dentro de una carpeta."""
    if not p.exists():
        return 0.0
    if p.is_file():
        return p.stat().st_mtime
    tiempos = [f.stat().st_mtime for f in p.rglob("*") if f.is_file() and not f.name.startswith(".")]
    return max(tiempos) if tiempos else 0.0


def contenido_util(p: Path) -> str:
    """Texto del archivo sin las líneas de instrucciones (> o #) ni la cabecera CSV."""
    if not p.exists():
        return ""
    lineas = [l for l in p.read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.lstrip().startswith((">", "#"))]
    if p.suffix == ".csv" and lineas:
        lineas = lineas[1:]
    return "\n".join(lineas).strip()


def archivar_entrada(nombre: str) -> None:
    origen = ENTRADA / nombre
    if contenido_util(origen):
        PROCESADO.mkdir(parents=True, exist_ok=True)
        destino = PROCESADO / f"{datetime.now():%Y%m%d-%H%M%S}-{nombre}"
        shutil.copy(origen, destino)
    origen.write_text(PLANTILLAS[nombre], encoding="utf-8")


def asegurar_entrada() -> None:
    ENTRADA.mkdir(parents=True, exist_ok=True)
    for nombre, texto in PLANTILLAS.items():
        p = ENTRADA / nombre
        if not p.exists():
            p.write_text(texto, encoding="utf-8")


def veredicto(p: Path) -> str:
    m = re.search(r"VEREDICTO:\s*\**\s*([A-ZÁÉÍÓÚ]+)", p.read_text(encoding="utf-8")[:600]) if p.exists() else None
    return m.group(1).replace("Á", "A") if m else "SIN_VEREDICTO"


def revisiones(id_: str, clase: str) -> list:
    """Revisiones de un guion o un paquete, de la primera a la última."""
    res = []
    for p in REVISIONES.glob(f"{id_}-{clase}-v*.md"):
        m = re.search(r"-v(\d+)\.md$", p.name)
        if m:
            res.append({"n": int(m.group(1)), "ruta": p, "veredicto": veredicto(p), "mtime": mtime(p)})
    return sorted(res, key=lambda r: r["n"])


def archivar_revisiones(id_: str) -> int:
    destino = REVISIONES / "antiguas"
    n = 0
    for p in REVISIONES.glob(f"{id_}-*-v*.md"):
        destino.mkdir(parents=True, exist_ok=True)
        p.rename(destino / f"{datetime.now():%Y%m%d%H%M%S}-{p.name}")
        n += 1
    return n


def brutos(id_: str) -> list:
    carpeta = RAIZ / "brutos" / id_
    return sorted(f for f in carpeta.glob("*") if f.suffix.lower() in EXT_VIDEO) if carpeta.exists() else []


def paquete_completo(id_: str, tipo: str) -> bool:
    carpeta = RAIZ / "publicar" / id_
    if not (carpeta / "texto.txt").exists():
        return False
    if tipo == "reel":
        return (carpeta / "reel.mp4").exists()
    return len(list(carpeta.glob("*.png"))) >= 2


def leer_planes() -> dict:
    """Todas las piezas planificadas: id -> fila del plan (+ semana)."""
    planes = {}
    for p in sorted(PLAN.glob("semana-*.csv")):
        sem = p.stem.replace("semana-", "")
        for fila in R.leer(p):
            if fila.get("id"):
                fila = {k: (v or "").strip() for k, v in fila.items()}
                fila["semana"] = sem
                fila["tipo"] = "carrusel" if "carr" in fila.get("tipo", "").lower() else "reel"
                planes[fila["id"]] = fila
    return planes


def fechas_reparto(cfg: dict, sem: str) -> list:
    lunes = lunes_de(sem)
    filas = []
    for r in cfg["reparto"]:
        d = lunes + timedelta(days=DIAS.index(r["dia"]))
        filas.append({**r, "fecha": d.isoformat()})
    return filas


# ---------------------------------------------------------------- 1. importar lo que deja Francis

def importar(est: dict, avisos: list) -> None:
    asegurar_entrada()
    hoy = date.today().isoformat()

    for fila in R.leer(ENTRADA / "publicadas.csv"):
        id_ = (fila.get("id") or "").strip()
        if not id_:
            continue
        try:
            R.cambiar_estado(id_, "publicada", (fila.get("fecha") or hoy).strip())
            apuntar(est, f"#{id_} publicada")
        except R.ErrorRegistro as e:
            avisos.append(f"entrada/publicadas.csv: {e}")
    archivar_entrada("publicadas.csv")

    hubo_metricas = False
    for fila in R.leer(ENTRADA / "metricas.csv"):
        id_ = (fila.get("id") or "").strip()
        if not id_:
            continue
        try:
            R.fijar_metricas(id_, fila)
            hubo_metricas = True
            apuntar(est, f"#{id_} métricas")
        except R.ErrorRegistro as e:
            avisos.append(f"entrada/metricas.csv: {e}")
    archivar_entrada("metricas.csv")
    if hubo_metricas:
        est["metricas_nuevas_ts"] = time.time()

    for linea in contenido_util(ENTRADA / "aprobados.txt").splitlines():
        id_ = linea.strip().lstrip("#")
        if not id_:
            continue
        try:
            R.cambiar_estado(id_, "aprobado", nota="aprobado por Francis")
            apuntar(est, f"#{id_} aprobado por Francis")
        except R.ErrorRegistro as e:
            avisos.append(f"entrada/aprobados.txt: {e}")
    archivar_entrada("aprobados.txt")

    for linea in contenido_util(ENTRADA / "cambios.md").splitlines():
        m = re.match(r"^\s*#?([A-Za-z]?\d+)\s*[:\-–]\s*(.+)$", linea)
        if not m:
            avisos.append(f"entrada/cambios.md: no entiendo «{linea.strip()}». Usa «0012: lo que quieres cambiar».")
            continue
        id_, texto = m.group(1), m.group(2).strip()
        est.setdefault("cambios", {}).setdefault(id_, []).append({"texto": texto, "ts": time.time()})
        archivar_revisiones(id_)  # un cambio de Francis reinicia las rondas de revisión
        limpiar_intentos(est, id_)
        apuntar(est, f"#{id_} cambio pedido: {texto}")
    archivar_entrada("cambios.md")


def archivar_material_investigado(sem: str) -> None:
    ideas = RAIZ / "ideas" / f"semana-{sem}.md"
    if not ideas.exists():
        return
    for nombre in ("preguntas.md", "referencias.md"):
        p = ENTRADA / nombre
        if contenido_util(p) and mtime(p) < mtime(ideas):
            archivar_entrada(nombre)


# ---------------------------------------------------------------- 2. avanzar lo mecánico

def avanzar(cfg: dict, est: dict, planes: dict, avisos: list) -> None:
    filas = {f["id"]: f for f in R.leer(R.REGISTRO)}
    for id_, plan in planes.items():
        f = filas.get(id_)
        if not f:
            avisos.append(f"El plan de la semana {plan['semana']} incluye #{id_}, que no está en el registro.")
            continue
        st = f["estado"]
        guion = RAIZ / "guiones" / f"{id_}.md"
        try:
            if st == "propuesta":
                R.cambiar_estado(id_, "elegida", nota=f"plan semana {plan['semana']}")
                st = "elegida"
            if st == "elegida" and cfg["aprobacion"] == "automatica" and guion.exists():
                revs = revisiones(id_, "guion")
                if revs and revs[-1]["veredicto"] == "APROBADO" and revs[-1]["mtime"] >= mtime(guion):
                    R.cambiar_estado(id_, "aprobado", nota=f"aprobado por el revisor ({revs[-1]['ruta'].name})")
                    apuntar(est, f"#{id_} aprobado automáticamente")
                    st = "aprobado"
            if st == "aprobado" and plan["tipo"] == "reel" and brutos(id_):
                R.cambiar_estado(id_, "grabada")
                apuntar(est, f"#{id_} brutos recibidos")
                st = "grabada"
            if st in ("aprobado", "grabada") and paquete_completo(id_, plan["tipo"]):
                R.cambiar_estado(id_, "editada", nota="paquete detectado")
                st = "editada"
        except R.ErrorRegistro as e:
            avisos.append(str(e))


# ---------------------------------------------------------------- 3. decidir las acciones

def limpiar_intentos(est: dict, id_: str) -> None:
    est["intentos"] = {k: v for k, v in est.get("intentos", {}).items() if f":{id_}:" not in f"{k}:"}


class Ronda:
    def __init__(self, cfg, est, contar):
        self.cfg, self.est, self.contar = cfg, est, contar
        self.acciones, self.vistas = [], set()
        self.bandeja = {"grabar": [], "publicar": [], "aprobar": [], "bloqueadas": [], "en_marcha": []}

    def accion(self, clave: str, agente: str, prompt: str, id_: str = "") -> None:
        self.vistas.add(clave)
        intentos = self.est.setdefault("intentos", {})
        n = intentos.get(clave, 0)
        if n >= self.cfg["max_reintentos_accion"]:
            self.bloquear(id_ or "-", f"la acción «{clave}» de {agente} se intentó {n} veces sin avanzar", "")
            return
        if self.contar:
            intentos[clave] = n + 1
        self.acciones.append({"id": id_, "agente": agente, "clave": clave, "intento": n + 1, "prompt": prompt})

    def bloquear(self, id_: str, motivo: str, ruta: str) -> None:
        self.bandeja["bloqueadas"].append({"id": id_, "motivo": motivo, "ruta": ruta})

    def cerrar(self) -> None:
        if self.contar:
            self.est["intentos"] = {k: v for k, v in self.est.get("intentos", {}).items() if k in self.vistas}


def cambios_pendientes(est: dict, id_: str, desde: Path) -> list:
    """Cambios de Francis para una pieza que aún no se han aplicado al archivo `desde`."""
    lista = est.get("cambios", {}).get(id_, [])
    pendientes = [c for c in lista if c["ts"] > mtime(desde)]
    if lista and not pendientes:
        est["cambios"].pop(id_, None)
    return pendientes


def analizar(cfg: dict, est: dict, contar: bool = True) -> Ronda:
    hoy = date.today()
    r = Ronda(cfg, est, contar)
    max_rev = cfg["max_revisiones"]
    entorno_ok = ENTORNO_LISTO.exists()
    sem = semana_de(hoy + timedelta(days=7 - hoy.weekday()))  # se produce siempre para la semana siguiente

    # --- técnica
    if ERRORES.exists() and ERRORES.read_text(encoding="utf-8").strip():
        huella = hashlib.md5(ERRORES.read_bytes()).hexdigest()[:8]
        r.accion(f"arreglar:{huella}", "ingeniero",
                 "Hay errores técnicos en .agencia/errores.md (léelos con `python3 scripts/pipeline.py errores`). "
                 "Diagnostica, arregla scripts o plantillas y, cuando funcione, vacíalos con "
                 "`python3 scripts/pipeline.py errores --limpiar`.")
    if not entorno_ok:
        r.accion("montar", "ingeniero",
                 "Monta y verifica el entorno técnico siguiendo la skill plantilla-remotion: proyecto Remotion en video/ "
                 "con la composición ReelFrancis, transcripción local, Playwright para carruseles y un render de prueba. "
                 "Cuando todo funcione, ejecuta `python3 scripts/pipeline.py marcar entorno-listo`.")

    # --- investigación y planificación de la semana siguiente
    ideas = RAIZ / "ideas" / f"semana-{sem}.md"
    plan = PLAN / f"semana-{sem}.csv"
    lunes = lunes_de(sem)
    if not ideas.exists():
        r.accion(f"investigar:{sem}", "investigador",
                 f"Investiga para la semana {sem} ({lunes:%d/%m} a {lunes + timedelta(days=6):%d/%m}). "
                 f"Registra unas {cfg['ideas_por_investigacion']} ideas nuevas y escribe ideas/semana-{sem}.md. "
                 f"Material de Francis: entrada/preguntas.md y entrada/referencias.md (pueden estar vacíos). "
                 f"Reparto que hay que cubrir: " +
                 "; ".join(f"{x['dia']} {x['pilar']} ({x['publico']})" for x in cfg["reparto"]) + ".")
    elif not plan.exists():
        filas = fechas_reparto(cfg, sem)
        formaciones = [f for f in cfg.get("formaciones_proximas", []) if f]
        r.accion(f"planificar:{sem}", "estratega",
                 f"Planifica la semana {sem} a partir de ideas/semana-{sem}.md y escribe plan/semana-{sem}.csv "
                 f"con la cabecera `id,dia,fecha,tipo,pilar,formato`. Una fila por día:\n" +
                 "\n".join(f"- {x['dia']} {x['fecha']}: {x['pilar']} · {x['publico']} · {x['nota']}" for x in filas) +
                 f"\nExactamente {cfg['carruseles_por_semana']} filas con tipo carrusel; el resto, reel. "
                 f"Próximas formaciones: {', '.join(formaciones) if formaciones else 'ninguna'}.")

    # --- analítica
    ts = est.get("metricas_nuevas_ts")
    if ts:
        if mtime(RAIZ / "aprendizajes.md") > ts:
            est.pop("metricas_nuevas_ts", None)
        else:
            r.accion(f"aprendizajes:{int(ts)}", "analista",
                     "Hay métricas nuevas en el registro. Actualiza aprendizajes.md (tarea «aprendizajes» de tu definición).")
    mes = f"{hoy:%Y-%m}"
    if datetime.fromtimestamp(mtime(RAIZ / "temas-cubiertos.md")).strftime("%Y-%m") != mes:
        r.accion(f"resumen:{mes}", "analista",
                 f"Haz el resumen del mes {mes}: reescribe temas-cubiertos.md y aprendizajes.md "
                 "(tarea «resumen-mes» de tu definición).")

    # --- pieza a pieza
    planes = leer_planes()
    filas = {f["id"]: f for f in R.leer(R.REGISTRO)}
    por_grabar = {}
    for id_, pl in sorted(planes.items(), key=lambda x: x[1].get("fecha", "")):
        f = filas.get(id_)
        if not f or f["estado"] not in EN_MARCHA:
            continue
        st, tipo = f["estado"], pl["tipo"]
        guion = RAIZ / "guiones" / f"{id_}.md"
        paquete = RAIZ / "publicar" / id_
        etiqueta = f"#{id_} {tipo} · {pl.get('dia', '')} {pl.get('fecha', '')} · {f['tema']}"
        r.bandeja["en_marcha"].append(f"{etiqueta} · {st}")
        agente_pieza = "editor-video" if tipo == "reel" else "disenador-carruseles"

        # Cambios pedidos por Francis: van antes que nada
        destino = paquete if st == "editada" else guion
        pend = cambios_pendientes(est, id_, destino)
        if pend:
            texto = " / ".join(c["texto"] for c in pend)
            if st == "editada":
                if entorno_ok:
                    r.accion(f"cambio:{id_}:{int(pend[-1]['ts'])}", agente_pieza,
                             f"Francis pide estos cambios en el paquete publicar/{id_}/ de la pieza #{id_}: «{texto}». "
                             f"Aplícalos (si cambian el texto, actualiza también guiones/{id_}.md) y vuelve a exportar.", id_)
                continue
            if st in ("elegida", "aprobado"):
                r.accion(f"cambio:{id_}:{int(pend[-1]['ts'])}", "guionista",
                         f"Francis pide estos cambios en el guion guiones/{id_}.md (#{id_}): «{texto}». "
                         f"Aplícalos sin tocar lo demás.", id_)
                continue
            # en grabada, el editor los recibe en su encargo (abajo)

        if st == "elegida":
            if not guion.exists():
                r.accion(f"guion:{id_}", "guionista",
                         f"Escribe el guion de la pieza #{id_} ({tipo}) en guiones/{id_}.md. "
                         f"Se publica el {pl.get('dia', '')} {pl.get('fecha', '')}. "
                         f"Datos: `python3 scripts/registro.py ver {id_}`.", id_)
                continue
            revs = revisiones(id_, "guion")
            ultima = revs[-1] if revs else None
            if ultima and ultima["veredicto"] == "APROBADO" and ultima["mtime"] >= mtime(guion):
                if cfg["aprobacion"] == "francis":
                    r.bandeja["aprobar"].append({"id": id_, "texto": etiqueta, "ruta": f"guiones/{id_}.md"})
                continue
            if len(revs) >= max_rev:
                r.bloquear(id_, f"el guion no pasó la revisión tras {len(revs)} rondas",
                           str(ultima["ruta"].relative_to(RAIZ)))
                continue
            if not ultima or ultima["mtime"] < mtime(guion):
                n = len(revs) + 1
                r.accion(f"revisar-guion:{id_}:v{n}", "revisor",
                         f"Revisa el guion guiones/{id_}.md (#{id_}, {tipo}). "
                         f"Escribe tu veredicto en revisiones/{id_}-guion-v{n}.md.", id_)
            else:
                r.accion(f"corregir-guion:{id_}:v{ultima['n']}", "guionista",
                         f"Corrige guiones/{id_}.md (#{id_}) según la revisión {ultima['ruta'].relative_to(RAIZ)}. "
                         f"Cambia solo lo que pide.", id_)
            continue

        if st == "aprobado":
            if tipo == "carrusel":
                if entorno_ok:
                    r.accion(f"carrusel:{id_}", "disenador-carruseles",
                             f"Maqueta y exporta el carrusel #{id_} a partir de guiones/{id_}.md. "
                             f"Deja el paquete en publicar/{id_}/.", id_)
            else:
                hoja = RAIZ / "grabacion" / f"semana-{pl['semana']}.md"
                if hoja.exists() and re.search(rf"\b{re.escape(id_)}\b", hoja.read_text(encoding="utf-8")):
                    r.bandeja["grabar"].append({"id": id_, "texto": etiqueta,
                                                "ruta": str(hoja.relative_to(RAIZ))})
                else:
                    por_grabar.setdefault(pl["semana"], []).append(id_)
            continue

        if st == "grabada":
            if not entorno_ok:
                continue
            extra = ""
            pend = cambios_pendientes(est, id_, paquete)
            if pend:
                extra = " Francis pide además: «" + " / ".join(c["texto"] for c in pend) + "»."
            r.accion(f"editar:{id_}", "editor-video",
                     f"Edita el reel #{id_}: brutos en brutos/{id_}/, guion en guiones/{id_}.md. "
                     f"Deja el paquete en publicar/{id_}/.{extra}", id_)
            continue

        if st == "editada":
            revs = revisiones(id_, "paquete")
            ultima = revs[-1] if revs else None
            pm = mtime(paquete)
            if ultima and ultima["veredicto"] == "APROBADO" and ultima["mtime"] >= pm:
                r.bandeja["publicar"].append({"id": id_, "texto": etiqueta, "fecha": pl.get("fecha", ""),
                                              "ruta": f"publicar/{id_}/"})
                continue
            if len(revs) >= max_rev:
                r.bloquear(id_, f"el paquete no pasó la revisión tras {len(revs)} rondas",
                           str(ultima["ruta"].relative_to(RAIZ)))
                continue
            if not ultima or ultima["mtime"] < pm:
                n = len(revs) + 1
                r.accion(f"revisar-paquete:{id_}:v{n}", "revisor",
                         f"Revisa el paquete publicar/{id_}/ (#{id_}, {tipo}) contra guiones/{id_}.md. "
                         f"Escribe tu veredicto en revisiones/{id_}-paquete-v{n}.md.", id_)
            elif entorno_ok:
                r.accion(f"corregir-paquete:{id_}:v{ultima['n']}", agente_pieza,
                         f"Corrige el paquete publicar/{id_}/ (#{id_}) según la revisión "
                         f"{ultima['ruta'].relative_to(RAIZ)}.", id_)

    for s, ids in por_grabar.items():
        r.accion(f"hoja:{s}:{'-'.join(ids)}", "productor",
                 f"Prepara la hoja de grabación grabacion/semana-{s}.md con los reels {', '.join('#' + i for i in ids)}. "
                 f"Si la hoja ya existe, añade estos sin borrar los que ya estaban.")

    r.cerrar()
    return r


# ---------------------------------------------------------------- 4. bandeja de Francis

def escribir_bandeja(r: Ronda, cfg: dict, avisos: list) -> str:
    hoy = date.today()
    b = r.bandeja
    L = [f"# Bandeja de Francis · {hoy:%d/%m/%Y}", ""]

    def seccion(titulo, items, linea, pie=""):
        if not items:
            return
        L.extend([f"## {titulo}", ""])
        L.extend(linea(i) for i in items)
        if pie:
            L.extend(["", pie])
        L.append("")

    publicar = sorted(b["publicar"], key=lambda x: x["fecha"] or "9999")

    def cuando(x):
        if not x["fecha"]:
            return ""
        d = date.fromisoformat(x["fecha"])
        return " · **HOY**" if d == hoy else (" · **atrasada**" if d < hoy else f" · {d:%d/%m}")

    seccion("Para publicar", publicar,
            lambda x: f"- {x['texto']}{cuando(x)} → `{x['ruta']}` (vídeo o imágenes + `texto.txt` para copiar)",
            "Cuando publiques, añade una línea a `entrada/publicadas.csv`: `0012,2026-11-16`")
    seccion("Para grabar", b["grabar"], lambda x: f"- {x['texto']} → hoja `{x['ruta']}`",
            "Deja los archivos de cada pieza en `brutos/NÚMERO/` (por ejemplo `brutos/0012/toma.mov`). "
            "La edición empieza sola en la siguiente ejecución.")
    seccion("Para aprobar", b["aprobar"], lambda x: f"- {x['texto']} → `{x['ruta']}`",
            "Escribe el número en `entrada/aprobados.txt` o pide cambios en `entrada/cambios.md`.")

    pendientes = []
    for f in R.leer(R.REGISTRO):
        fp = R.fecha(f.get("fecha_publicacion", ""))
        if f["estado"] == "publicada" and fp and not f.get("vistas") and (hoy - fp).days >= 7:
            pendientes.append(f"- #{f['id']} · {f['tema']} · publicada el {fp:%d/%m}")
    if pendientes:
        L.extend(["## Métricas pendientes (7 días después de publicar)", "", *pendientes, "",
                  "Copia las cifras de Insights en `entrada/metricas.csv`: "
                  "`id,vistas,comentarios,guardados,compartidos,dms`", ""])

    seccion("Paradas: necesitan tu decisión", b["bloqueadas"],
            lambda x: (f"- #{x['id']}: " if x["id"] != "-" else "- General: ") + x["motivo"] +
                      (f" → `{x['ruta']}`" if x["ruta"] else ""),
            "Para desbloquear: pide el cambio en `entrada/cambios.md`, apruébala en `entrada/aprobados.txt`, "
            "vuelve a intentarlo con `/reintentar NÚMERO` (o `/reintentar todo`) o descártala con `/descartar NÚMERO`.")
    seccion("Avisos", avisos, lambda x: f"- {x}")
    seccion("En marcha", b["en_marcha"], lambda x: f"- {x}")
    if not ENTORNO_LISTO.exists():
        L.extend(["> El entorno técnico aún no está verificado: el ingeniero lo monta en la siguiente ejecución.", ""])
    if len(L) <= 2:
        L.append("Nada pendiente para ti. La agencia sigue trabajando.")
    texto = "\n".join(L).rstrip() + "\n"
    BANDEJA.parent.mkdir(parents=True, exist_ok=True)
    BANDEJA.write_text(texto, encoding="utf-8")
    return texto


# ---------------------------------------------------------------- CLI

def preparar(cfg, est):
    avisos = []
    importar(est, avisos)
    hoy = date.today()
    sem = semana_de(hoy + timedelta(days=7 - hoy.weekday()))
    archivar_material_investigado(sem)
    avanzar(cfg, est, leer_planes(), avisos)
    return avisos


def cmd_siguiente(a):
    cfg, est = cargar_config(), leer_estado()
    avisos = preparar(cfg, est)
    r = analizar(cfg, est, contar=True)
    est["ultima_ronda"] = datetime.now().isoformat(timespec="seconds")
    est["avisos"] = avisos
    guardar_estado(est)
    escribir_bandeja(r, cfg, avisos)
    if a.json:
        print(json.dumps({"acciones": r.acciones, "avisos": avisos,
                          "bloqueadas": r.bandeja["bloqueadas"]}, ensure_ascii=False, indent=1))
        return
    if not r.acciones:
        print("SIN ACCIONES: no hay nada que lanzar en esta ronda.")
    for x in r.acciones:
        print(f"[{x['agente']}] {x['clave']} (intento {x['intento']})\n    {x['prompt']}")
    for x in avisos:
        print(f"AVISO: {x}")


def cmd_bandeja(a):
    cfg, est = cargar_config(), leer_estado()
    r = analizar(cfg, est, contar=False)
    print(escribir_bandeja(r, cfg, est.get("avisos", [])))


def cmd_estado(a):
    cfg, est = cargar_config(), leer_estado()
    r = analizar(cfg, est, contar=False)
    for linea in r.bandeja["en_marcha"] or ["No hay piezas en marcha."]:
        print(linea)
    for x in r.bandeja["bloqueadas"]:
        print(f"PARADA #{x['id']}: {x['motivo']}")
    print(f"Entorno técnico: {'listo' if ENTORNO_LISTO.exists() else 'sin verificar'} · "
          f"aprobación: {cfg['aprobacion']} · última ronda: {est.get('ultima_ronda', 'nunca')}")


def cmd_log(a):
    est = leer_estado()
    apuntar(est, a.texto)
    guardar_estado(est)
    print("OK")


def cmd_error(a):
    AGENCIA.mkdir(parents=True, exist_ok=True)
    with ERRORES.open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.now():%Y-%m-%d %H:%M} {a.texto}\n")
    print("Error apuntado para el ingeniero.")


def cmd_errores(a):
    if a.limpiar:
        if ERRORES.exists():
            PROCESADO.mkdir(parents=True, exist_ok=True)
            with (AGENCIA / "errores-resueltos.md").open("a", encoding="utf-8") as f:
                f.write(ERRORES.read_text(encoding="utf-8"))
            ERRORES.unlink()
        print("Errores vaciados.")
    else:
        print(ERRORES.read_text(encoding="utf-8") if ERRORES.exists() else "Sin errores.")


def cmd_marcar(a):
    if a.que != "entorno-listo":
        sys.exit("Solo se puede marcar: entorno-listo")
    AGENCIA.mkdir(parents=True, exist_ok=True)
    ENTORNO_LISTO.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    print("Entorno marcado como listo.")


def cmd_desbloquear(a):
    est = leer_estado()
    if a.id == "todo":
        est["intentos"] = {}
        apuntar(est, "todas las acciones desbloqueadas")
        guardar_estado(est)
        print("Todas las acciones desbloqueadas (las revisiones se conservan).")
        return
    n = archivar_revisiones(a.id)
    limpiar_intentos(est, a.id)
    apuntar(est, f"#{a.id} desbloqueada")
    guardar_estado(est)
    print(f"#{a.id} desbloqueada ({n} revisiones archivadas).")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("siguiente"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_siguiente)
    sub.add_parser("bandeja").set_defaults(fn=cmd_bandeja)
    sub.add_parser("estado").set_defaults(fn=cmd_estado)
    s = sub.add_parser("log"); s.add_argument("texto"); s.set_defaults(fn=cmd_log)
    s = sub.add_parser("error"); s.add_argument("texto"); s.set_defaults(fn=cmd_error)
    s = sub.add_parser("errores"); s.add_argument("--limpiar", action="store_true"); s.set_defaults(fn=cmd_errores)
    s = sub.add_parser("marcar"); s.add_argument("que"); s.set_defaults(fn=cmd_marcar)
    s = sub.add_parser("desbloquear"); s.add_argument("id"); s.set_defaults(fn=cmd_desbloquear)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
