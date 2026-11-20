"""Pruebas del motor de combate: equipos, turnos, estados, KO y fin del combate."""
import random

from app.game.battle import (
    MAX_EQUIPO, crear_batalla, ejecutar_turno, elegir_movimiento_rival,
    intentar_estado, puntuar_movimiento, revancha,
)
from app.game.data_loader import cargar_datos

DATOS = cargar_datos()


def batalla(jugador, rival, semilla=1):
    return crear_batalla(DATOS, jugador, rng=random.Random(semilla), rival_slugs=rival)


def solo_movimientos(combatiente, *ids):
    """Deja al Pokemon con los movimientos indicados para controlar al rival."""
    combatiente.movimientos = [DATOS.movimientos[i] for i in ids]


def error_de(funcion, *args):
    try:
        funcion(*args)
    except ValueError as e:
        return str(e)
    return None


# ------------------------------------------------------------ creacion
def test_el_rival_lleva_tantos_pokemon_distintos_como_el_jugador():
    for n in range(1, MAX_EQUIPO + 1):
        equipo = sorted(DATOS.especies)[:n]
        b = crear_batalla(DATOS, equipo, rng=random.Random(n))
        slugs_rival = [c.especie.slug for c in b.rival.equipo]
        assert len(slugs_rival) == n == len(set(slugs_rival))
    b = crear_batalla(DATOS, ["charizard", "pikachu"], rng=random.Random(5))
    assert b.entrenador.slug in DATOS.entrenadores
    assert len(b.jugador.equipo) == 2


def test_misma_semilla_crea_la_misma_batalla():
    a = crear_batalla(DATOS, ["charizard"], rng=random.Random(9))
    b = crear_batalla(DATOS, ["charizard"], rng=random.Random(9))
    assert a.entrenador.slug == b.entrenador.slug
    assert [c.especie.slug for c in a.rival.equipo] == [c.especie.slug for c in b.rival.equipo]


def test_hay_como_maximo_6_entrenadores_y_todos_aparecen_al_azar():
    assert len(DATOS.entrenadores) <= 6
    vistos = {crear_batalla(DATOS, ["pikachu"], rng=random.Random(s)).entrenador.slug
              for s in range(200)}
    assert vistos == set(DATOS.entrenadores)


def test_equipos_invalidos_se_rechazan():
    assert error_de(crear_batalla, DATOS, []) is not None
    assert error_de(crear_batalla, DATOS, ["charizard"] * 2) is not None
    assert error_de(crear_batalla, DATOS, ["missingno"]) is not None
    assert "máximo" in error_de(crear_batalla, DATOS, ["charizard", "blaziken", "blastoise", "swampert", "venusaur", "sceptile", "pikachu"])
    assert MAX_EQUIPO == 6


def test_la_revancha_cambia_de_entrenador_y_restaura_la_vida():
    b = batalla(["charizard", "pikachu"], ["snorlax"])
    b.jugador.pokemon.recibir_dano(50)
    nueva = revancha(DATOS, b, rng=random.Random(3))
    assert nueva.entrenador.slug != b.entrenador.slug
    assert nueva.jugador.pokemon.hp == nueva.jugador.pokemon.hp_max
    assert nueva.id != b.id


# ------------------------------------------------------------ orden del turno
def test_el_mas_rapido_ataca_primero():
    b = batalla(["pikachu"], ["snorlax"])           # 120 de velocidad vs 30
    solo_movimientos(b.rival.pokemon, "terremoto")
    ejecutar_turno(b, "mover", 3)                   # Onda Trueno (sin prioridad)
    assert b.ultimo[0].startswith("Pikachu usó")


def test_la_prioridad_va_antes_que_la_velocidad():
    b = batalla(["pidgeot"], ["sceptile"])          # Sceptile es mas rapido
    solo_movimientos(b.rival.pokemon, "hoja_aguda")
    ejecutar_turno(b, "mover", 2)                   # Ataque Rapido (+1)
    assert b.ultimo[0].startswith("Pidgeot usó Ataque Rápido")


# ------------------------------------------------------------ estados y efectos
def test_fuego_no_se_quema_ni_electrico_se_paraliza():
    b = batalla(["charizard"], ["pikachu", "blastoise"])
    assert intentar_estado(b, b.jugador.pokemon, "quemadura") is False
    assert intentar_estado(b, b.rival.equipo[0], "paralisis") is False
    assert intentar_estado(b, b.rival.equipo[1], "quemadura") is True
    assert b.rival.equipo[1].estado == "quemadura"
    assert intentar_estado(b, b.rival.equipo[1], "paralisis") is False   # ya tiene estado


def test_la_quemadura_hace_dano_al_final_del_turno():
    b = batalla(["blastoise"], ["blastoise"])
    solo_movimientos(b.rival.pokemon, "refugio")
    jugador = b.jugador.pokemon
    jugador.estado = "quemadura"
    ejecutar_turno(b, "mover", 2)                   # Refugio
    assert jugador.hp == jugador.hp_max - int(jugador.hp_max / 16)


def test_un_pokemon_dormido_no_actua():
    b = batalla(["charizard"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "terremoto")
    b.jugador.pokemon.estado, b.jugador.pokemon.contador_sueno = "sueno", 2
    vida_rival = b.rival.pokemon.hp
    ejecutar_turno(b, "mover", 0)
    assert any("dormido" in m for m in b.ultimo)
    assert b.rival.pokemon.hp == vida_rival


def test_respiro_cura_la_mitad_de_la_vida():
    b = batalla(["zapdos"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "refugio")
    z = b.jugador.pokemon
    z.hp = z.hp_max // 4
    esperado = z.hp + int(z.hp_max * 0.5)
    ejecutar_turno(b, "mover", 3)
    assert z.hp == esperado


def test_danza_espada_sube_el_ataque_en_combate():
    b = batalla(["charizard"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "refugio")
    ejecutar_turno(b, "mover", 2)
    assert b.jugador.pokemon.etapas["ataque"] == 2
    assert any("subió mucho" in m for m in b.ultimo)


def test_onda_trueno_no_afecta_a_dugtrio():
    b = batalla(["pikachu"], ["dugtrio"])
    solo_movimientos(b.rival.pokemon, "ataque_arena")
    ejecutar_turno(b, "mover", 3)
    assert b.rival.pokemon.estado is None
    assert any("No afecta" in m for m in b.ultimo)


# ------------------------------------------------------------ debilitados y cambios
def preparar_ko():
    """Charizard con 1 PS contra un Snorlax que usa Terremoto."""
    b = batalla(["charizard", "blastoise"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "terremoto")
    b.jugador.pokemon.hp = 1
    return b


def test_al_debilitarse_el_jugador_debe_elegir_otro_pokemon():
    b = preparar_ko()
    ejecutar_turno(b, "mover", 2)                   # Danza Espada
    assert b.jugador.pokemon.debilitado
    assert b.debe_cambiar is True
    assert any("se debilitó" in m for m in b.ultimo)
    assert error_de(ejecutar_turno, b, "mover", 0) is not None   # no puede atacar
    assert error_de(ejecutar_turno, b, "cambiar", 0) is not None  # ni elegir al caido
    ejecutar_turno(b, "cambiar", 1)
    assert b.debe_cambiar is False
    assert b.jugador.pokemon.especie.slug == "blastoise"


def test_el_cambio_voluntario_gasta_el_turno():
    b = batalla(["charizard", "blastoise"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "terremoto")
    ejecutar_turno(b, "cambiar", 1)
    assert b.jugador.pokemon.especie.slug == "blastoise"
    assert b.jugador.pokemon.hp < b.jugador.pokemon.hp_max    # el rival ataco al entrar
    assert error_de(ejecutar_turno, b, "cambiar", 1) is not None  # ya esta en combate


def test_el_rival_envia_su_siguiente_pokemon():
    b = batalla(["blaziken"], ["dugtrio", "snorlax"])
    solo_movimientos(b.rival.pokemon, "refugio")
    b.rival.pokemon.hp = 1
    ejecutar_turno(b, "mover", 0)                   # Lanzallamas
    assert b.rival.equipo[0].debilitado
    assert b.rival.pokemon.especie.slug == "snorlax"
    assert any("envía a Snorlax" in m for m in b.ultimo)
    assert not b.terminada


# ------------------------------------------------------------ fin del combate
def test_victoria_muestra_el_mensaje_del_entrenador():
    b = batalla(["blaziken"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "refugio")
    b.rival.pokemon.hp = 1
    ejecutar_turno(b, "mover", 0)
    assert b.terminada and b.ganador == "jugador"
    assert "¡Has ganado el combate!" in b.ultimo
    assert any(b.entrenador.victoria in m for m in b.ultimo)
    assert error_de(ejecutar_turno, b, "mover", 0) is not None   # ya no se puede jugar


def test_derrota_muestra_el_mensaje_del_entrenador():
    b = batalla(["charizard"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "terremoto")
    b.jugador.pokemon.hp = 1
    ejecutar_turno(b, "mover", 2)
    assert b.terminada and b.ganador == "rival"
    assert any(b.entrenador.derrota in m for m in b.ultimo)


# ------------------------------------------------------------ rival
def test_el_rival_puntua_mejor_el_movimiento_super_eficaz():
    b = batalla(["charizard"], ["blastoise"])
    surf = puntuar_movimiento(DATOS.movimientos["surf"], b.rival.pokemon, b.jugador.pokemon, b.tabla)
    hielo = puntuar_movimiento(DATOS.movimientos["rayo_hielo"], b.rival.pokemon, b.jugador.pokemon, b.tabla)
    assert surf > hielo


def test_el_rival_siempre_elige_un_movimiento_valido():
    b = batalla(["charizard"], ["pikachu"])
    n = len(b.rival.pokemon.movimientos)
    assert all(0 <= elegir_movimiento_rival(b) < n for _ in range(100))


# ------------------------------------------------------------ simulacion completa
def jugar_completo(semilla):
    b = crear_batalla(DATOS, ["charizard", "blastoise", "venusaur", "pikachu"],
                      rng=random.Random(semilla))
    for _ in range(500):
        if b.terminada:
            break
        if b.debe_cambiar:
            ejecutar_turno(b, "cambiar", b.jugador.disponibles()[0])
        else:
            ejecutar_turno(b, "mover", 0)
    return b


def test_un_combate_completo_siempre_termina_y_es_repetible():
    a, b = jugar_completo(11), jugar_completo(11)
    assert a.terminada and a.ganador in ("jugador", "rival")
    assert a.historial == b.historial


# ------------------------------------------------------------ PP y Forcejeo
def test_usar_un_movimiento_gasta_un_pp():
    b = batalla(["charizard"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "refugio")
    antes = b.jugador.pokemon.pp[0]
    ejecutar_turno(b, "mover", 0)
    assert b.jugador.pokemon.pp[0] == antes - 1


def test_sin_pp_en_ese_movimiento_no_se_puede_usar():
    b = batalla(["charizard"], ["snorlax"])
    b.jugador.pokemon.pp[0] = 0
    assert "PP" in error_de(ejecutar_turno, b, "mover", 0)


def test_sin_ningun_pp_se_usa_forcejeo_con_retroceso():
    b = batalla(["charizard"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "refugio")
    c = b.jugador.pokemon
    c.pp = [0, 0, 0, 0]
    ejecutar_turno(b, "mover", 0)
    assert "Charizard usó Forcejeo." in b.ultimo
    assert c.hp == c.hp_max - int(c.hp_max * 0.25)


def test_forcejeo_si_afecta_a_fantasma():
    b = batalla(["snorlax"], ["gengar"])
    solo_movimientos(b.rival.pokemon, "refugio")
    b.jugador.pokemon.pp = [0, 0, 0, 0]
    vida = b.rival.pokemon.hp
    ejecutar_turno(b, "mover", 0)
    assert b.rival.pokemon.hp < vida


def test_el_rival_no_elige_movimientos_sin_pp():
    b = batalla(["charizard"], ["snorlax"])
    b.rival.pokemon.pp = [0, 0, 5, 0]
    assert all(elegir_movimiento_rival(b) == 2 for _ in range(50))
    b.rival.pokemon.pp = [0, 0, 0, 0]
    assert elegir_movimiento_rival(b) == -1
