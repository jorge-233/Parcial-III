"""Formula de dano, efectividad de tipos y precision.

Reciben el generador aleatorio como parametro para poder fijar la semilla en las pruebas.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from app.game.models import NIVEL, Combatiente, Movimiento, LIMITE_ETAPA

PROB_CRITICO = 1 / 24
PROB_CRITICO_ALTO = 1 / 8
MULT_CRITICO = 1.5
MULT_STAB = 1.5
FORCEJEO = "forcejeo"


@dataclass(frozen=True)
class ResultadoDano:
    dano: int
    efectividad: float
    critico: bool
    stab: bool


def efectividad(tipo_mov: str, tipos_defensor, tabla: dict) -> float:
    """Multiplicador total del movimiento contra los tipos del defensor."""
    mult = 1.0
    for tipo in tipos_defensor:
        mult *= tabla.get(tipo_mov, {}).get(tipo, 1.0)
    return mult


def calcular_dano(atacante: Combatiente, defensor: Combatiente, mov: Movimiento,
                  tabla: dict, rng=None, critico: bool | None = None,
                  azar: float | None = None) -> ResultadoDano:
    """Calcula el dano de un movimiento.

    `critico` y `azar` permiten forzar esos valores (util en las pruebas).
    Siempre se consumen dos numeros del rng para que la secuencia sea estable.
    """
    rng = rng or random
    sin_tipo = mov.id == FORCEJEO       # Forcejeo no tiene tipo
    stab = mov.tipo in atacante.tipos and not sin_tipo

    if mov.categoria == "estado" or not mov.poder:
        return ResultadoDano(0, 1.0, False, False)

    efect = 1.0 if sin_tipo else efectividad(mov.tipo, defensor.tipos, tabla)
    if efect == 0:
        return ResultadoDano(0, 0.0, False, stab)

    prob = PROB_CRITICO_ALTO if mov.alto_critico else PROB_CRITICO
    es_critico = rng.random() < prob
    factor_azar = rng.randint(85, 100) / 100
    if critico is not None:
        es_critico = critico
    if azar is not None:
        factor_azar = azar

    if mov.categoria == "fisico":
        ataque = atacante.stat_efectivo("ataque")
        defensa = defensor.stat_efectivo("defensa")
    else:
        ataque = atacante.stat_efectivo("atq_esp")
        defensa = defensor.stat_efectivo("def_esp")

    base = ((2 * NIVEL // 5 + 2) * mov.poder * ataque // defensa) // 50 + 2
    total = base * factor_azar * efect
    if stab:
        total *= MULT_STAB
    if es_critico:
        total *= MULT_CRITICO
    return ResultadoDano(max(1, int(total)), efect, es_critico, stab)


def acierta(mov: Movimiento, atacante: Combatiente, defensor: Combatiente, rng=None) -> bool:
    """Decide si el movimiento acierta, usando precision y evasion."""
    if mov.precision is None:
        return True
    rng = rng or random
    neto = atacante.etapas["precision"] - defensor.etapas["evasion"]
    neto = max(-LIMITE_ETAPA, min(LIMITE_ETAPA, neto))
    mult = (3 + neto) / 3 if neto >= 0 else 3 / (3 - neto)
    return rng.random() * 100 < mov.precision * mult
