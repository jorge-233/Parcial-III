"""Especies, movimientos, entrenadores y combatientes."""
from __future__ import annotations

from dataclasses import dataclass, field

NIVEL = 50
IV = 31
LIMITE_ETAPA = 6

STATS = ("hp", "ataque", "defensa", "atq_esp", "def_esp", "velocidad")
ETAPAS = ("ataque", "defensa", "atq_esp", "def_esp", "velocidad", "precision", "evasion")


@dataclass(frozen=True)
class Movimiento:
    id: str
    nombre: str
    tipo: str
    categoria: str                  # "fisico", "especial" o "estado"
    poder: int | None = None
    precision: int | None = None    # None: no falla
    prioridad: int = 0
    alto_critico: bool = False
    efectos: tuple = ()
    pp: int | None = None


@dataclass(frozen=True)
class Especie:
    slug: str
    id: int                         # N.º de Pokédex
    nombre: str
    tipos: tuple
    stats_base: dict
    movimientos: tuple
    sprite: str


@dataclass(frozen=True)
class Entrenador:
    slug: str
    nombre: str
    relacion: str
    saludo: str
    victoria: str       # frase cuando gana el jugador
    derrota: str        # frase cuando pierde el jugador
    sprite: str
    color: str = "#d93a3a"


def calcular_stats(stats_base: dict) -> dict:
    """Estadisticas reales a nivel 50 (IV 31, sin EVs ni naturaleza)."""
    stats = {}
    for nombre, base in stats_base.items():
        parcial = (2 * base + IV) * NIVEL // 100
        stats[nombre] = parcial + NIVEL + 10 if nombre == "hp" else parcial + 5
    return stats


def multiplicador_etapa(etapa: int) -> float:
    """Multiplicador de ataque/defensa/velocidad segun la etapa (-6 a +6)."""
    etapa = max(-LIMITE_ETAPA, min(LIMITE_ETAPA, etapa))
    return (2 + etapa) / 2 if etapa >= 0 else 2 / (2 - etapa)


@dataclass
class Combatiente:
    """Un Pokemon dentro de un combate."""
    especie: Especie
    movimientos: list
    stats: dict
    hp: int
    etapas: dict = field(default_factory=lambda: {e: 0 for e in ETAPAS})
    estado: str | None = None       # quemadura, paralisis, sueno o congelado
    contador_sueno: int = 0
    pp: list = field(default_factory=list)

    @classmethod
    def crear(cls, especie: Especie, movimientos_por_id: dict) -> "Combatiente":
        stats = calcular_stats(especie.stats_base)
        movs = [movimientos_por_id[m] for m in especie.movimientos]
        return cls(especie=especie, movimientos=movs, stats=stats, hp=stats["hp"],
                   pp=[m.pp for m in movs])

    def tiene_pp(self, indice: int) -> bool:
        return self.pp[indice] is None or self.pp[indice] > 0

    @property
    def sin_pp(self) -> bool:
        return not any(self.tiene_pp(i) for i in range(len(self.movimientos)))

    def gastar_pp(self, mov: "Movimiento") -> None:
        for i, m in enumerate(self.movimientos):
            if m is mov and self.pp[i] is not None:
                self.pp[i] = max(0, self.pp[i] - 1)
                return

    @property
    def nombre(self) -> str:
        return self.especie.nombre

    @property
    def tipos(self) -> tuple:
        return self.especie.tipos

    @property
    def hp_max(self) -> int:
        return self.stats["hp"]

    @property
    def debilitado(self) -> bool:
        return self.hp <= 0

    def stat_efectivo(self, stat: str) -> int:
        valor = int(self.stats[stat] * multiplicador_etapa(self.etapas[stat]))
        if stat == "ataque" and self.estado == "quemadura":
            valor //= 2
        if stat == "velocidad" and self.estado == "paralisis":
            valor //= 2
        return max(1, valor)

    def cambiar_etapa(self, stat: str, delta: int) -> int:
        """Devuelve cuanto cambio realmente (el limite es +-6)."""
        actual = self.etapas[stat]
        nuevo = max(-LIMITE_ETAPA, min(LIMITE_ETAPA, actual + delta))
        self.etapas[stat] = nuevo
        return nuevo - actual

    def reiniciar_etapas(self) -> None:
        self.etapas = {e: 0 for e in ETAPAS}

    def recibir_dano(self, cantidad: int) -> int:
        perdido = min(self.hp, max(0, cantidad))
        self.hp -= perdido
        return perdido

    def curar(self, cantidad: int) -> int:
        ganado = min(self.hp_max - self.hp, max(0, cantidad))
        self.hp += ganado
        return ganado
