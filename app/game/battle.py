"""Motor de combate por turnos.

Orden de un turno: acciones (por prioridad y velocidad), quemadura y debilitados.
Todo lo que pasa queda en `Batalla.pasos` (texto, animacion y estado de la escena)
para que la pagina lo reproduzca en orden.
"""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field

from app.game.damage import acierta, calcular_dano, efectividad
from app.game.models import Combatiente, Entrenador

MAX_EQUIPO = 6
PROB_PARALISIS = 0.25
PROB_DESCONGELAR = 0.2
FRACCION_QUEMADURA = 1 / 16
PROB_RIVAL_AL_AZAR = 0.2
# Generador aparte para estimar dano sin alterar el azar del combate
_RNG_ESTIMACION = random.Random(0)

NOMBRES_STAT = {
    "ataque": "El Ataque", "defensa": "La Defensa", "atq_esp": "El Ataque Esp.",
    "def_esp": "La Defensa Esp.", "velocidad": "La Velocidad",
    "precision": "La Precisión", "evasion": "La Evasión",
}
TEXTO_ESTADO = {"quemadura": "se quemó", "paralisis": "quedó paralizado", "sueno": "se durmió",
                "congelado": "quedó congelado"}
INMUNIDAD_ESTADO = {"quemadura": "fuego", "paralisis": "electrico", "congelado": "hielo"}


@dataclass
class Lado:
    nombre: str
    equipo: list
    activo: int = 0
    en_campo: bool = True

    @property
    def pokemon(self) -> Combatiente:
        return self.equipo[self.activo]

    def disponibles(self) -> list:
        return [i for i, c in enumerate(self.equipo) if not c.debilitado]

    @property
    def derrotado(self) -> bool:
        return not self.disponibles()


@dataclass
class Batalla:
    id: str
    jugador: Lado
    rival: Lado
    entrenador: Entrenador
    tabla: dict
    rng: random.Random
    equipo_slugs: list
    turno: int = 0
    ultimo: list = field(default_factory=list)
    historial: list = field(default_factory=list)
    pasos: list = field(default_factory=list)
    escena_inicial: dict = field(default_factory=dict)
    pasos_nuevos: bool = False
    forcejeo: object = None
    debe_cambiar: bool = False
    ganador: str | None = None      # "jugador" o "rival"

    @property
    def terminada(self) -> bool:
        return self.ganador is not None


# ---------------------------------------------------------------- creacion
def _validar_equipo(datos, slugs: list) -> None:
    if not slugs:
        raise ValueError("Elige al menos 1 Pokémon para tu equipo.")
    if len(slugs) > MAX_EQUIPO:
        raise ValueError(f"Tu equipo puede tener como máximo {MAX_EQUIPO} Pokémon.")
    if len(set(slugs)) != len(slugs):
        raise ValueError("No puedes repetir Pokémon en tu equipo.")
    for slug in slugs:
        if slug not in datos.especies:
            raise ValueError(f"El Pokémon '{slug}' no existe.")


def crear_batalla(datos, equipo_slugs, rng=None, rival_slugs=None, excluir=None) -> Batalla:
    """El rival es un entrenador al azar con la misma cantidad de Pokemon que el jugador."""
    equipo_slugs = list(equipo_slugs)
    _validar_equipo(datos, equipo_slugs)
    rng = rng or random.Random()

    if rival_slugs is None:
        rival_slugs = rng.sample(sorted(datos.especies), len(equipo_slugs))
    candidatos = [e for e in datos.entrenadores.values() if e.slug != excluir]
    entrenador = rng.choice(candidatos or list(datos.entrenadores.values()))

    def armar(slugs):
        return [Combatiente.crear(datos.especies[s], datos.movimientos) for s in slugs]

    b = Batalla(
        id=uuid.uuid4().hex[:8], jugador=Lado("Tú", armar(equipo_slugs)),
        rival=Lado(entrenador.nombre, armar(rival_slugs)), entrenador=entrenador,
        tabla=datos.tabla_tipos, rng=rng, equipo_slugs=equipo_slugs,
        forcejeo=datos.movimientos.get("forcejeo"))

    b.jugador.en_campo = b.rival.en_campo = False
    _iniciar_accion(b)
    _decir(b, f"¡{entrenador.nombre} quiere combatir!", {"tipo": "presentacion"})
    _decir(b, f"{entrenador.nombre}: «{entrenador.saludo}»")
    b.rival.en_campo = True
    _decir(b, f"{entrenador.nombre} envía a {_corto(b.rival.pokemon)}.",
           {"tipo": "entrada", "lado": "rival"})
    b.jugador.en_campo = True
    _decir(b, f"¡Adelante, {_corto(b.jugador.pokemon)}!", {"tipo": "entrada", "lado": "jugador"})
    return b


def revancha(datos, b: Batalla, rng=None) -> Batalla:
    """Mismo equipo, con la vida restaurada, contra otro entrenador."""
    return crear_batalla(datos, b.equipo_slugs, rng=rng, excluir=b.entrenador.slug)


# ---------------------------------------------------------------- pasos
def _corto(c: Combatiente) -> str:
    return c.nombre.split(" (")[0]


def _nombre(b: Batalla, c: Combatiente) -> str:
    return f"{_corto(c)} rival" if _lado(b, c) == "rival" else _corto(c)


def _lado(b: Batalla, c: Combatiente) -> str:
    return "rival" if any(c is x for x in b.rival.equipo) else "jugador"


def _foto_lado(lado: Lado) -> dict:
    c = lado.pokemon
    return {
        "nombre": _corto(c), "slug": c.especie.slug, "sprite": c.especie.sprite,
        "hp": c.hp, "hp_max": c.hp_max, "estado": c.estado, "debilitado": c.debilitado,
        "en_campo": lado.en_campo, "activo": lado.activo,
        "equipo": [{"slug": x.especie.slug, "debilitado": x.debilitado,
                    "hp": x.hp, "hp_max": x.hp_max} for x in lado.equipo],
        "etapas": {k: v for k, v in c.etapas.items() if v != 0},
    }


def foto(b: Batalla) -> dict:
    return {"jugador": _foto_lado(b.jugador), "rival": _foto_lado(b.rival)}


def _iniciar_accion(b: Batalla) -> None:
    b.ultimo = []
    b.pasos = []
    b.escena_inicial = foto(b)
    b.pasos_nuevos = True


def _paso(b: Batalla, texto: str | None, anim: dict | None) -> None:
    b.pasos.append({"texto": texto, "anim": anim, "escena": foto(b)})


def _decir(b: Batalla, texto: str, anim: dict | None = None) -> None:
    b.ultimo.append(texto)
    b.historial.append({"turno": b.turno, "texto": texto})
    _paso(b, texto, anim)


def _animar(b: Batalla, anim: dict) -> None:
    _paso(b, None, anim)


# ---------------------------------------------------------------- estados y efectos
def intentar_estado(b: Batalla, objetivo: Combatiente, estado: str) -> bool:
    if objetivo.debilitado or objetivo.estado is not None:
        return False
    if INMUNIDAD_ESTADO.get(estado) in objetivo.tipos:
        return False
    objetivo.estado = estado
    if estado == "sueno":
        objetivo.contador_sueno = b.rng.randint(1, 3)
    _decir(b, f"¡{_nombre(b, objetivo)} {TEXTO_ESTADO[estado]}!",
           {"tipo": "estado", "lado": _lado(b, objetivo), "estado": estado})
    return True


def _bloqueado_por_tipo(mov, defensor, tabla) -> bool:
    """Onda Trueno respeta la inmunidad de tipo (no afecta a los de Tierra)."""
    return efectividad(mov.tipo, defensor.tipos, tabla) == 0 and any(
        e.get("estado") == "paralisis" for e in mov.efectos)


def _debilitado(b: Batalla, c: Combatiente) -> None:
    _decir(b, f"¡{_nombre(b, c)} se debilitó!", {"tipo": "debilitado", "lado": _lado(b, c)})


def _aplicar_efecto(b, efecto, mov, atac, defe, dano) -> None:
    tipo = efecto["tipo"]
    es_estado = mov.categoria == "estado"
    n_atac, n_def = _nombre(b, atac), _nombre(b, defe)

    if tipo == "estado":
        if defe.debilitado:
            return
        if not es_estado and b.rng.random() >= efecto["prob"]:
            return
        if not intentar_estado(b, defe, efecto["estado"]) and es_estado:
            _decir(b, "¡Pero falló!")

    elif tipo == "stat":
        objetivo = atac if efecto["objetivo"] == "propio" else defe
        if objetivo.debilitado:
            return
        prob = efecto.get("prob", 1.0)
        if not es_estado and prob < 1 and b.rng.random() >= prob:
            return
        cambio = objetivo.cambiar_etapa(efecto["stat"], efecto["etapas"])
        sube = efecto["etapas"] > 0
        nombre = NOMBRES_STAT[efecto["stat"]]
        if cambio == 0:
            _decir(b, f"¡{nombre} de {_nombre(b, objetivo)} no puede {'subir' if sube else 'bajar'} más!")
        else:
            intensidad = " mucho" if abs(cambio) >= 2 else ""
            _decir(b, f"¡{nombre} de {_nombre(b, objetivo)} {'subió' if sube else 'bajó'}{intensidad}!",
                   {"tipo": "stat", "lado": _lado(b, objetivo), "sube": sube})

    elif tipo == "cura":
        if atac.curar(max(1, int(atac.hp_max * efecto["fraccion"]))):
            _decir(b, f"¡{n_atac} recuperó salud!", {"tipo": "cura", "lado": _lado(b, atac)})
        else:
            _decir(b, "¡Pero falló!")

    elif tipo == "descanso":
        if atac.hp == atac.hp_max or atac.estado == "sueno":
            _decir(b, "¡Pero falló!")
        else:
            atac.curar(atac.hp_max)
            atac.estado, atac.contador_sueno = "sueno", 2
            _decir(b, f"¡{n_atac} se durmió y recuperó toda su salud!",
                   {"tipo": "cura", "lado": _lado(b, atac)})

    elif tipo == "drenaje" and dano > 0:
        atac.curar(max(1, int(dano * efecto["fraccion"])))
        _decir(b, f"¡{n_atac} absorbió energía de {n_def}!", {"tipo": "cura", "lado": _lado(b, atac)})

    elif tipo in ("retroceso", "retroceso_max") and dano > 0:
        base = atac.hp_max if tipo == "retroceso_max" else dano
        perdido = atac.recibir_dano(max(1, int(base * efecto["fraccion"])))
        _decir(b, f"¡{n_atac} sufre daño por el retroceso!",
               {"tipo": "dano", "lado": _lado(b, atac), "cantidad": perdido})
        if atac.debilitado:
            _debilitado(b, atac)


def _puede_moverse(b: Batalla, atac: Combatiente) -> bool:
    n_atac, lado = _nombre(b, atac), _lado(b, atac)

    if atac.estado == "congelado":
        if b.rng.random() >= PROB_DESCONGELAR:
            _decir(b, f"¡{n_atac} está congelado y no puede moverse!",
                   {"tipo": "estado", "lado": lado, "estado": "congelado"})
            return False
        atac.estado = None
        _decir(b, f"¡{n_atac} se descongeló!")

    if atac.estado == "sueno":
        if atac.contador_sueno > 0:
            atac.contador_sueno -= 1
            _decir(b, f"{n_atac} está profundamente dormido.",
                   {"tipo": "estado", "lado": lado, "estado": "sueno"})
            return False
        atac.estado = None
        _decir(b, f"¡{n_atac} se despertó!")

    if atac.estado == "paralisis" and b.rng.random() < PROB_PARALISIS:
        _decir(b, f"¡{n_atac} está paralizado y no puede moverse!",
               {"tipo": "estado", "lado": lado, "estado": "paralisis"})
        return False
    return True


def _usar_movimiento(b: Batalla, atac: Combatiente, defe: Combatiente, mov) -> None:
    if not _puede_moverse(b, atac):
        return
    n_atac, n_def = _nombre(b, atac), _nombre(b, defe)
    lado_def = _lado(b, defe)

    if mov is b.forcejeo:
        _decir(b, f"¡A {n_atac} no le quedan movimientos!")
    atac.gastar_pp(mov)
    _decir(b, f"{n_atac} usó {mov.nombre}.",
           {"tipo": "ataque", "lado": _lado(b, atac), "mov_tipo": mov.tipo,
            "categoria": mov.categoria})

    if mov.categoria == "estado" and _bloqueado_por_tipo(mov, defe, b.tabla):
        _decir(b, f"No afecta a {n_def}...")
        return
    if not acierta(mov, atac, defe, b.rng):
        _decir(b, f"¡El ataque de {n_atac} falló!", {"tipo": "fallo", "lado": lado_def})
        return

    dano = 0
    if mov.categoria != "estado":
        res = calcular_dano(atac, defe, mov, b.tabla, rng=b.rng)
        if res.efectividad == 0:
            _decir(b, f"No afecta a {n_def}...")
            return
        dano = defe.recibir_dano(res.dano)
        _animar(b, {"tipo": "dano", "lado": lado_def, "cantidad": dano,
                    "efectividad": res.efectividad, "critico": res.critico})
        if res.critico:
            _decir(b, "¡Golpe crítico!")
        if res.efectividad > 1:
            _decir(b, "¡Es muy eficaz!")
        elif res.efectividad < 1:
            _decir(b, "No es muy eficaz...")
        if defe.debilitado:
            _debilitado(b, defe)
        elif mov.tipo == "fuego" and defe.estado == "congelado":
            defe.estado = None
            _decir(b, f"¡{n_def} se descongeló!")

    for efecto in mov.efectos:
        _aplicar_efecto(b, efecto, mov, atac, defe, dano)


# ---------------------------------------------------------------- rival
def puntuar_movimiento(mov, atac: Combatiente, defe: Combatiente, tabla: dict) -> float:
    """Dano esperado del movimiento, o un puntaje fijo si es de estado."""
    if mov.categoria != "estado":
        dano = calcular_dano(atac, defe, mov, tabla, rng=_RNG_ESTIMACION, critico=False, azar=0.925).dano
        return dano * ((mov.precision or 100) / 100)

    valor = 0.0
    for e in mov.efectos:
        t = e["tipo"]
        if t == "estado":
            inmune = INMUNIDAD_ESTADO.get(e["estado"]) in defe.tipos
            bloqueado = _bloqueado_por_tipo(mov, defe, tabla)
            if defe.estado is None and not inmune and not bloqueado:
                valor += 30 * ((mov.precision or 100) / 100)
        elif t == "stat":
            if e["objetivo"] == "propio" and atac.etapas[e["stat"]] < 2:
                valor += 25
            elif e["objetivo"] == "rival" and defe.etapas[e["stat"]] > -2:
                valor += 12
        elif t == "cura" and atac.hp < atac.hp_max * 0.5:
            valor += 60
        elif t == "descanso" and atac.hp < atac.hp_max * 0.4 and atac.estado != "sueno":
            valor += 55
    return valor


def elegir_movimiento_rival(b: Batalla) -> int:
    """Indice del mejor movimiento con PP (a veces uno al azar), o -1 si debe usar Forcejeo."""
    atac, defe = b.rival.pokemon, b.jugador.pokemon
    validos = [i for i in range(len(atac.movimientos)) if atac.tiene_pp(i)]
    if not validos:
        return -1
    if b.rng.random() < PROB_RIVAL_AL_AZAR:
        return b.rng.choice(validos)
    puntos = {i: puntuar_movimiento(atac.movimientos[i], atac, defe, b.tabla) for i in validos}
    return max(validos, key=lambda i: puntos[i])


def _movimiento_rival(b: Batalla):
    i = elegir_movimiento_rival(b)
    return b.forcejeo if i < 0 else b.rival.pokemon.movimientos[i]


def _elegir_reemplazo_rival(b: Batalla) -> int:
    objetivo = b.jugador.pokemon

    def mejor(i):
        c = b.rival.equipo[i]
        return max(puntuar_movimiento(m, c, objetivo, b.tabla) for m in c.movimientos)
    return max(b.rival.disponibles(), key=mejor)


# ---------------------------------------------------------------- turno
def _validar_cambio(lado: Lado, indice: int) -> None:
    if not 0 <= indice < len(lado.equipo):
        raise ValueError("Ese Pokémon no está en tu equipo.")
    if indice == lado.activo and not lado.pokemon.debilitado:
        raise ValueError("Ese Pokémon ya está en combate.")
    if lado.equipo[indice].debilitado:
        raise ValueError("Ese Pokémon está debilitado.")


def _enviar_jugador(b: Batalla, indice: int) -> None:
    anterior = b.jugador.pokemon
    if not anterior.debilitado:
        anterior.reiniciar_etapas()
        _decir(b, f"¡Vuelve, {_corto(anterior)}!", {"tipo": "retirada", "lado": "jugador"})
    b.jugador.activo = indice
    _decir(b, f"¡Adelante, {_corto(b.jugador.pokemon)}!", {"tipo": "entrada", "lado": "jugador"})


def _fin_de_turno(b: Batalla) -> None:
    for lado in (b.jugador, b.rival):
        c = lado.pokemon
        if not c.debilitado and c.estado == "quemadura":
            perdido = c.recibir_dano(max(1, int(c.hp_max * FRACCION_QUEMADURA)))
            _decir(b, f"¡{_nombre(b, c)} sufre por la quemadura!",
                   {"tipo": "dano", "lado": _lado(b, c), "cantidad": perdido})
            if c.debilitado:
                _debilitado(b, c)


def _terminar(b: Batalla, ganador: str) -> None:
    b.ganador = ganador
    e = b.entrenador
    if ganador == "jugador":
        _decir(b, "¡Has ganado el combate!", {"tipo": "fin", "ganador": ganador})
        _decir(b, f"{e.nombre}: «{e.victoria}»")
    else:
        _decir(b, "Te has quedado sin Pokémon... ¡Has perdido el combate!",
               {"tipo": "fin", "ganador": ganador})
        _decir(b, f"{e.nombre}: «{e.derrota}»")


def _resolver_debilitados(b: Batalla) -> None:
    if b.rival.pokemon.debilitado:
        if b.rival.derrotado:
            _terminar(b, "jugador")
            return
        b.rival.activo = _elegir_reemplazo_rival(b)
        _decir(b, f"{b.entrenador.nombre} envía a {_corto(b.rival.pokemon)}.",
               {"tipo": "entrada", "lado": "rival"})
    if b.jugador.pokemon.debilitado:
        if b.jugador.derrotado:
            _terminar(b, "rival")
        else:
            b.debe_cambiar = True
            _decir(b, "Elige tu siguiente Pokémon.")


def ejecutar_turno(b: Batalla, tipo: str, indice: int) -> None:
    """Aplica la accion del jugador ("mover" o "cambiar"). ValueError si no es valida."""
    if b.terminada:
        raise ValueError("El combate ya terminó.")
    jug, riv = b.jugador, b.rival

    if b.debe_cambiar and tipo != "cambiar":
        raise ValueError("Tu Pokémon se debilitó: debes elegir otro para continuar.")
    if tipo == "mover":
        if not 0 <= indice < len(jug.pokemon.movimientos):
            raise ValueError("Ese movimiento no existe.")
        if not jug.pokemon.sin_pp and not jug.pokemon.tiene_pp(indice):
            raise ValueError("¡No quedan PP para ese movimiento!")
    elif tipo == "cambiar":
        _validar_cambio(jug, indice)
    else:
        raise ValueError("Acción desconocida.")

    _iniciar_accion(b)

    if b.debe_cambiar:                  # el reemplazo tras un debilitado no gasta turno
        _enviar_jugador(b, indice)
        b.debe_cambiar = False
        return

    b.turno += 1
    p_jug = jug.pokemon
    if tipo == "cambiar":
        _enviar_jugador(b, indice)
        acciones = [(riv.pokemon, jug.pokemon, _movimiento_rival(b))]
    else:
        mov_jug = b.forcejeo if p_jug.sin_pp else p_jug.movimientos[indice]
        acciones = [(p_jug, riv.pokemon, mov_jug),
                    (riv.pokemon, p_jug, _movimiento_rival(b))]
        acciones.sort(key=lambda a: (-a[2].prioridad, -a[0].stat_efectivo("velocidad"),
                                     b.rng.random()))

    for atac, defe, mov in acciones:
        if atac.debilitado or defe.debilitado:
            continue
        _usar_movimiento(b, atac, defe, mov)

    _fin_de_turno(b)
    _resolver_debilitados(b)
