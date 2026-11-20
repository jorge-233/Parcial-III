"""Carga y valida los datos del juego desde los archivos JSON."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.game.models import Entrenador, Especie, Movimiento

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Datos:
    especies: dict
    movimientos: dict
    tabla_tipos: dict
    tipos: list
    entrenadores: dict
    jugador: dict


def _leer(nombre: str, directorio: Path):
    with open(directorio / nombre, encoding="utf-8") as f:
        return json.load(f)


def cargar_datos(directorio: Path | None = None) -> Datos:
    directorio = directorio or DATA_DIR
    chart = _leer("type_chart.json", directorio)
    tipos = chart["tipos"]

    movimientos = {}
    for mid, m in _leer("moves.json", directorio).items():
        if m["tipo"] not in tipos:
            raise ValueError(f"Movimiento '{mid}' tiene un tipo desconocido: {m['tipo']}")
        movimientos[mid] = Movimiento(
            id=mid, nombre=m["nombre"], tipo=m["tipo"], categoria=m["categoria"],
            poder=m["poder"], precision=m["precision"], prioridad=m["prioridad"],
            alto_critico=m["alto_critico"], efectos=tuple(m["efectos"]),
            pp=m.get("pp"))

    especies = {}
    for slug, p in _leer("pokemon.json", directorio).items():
        for t in p["tipos"]:
            if t not in tipos:
                raise ValueError(f"'{slug}' tiene un tipo desconocido: {t}")
        for mid in p["movimientos"]:
            if mid not in movimientos:
                raise ValueError(f"'{slug}' usa un movimiento inexistente: {mid}")
        especies[slug] = Especie(
            slug=slug, id=p["id"], nombre=p["nombre"], tipos=tuple(p["tipos"]),
            stats_base=p["stats"], movimientos=tuple(p["movimientos"]), sprite=p["sprite"])

    entrenadores = {}
    for e in _leer("entrenadores.json", directorio):
        entrenadores[e["slug"]] = Entrenador(
            slug=e["slug"], nombre=e["nombre"], relacion=e["relacion"],
            saludo=e["saludo"], victoria=e["victoria"], derrota=e["derrota"],
            sprite=e["sprite"], color=e.get("color", "#d93a3a"))

    return Datos(especies=especies, movimientos=movimientos,
                 tabla_tipos=chart["efectividad"], tipos=tipos, entrenadores=entrenadores,
                 jugador=_leer("jugador.json", directorio))
