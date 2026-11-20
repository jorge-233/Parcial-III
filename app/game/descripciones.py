"""Descripcion en texto de cada movimiento, generada a partir de sus efectos."""
from __future__ import annotations

from app.game.models import Movimiento

VERBO_ESTADO = {"quemadura": "quemar", "paralisis": "paralizar", "sueno": "dormir",
                "congelado": "congelar"}
NOMBRE_STAT = {"ataque": "el Ataque", "defensa": "la Defensa", "atq_esp": "el Ataque Especial",
               "def_esp": "la Defensa Especial", "velocidad": "la Velocidad",
               "precision": "la Precisión", "evasion": "la Evasión"}


def _porcentaje(prob: float) -> str:
    return f"{round(prob * 100)} %"


def _efecto(e: dict, es_estado: bool) -> str:
    t = e["tipo"]
    if t == "estado":
        verbo = VERBO_ESTADO[e["estado"]]
        if es_estado or e["prob"] >= 1:
            return f"Intenta {verbo} al rival."
        return f"{_porcentaje(e['prob'])} de probabilidad de {verbo} al rival."
    if t == "stat":
        quien = "propio" if e["objetivo"] == "propio" else "del rival"
        cuanto = "mucho" if abs(e["etapas"]) >= 2 else ""
        accion = ("Sube" if e["etapas"] > 0 else "Baja") + (f" {cuanto}" if cuanto else "")
        texto = f"{accion} {NOMBRE_STAT[e['stat']]} {quien}."
        prob = e.get("prob", 1.0)
        if not es_estado and prob < 1:
            texto = f"{_porcentaje(prob)} de probabilidad: {texto[0].lower()}{texto[1:]}"
        return texto
    if t == "cura":
        return f"Recupera el {_porcentaje(e['fraccion'])} de sus PS máximos."
    if t == "descanso":
        return "Se duerme 2 turnos y recupera todos sus PS y se cura de cualquier estado."
    if t == "drenaje":
        return f"Recupera el {_porcentaje(e['fraccion'])} del daño causado."
    if t == "retroceso":
        return f"El usuario pierde el {_porcentaje(e['fraccion'])} del daño causado."
    if t == "retroceso_max":
        return f"El usuario pierde 1/4 de sus PS máximos."
    return ""


def describir(mov: Movimiento) -> str:
    """Texto corto con lo que hace el movimiento en combate."""
    partes = []
    if mov.id == "forcejeo":
        partes.append("Solo se usa cuando no quedan PP. No tiene tipo: afecta a todos.")
    elif mov.categoria != "estado":
        partes.append(f"Ataque {'físico' if mov.categoria == 'fisico' else 'especial'}.")
    if mov.prioridad > 0:
        partes.append("Ataca primero (prioridad +1).")
    if mov.alto_critico:
        partes.append("Alta probabilidad de golpe crítico.")
    es_estado = mov.categoria == "estado"
    partes += [_efecto(e, es_estado) for e in mov.efectos]
    return " ".join(p for p in partes if p)
