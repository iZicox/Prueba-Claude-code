#!/usr/bin/env python3
"""Registro de ideas de @francismangano.

Única puerta de entrada a registro-ideas.csv y archivo/*.csv.
Imprime solo lo necesario para que los agentes gasten pocos tokens.

Uso rápido:
  registro.py buscar "texto libre" [--top 5]
  registro.py nuevo --tema ... --angulo ... --gancho ... --pilar tecnica --publico manicuristas --formato "Mito o realidad" [--cta CALOR] [--fuente ...] [--etiquetas "a;b"] [--remix-de ID] [--estado propuesta]
  registro.py ver ID
  registro.py estado ID NUEVO_ESTADO [--fecha AAAA-MM-DD] [--forzar]
  registro.py metricas ID --vistas N [--comentarios N] [--guardados N] [--compartidos N] [--dms N]
  registro.py listar [--estado elegida] [--pilar tecnica] [--limite 20]
  registro.py pendientes          # publicadas hace 7+ días sin métricas
  registro.py ganadoras           # piezas que doblan la mediana de su pilar y se pueden rehacer
  registro.py resumen [--semanas 8]
  registro.py archivar --anio 2025
"""
import argparse
import csv
import difflib
import re
import statistics
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REGISTRO = RAIZ / "registro-ideas.csv"
ARCHIVO = RAIZ / "archivo"

COLUMNAS = [
    "id", "fecha_alta", "tema", "angulo", "gancho", "pilar", "publico", "formato",
    "cta", "fuente", "etiquetas", "estado", "fecha_publicacion",
    "vistas", "comentarios", "guardados", "compartidos", "dms", "remix_de", "notas",
]
PILARES = ["tecnica", "duran", "negocio", "camino", "actualidad"]
PUBLICOS = ["manicuristas", "clientas", "ambos"]
ESTADOS = ["propuesta", "elegida", "aprobado", "grabada", "editada", "publicada", "descartada"]
# Estado nuevo -> estados desde los que se puede llegar
TRANSICIONES = {
    "propuesta": {"propuesta"},
    "elegida": {"propuesta", "descartada"},
    "aprobado": {"elegida"},
    "grabada": {"aprobado"},
    "editada": {"aprobado", "grabada"},  # un carrusel no necesita grabación
    "publicada": {"editada"},
    "descartada": set(ESTADOS) - {"publicada"},
}
SEMANAS_REMIX = 6        # una ganadora se puede rehacer a partir de 6 semanas
UMBRAL_DUPLICADA = 0.60
UMBRAL_PARECIDA = 0.35

STOP = set("""a al algo como con cual cuando de del desde donde el ella en entre es esa ese eso esta este esto
estas estos hay la las le les lo los mas me mi mis muy no nos o para pero por que se si sin sobre su sus te
tu tus un una uno unos unas y ya yo the tu te ti asi tan mas hace hacer tiene tienes son""".split())


# ---------- utilidades ----------

def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", texto.lower())


def raices(texto: str) -> set:
    """Palabras significativas recortadas a 6 letras (levanta ~ levantamiento)."""
    return {p[:6] for p in normalizar(texto).split() if len(p) > 2 and p not in STOP}


def texto_busqueda(fila: dict) -> str:
    return " ".join([fila.get("tema", ""), fila.get("angulo", ""), fila.get("gancho", ""),
                     fila.get("etiquetas", "").replace(";", " ")])


def similitud(a: str, b: str) -> float:
    ra, rb = raices(a), raices(b)
    if not ra or not rb:
        return 0.0
    solape = len(ra & rb) / min(len(ra), len(rb))
    jaccard = len(ra & rb) / len(ra | rb)
    secuencia = difflib.SequenceMatcher(None, " ".join(sorted(ra)), " ".join(sorted(rb))).ratio()
    return round(0.5 * solape + 0.3 * jaccard + 0.2 * secuencia, 2)


def leer(ruta: Path) -> list:
    if not ruta.exists():
        return []
    with ruta.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def escribir(ruta: Path, filas: list) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        for fila in filas:
            w.writerow({c: fila.get(c, "") for c in COLUMNAS})
    tmp.replace(ruta)


def todas() -> list:
    filas = leer(REGISTRO)
    for archivo in sorted(ARCHIVO.glob("*.csv")):
        filas += leer(archivo)
    return filas


def fecha(txt: str):
    try:
        return datetime.strptime(txt.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def num(txt: str):
    try:
        return int(float(str(txt).replace(".", "").replace(",", ".")))
    except (ValueError, TypeError):
        return None


def linea(f: dict, extra: str = "") -> str:
    vistas = f" · {f['vistas']} vistas" if f.get("vistas") else ""
    pub = f" · pub {f['fecha_publicacion']}" if f.get("fecha_publicacion") else ""
    return (f"#{f['id']} [{f['estado']}] {f['pilar']}/{f['formato']} · {f['tema']} — {f['angulo']}"
            f"{pub}{vistas}{extra}")


def buscar_fila(filas: list, id_: str):
    for f in filas:
        if f["id"].lower() == id_.lower():
            return f
    return None


def siguiente_id(filas: list) -> str:
    nums = [int(f["id"]) for f in filas if f["id"].isdigit()]
    return f"{(max(nums) + 1) if nums else 1:04d}"


def parecidas(texto: str, filas: list, top: int, excluir: str = ""):
    puntuadas = []
    for f in filas:
        if f["id"] == excluir:
            continue
        s = similitud(texto, texto_busqueda(f))
        if s >= UMBRAL_PARECIDA:
            puntuadas.append((s, f))
    puntuadas.sort(key=lambda x: -x[0])
    return puntuadas[:top]


def salir(msg: str, codigo: int = 1):
    print(msg, file=sys.stderr if codigo else sys.stdout)
    sys.exit(codigo)


# ---------- comandos ----------

def cmd_buscar(a):
    res = parecidas(a.texto, todas(), a.top)
    if not res:
        print("SIN COINCIDENCIAS: idea nueva.")
        return
    for s, f in res:
        etiqueta = "DUPLICADA" if s >= UMBRAL_DUPLICADA else "PARECIDA"
        print(f"{etiqueta} {s:.2f} {linea(f)}")


def cmd_nuevo(a):
    if a.pilar not in PILARES:
        salir(f"Pilar no válido. Usa uno de: {', '.join(PILARES)}")
    if a.publico not in PUBLICOS:
        salir(f"Público no válido. Usa uno de: {', '.join(PUBLICOS)}")
    if a.estado not in ("propuesta", "elegida", "descartada"):
        salir("Una idea nueva entra como propuesta, elegida o descartada.")
    filas = leer(REGISTRO)
    historico = todas()
    nueva = {
        "id": "", "fecha_alta": date.today().isoformat(), "tema": a.tema, "angulo": a.angulo,
        "gancho": a.gancho, "pilar": a.pilar, "publico": a.publico, "formato": a.formato,
        "cta": (a.cta or "").upper(), "fuente": a.fuente or "", "etiquetas": a.etiquetas or "",
        "estado": a.estado, "remix_de": a.remix_de or "", "notas": a.notas or "",
    }
    res = parecidas(texto_busqueda(nueva), historico, 3)
    if a.remix_de:
        original = buscar_fila(historico, a.remix_de)
        if not original:
            salir(f"No existe la idea #{a.remix_de}.")
        if original["estado"] != "publicada":
            salir(f"#{a.remix_de} no está publicada: no se puede rehacer.")
        fp = fecha(original.get("fecha_publicacion", ""))
        if fp and (date.today() - fp).days < SEMANAS_REMIX * 7:
            salir(f"#{a.remix_de} se publicó hace menos de {SEMANAS_REMIX} semanas. Espera.")
        if similitud(a.gancho, original.get("gancho", "")) >= UMBRAL_DUPLICADA:
            salir("El gancho del remix es casi igual al original. Cámbialo.")
        res = [(s, f) for s, f in res if f["id"] != original["id"] and f.get("remix_de") != original["id"]]
    duplicadas = [(s, f) for s, f in res if s >= UMBRAL_DUPLICADA]
    if duplicadas and not a.forzar:
        print("NO REGISTRADA: se parece demasiado a:")
        for s, f in duplicadas:
            print(f"  {s:.2f} {linea(f)}")
        print("Cambia el ángulo, márcala como remix con --remix-de ID o usa --forzar si Francis lo pide.")
        sys.exit(2)
    nueva["id"] = siguiente_id(historico)
    filas.append(nueva)
    escribir(REGISTRO, filas)
    print(f"REGISTRADA #{nueva['id']} ({nueva['estado']})")
    for s, f in res:
        if s < UMBRAL_DUPLICADA:
            print(f"  aviso, parecida {s:.2f}: {linea(f)}")


def cmd_ver(a):
    f = buscar_fila(todas(), a.id)
    if not f:
        salir(f"No existe #{a.id}.")
    for c in COLUMNAS:
        if f.get(c):
            print(f"{c}: {f[c]}")


class ErrorRegistro(ValueError):
    pass


def cambiar_estado(id_: str, estado: str, fecha_pub: str = None, nota: str = None, forzar: bool = False) -> str:
    """Cambia el estado de una idea respetando las transiciones. Lo usan este CLI y pipeline.py."""
    if estado not in ESTADOS:
        raise ErrorRegistro(f"Estado no válido. Usa uno de: {', '.join(ESTADOS)}")
    filas = leer(REGISTRO)
    f = buscar_fila(filas, id_)
    if not f:
        raise ErrorRegistro(f"#{id_} no está en el registro activo.")
    if f["estado"] not in TRANSICIONES[estado] and not forzar:
        raise ErrorRegistro(f"#{id_} está en '{f['estado']}': no puede pasar a '{estado}'. "
                            f"Necesita estar en: {', '.join(sorted(TRANSICIONES[estado]))}.")
    f["estado"] = estado
    if estado == "publicada":
        f["fecha_publicacion"] = fecha_pub or date.today().isoformat()
    if nota:
        f["notas"] = (f.get("notas", "") + " | " + nota).strip(" |")
    escribir(REGISTRO, filas)
    return f"OK #{f['id']} → {estado}"


def fijar_metricas(id_: str, valores: dict) -> str:
    filas = leer(REGISTRO)
    f = buscar_fila(filas, id_)
    if not f:
        raise ErrorRegistro(f"#{id_} no está en el registro activo.")
    for campo in ("vistas", "comentarios", "guardados", "compartidos", "dms"):
        if valores.get(campo) not in (None, ""):
            f[campo] = str(num(valores[campo]) if num(valores[campo]) is not None else valores[campo])
    escribir(REGISTRO, filas)
    return f"OK métricas #{f['id']}: " + ", ".join(
        f"{c}={f[c]}" for c in ("vistas", "comentarios", "guardados", "compartidos", "dms") if f.get(c))


def cmd_estado(a):
    try:
        print(cambiar_estado(a.id, a.estado, a.fecha, a.nota, a.forzar))
    except ErrorRegistro as e:
        salir(str(e))


def cmd_metricas(a):
    try:
        print(fijar_metricas(a.id, {c: getattr(a, c) for c in
                                    ("vistas", "comentarios", "guardados", "compartidos", "dms")}))
    except ErrorRegistro as e:
        salir(str(e))


def cmd_listar(a):
    filas = leer(REGISTRO)
    if a.estado:
        filas = [f for f in filas if f["estado"] == a.estado]
    if a.pilar:
        filas = [f for f in filas if f["pilar"] == a.pilar]
    for f in filas[-a.limite:]:
        print(linea(f))
    if not filas:
        print("Nada que listar.")


def cmd_pendientes(a):
    hoy = date.today()
    hay = False
    for f in leer(REGISTRO):
        fp = fecha(f.get("fecha_publicacion", ""))
        if f["estado"] == "publicada" and fp and not f.get("vistas") and (hoy - fp).days >= 7:
            print(linea(f, f" · hace {(hoy - fp).days} días"))
            hay = True
    if not hay:
        print("No hay métricas pendientes.")


def medianas(filas: list) -> dict:
    por_pilar = {}
    for f in filas:
        v = num(f.get("vistas"))
        if f["estado"] == "publicada" and v is not None:
            por_pilar.setdefault(f["pilar"], []).append(v)
    return {p: statistics.median(vs) for p, vs in por_pilar.items() if vs}


def cmd_ganadoras(a):
    filas = todas()
    med = medianas(filas)
    rehechas = {f["remix_de"] for f in filas if f.get("remix_de") and f["estado"] != "descartada"}
    hoy = date.today()
    hay = False
    for f in filas:
        v = num(f.get("vistas"))
        m = med.get(f["pilar"])
        if v is None or not m or v < 2 * m:
            continue
        fp = fecha(f.get("fecha_publicacion", ""))
        semanas = (hoy - fp).days // 7 if fp else None
        if f["id"] in rehechas:
            situacion = "ya rehecha"
        elif semanas is not None and semanas < SEMANAS_REMIX:
            situacion = f"esperar ({semanas} sem)"
        else:
            situacion = "LISTA PARA REHACER"
        print(linea(f, f" · x{v / m:.1f} mediana · {situacion}"))
        hay = True
    if not hay:
        print("Aún no hay ganadoras (o faltan métricas).")
    if med:
        print("Medianas por pilar: " + ", ".join(f"{p}={int(m)}" for p, m in sorted(med.items())))


def cmd_resumen(a):
    filas = todas()
    hoy = date.today()
    recientes = []
    for f in filas:
        if f["estado"] == "publicada":
            ref = fecha(f.get("fecha_publicacion", ""))  # sin fecha (histórico) no cuenta como reciente
        elif f["estado"] in ("elegida", "aprobado", "grabada", "editada"):
            ref = fecha(f.get("fecha_alta", "")) or hoy
        else:
            continue
        if ref and (hoy - ref).days <= a.semanas * 7:
            recientes.append(f)
    print(f"Total ideas: {len(filas)} · " + ", ".join(
        f"{e}={sum(1 for f in filas if f['estado'] == e)}" for e in ESTADOS if any(f['estado'] == e for f in filas)))
    print(f"Últimas {a.semanas} semanas (en producción o publicadas): {len(recientes)}")
    for p in PILARES:
        del_pilar = [f for f in recientes if f["pilar"] == p]
        if del_pilar:
            formatos = {}
            for f in del_pilar:
                formatos[f["formato"]] = formatos.get(f["formato"], 0) + 1
            print(f"  {p}: {len(del_pilar)} · " + ", ".join(f"{k} {n}" for k, n in formatos.items()))
    etiquetas = {}
    for f in recientes:
        for e in filter(None, (x.strip().lower() for x in f.get("etiquetas", "").split(";"))):
            etiquetas[e] = etiquetas.get(e, 0) + 1
    repetidas = [f"{e} ({n})" for e, n in sorted(etiquetas.items(), key=lambda x: -x[1]) if n >= 2]
    if repetidas:
        print("Etiquetas más usadas (posible saturación): " + ", ".join(repetidas[:10]))


def cmd_archivar(a):
    filas = leer(REGISTRO)
    quedan, salen = [], []
    for f in filas:
        fp = fecha(f.get("fecha_publicacion", "")) or fecha(f.get("fecha_alta", ""))
        if f["estado"] in ("publicada", "descartada") and fp and fp.year == a.anio:
            salen.append(f)
        else:
            quedan.append(f)
    if not salen:
        print(f"Nada que archivar de {a.anio}.")
        return
    destino = ARCHIVO / f"{a.anio}.csv"
    escribir(destino, leer(destino) + salen)
    escribir(REGISTRO, quedan)
    print(f"Archivadas {len(salen)} ideas en archivo/{a.anio}.csv. Quedan {len(quedan)} en el registro.")


def main():
    p = argparse.ArgumentParser(description="Registro de ideas de @francismangano")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("buscar"); s.add_argument("texto"); s.add_argument("--top", type=int, default=5)
    s.set_defaults(fn=cmd_buscar)

    s = sub.add_parser("nuevo")
    for campo in ("tema", "angulo", "gancho", "pilar", "publico", "formato"):
        s.add_argument(f"--{campo}", required=True)
    for campo in ("cta", "fuente", "etiquetas", "remix-de", "notas"):
        s.add_argument(f"--{campo}")
    s.add_argument("--estado", default="propuesta")
    s.add_argument("--forzar", action="store_true")
    s.set_defaults(fn=cmd_nuevo)

    s = sub.add_parser("ver"); s.add_argument("id"); s.set_defaults(fn=cmd_ver)

    s = sub.add_parser("estado"); s.add_argument("id"); s.add_argument("estado")
    s.add_argument("--fecha"); s.add_argument("--nota"); s.add_argument("--forzar", action="store_true")
    s.set_defaults(fn=cmd_estado)

    s = sub.add_parser("metricas"); s.add_argument("id")
    for campo in ("vistas", "comentarios", "guardados", "compartidos", "dms"):
        s.add_argument(f"--{campo}", type=int)
    s.set_defaults(fn=cmd_metricas)

    s = sub.add_parser("listar"); s.add_argument("--estado"); s.add_argument("--pilar")
    s.add_argument("--limite", type=int, default=20); s.set_defaults(fn=cmd_listar)

    sub.add_parser("pendientes").set_defaults(fn=cmd_pendientes)
    sub.add_parser("ganadoras").set_defaults(fn=cmd_ganadoras)

    s = sub.add_parser("resumen"); s.add_argument("--semanas", type=int, default=8)
    s.set_defaults(fn=cmd_resumen)

    s = sub.add_parser("archivar"); s.add_argument("--anio", type=int, required=True)
    s.set_defaults(fn=cmd_archivar)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
