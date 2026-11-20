"""Pruebas de los pasos del turno (lo que la pagina anima) y de la congelacion."""
import random

from app.game.battle import crear_batalla, ejecutar_turno, intentar_estado
from app.game.data_loader import cargar_datos

DATOS = cargar_datos()


class RngFijo(random.Random):
    """Generador cuyo random() siempre devuelve el mismo valor (controla el azar)."""

    def __init__(self, valor):
        super().__init__(0)
        self.valor = valor

    def random(self):
        return self.valor


def batalla(jugador, rival, rng=None):
    return crear_batalla(DATOS, jugador, rng=rng or random.Random(1), rival_slugs=rival)


def solo_movimientos(combatiente, *ids):
    combatiente.movimientos = [DATOS.movimientos[i] for i in ids]


def textos(b):
    return [p["texto"] for p in b.pasos if p["texto"]]


def posicion(lista, inicio):
    """Indice del primer mensaje que empieza con `inicio`."""
    return next(i for i, t in enumerate(lista) if t.startswith(inicio))


# ------------------------------------------------------------ presentacion
def test_la_presentacion_muestra_entrenadores_antes_de_los_pokemon():
    b = batalla(["charizard"], ["blastoise"])
    primero, ultimo = b.pasos[0], b.pasos[-1]
    assert primero["anim"] == {"tipo": "presentacion"}
    assert primero["texto"] == f"¡{b.entrenador.nombre} quiere combatir!"
    assert not primero["escena"]["rival"]["en_campo"]
    assert not primero["escena"]["jugador"]["en_campo"]
    assert not b.escena_inicial["rival"]["en_campo"]
    lista = textos(b)
    assert posicion(lista, f"{b.entrenador.nombre} envía a Blastoise") < posicion(lista, "¡Adelante, Charizard!")
    assert ultimo["escena"]["rival"]["en_campo"] and ultimo["escena"]["jugador"]["en_campo"]
    assert b.pasos_nuevos is True


# ------------------------------------------------------------ orden de los pasos
def test_pasos_en_orden_rival_te_deja_herido_y_tu_lo_derrotas():
    """Caso del enunciado: Sceptile (mas rapido) ataca primero, luego Articuno lo
    derrota y el entrenador envia a su siguiente Pokemon."""
    b = batalla(["articuno"], ["sceptile", "dugtrio"])
    solo_movimientos(b.rival.pokemon, "hoja_aguda")
    b.rival.pokemon.hp = 1
    vida_inicial = b.jugador.pokemon.hp
    ejecutar_turno(b, "mover", 0)                       # Rayo Hielo

    lista = textos(b)
    orden = [posicion(lista, "Sceptile rival usó Hoja Aguda"),
             posicion(lista, "Articuno usó Rayo Hielo"),
             posicion(lista, "¡Sceptile rival se debilitó!"),
             posicion(lista, f"{b.entrenador.nombre} envía a Dugtrio")]
    assert orden == sorted(orden)

    # La foto de cada paso refleja el instante: primero baja tu vida, luego cae el rival
    golpes = [p for p in b.pasos if p["anim"] and p["anim"]["tipo"] == "dano"]
    al_jugador, al_rival = golpes[0], golpes[1]
    assert al_jugador["anim"]["lado"] == "jugador"
    assert al_jugador["escena"]["jugador"]["hp"] < vida_inicial
    assert al_jugador["escena"]["rival"]["hp"] == 1
    assert al_rival["anim"]["lado"] == "rival"
    assert al_rival["escena"]["rival"]["hp"] == 0
    assert b.pasos[-1]["escena"]["rival"]["slug"] == "dugtrio"
    assert b.escena_inicial["jugador"]["hp"] == vida_inicial


def test_cada_paso_trae_la_foto_completa_de_la_escena():
    b = batalla(["charizard"], ["snorlax"])
    ejecutar_turno(b, "mover", 0)
    for paso in b.pasos:
        for lado in ("jugador", "rival"):
            foto = paso["escena"][lado]
            assert {"nombre", "sprite", "hp", "hp_max", "estado", "equipo", "etapas"} <= set(foto)


def test_el_ataque_lleva_el_tipo_del_movimiento_para_el_destello():
    b = batalla(["charizard"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "refugio")
    ejecutar_turno(b, "mover", 0)                       # Lanzallamas
    ataque = next(p["anim"] for p in b.pasos if p["anim"] and p["anim"]["tipo"] == "ataque"
                  and p["anim"]["lado"] == "jugador")
    assert ataque["mov_tipo"] == "fuego" and ataque["categoria"] == "especial"


def test_el_historial_queda_ordenado_por_turnos():
    b = batalla(["charizard"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "refugio")
    ejecutar_turno(b, "mover", 2)
    ejecutar_turno(b, "mover", 2)
    turnos = [m["turno"] for m in b.historial]
    assert turnos == sorted(turnos)
    assert turnos[0] == 0 and turnos[-1] == 2


# ------------------------------------------------------------ congelacion
def test_los_de_tipo_hielo_no_se_congelan():
    b = batalla(["articuno"], ["charizard"])
    assert intentar_estado(b, b.jugador.pokemon, "congelado") is False
    assert intentar_estado(b, b.rival.pokemon, "congelado") is True
    assert b.rival.pokemon.estado == "congelado"


def test_congelado_no_puede_moverse():
    b = batalla(["charizard"], ["snorlax"], rng=RngFijo(0.99))     # nunca se descongela
    solo_movimientos(b.rival.pokemon, "refugio")
    b.jugador.pokemon.estado = "congelado"
    vida_rival = b.rival.pokemon.hp
    ejecutar_turno(b, "mover", 0)
    assert "¡Charizard está congelado y no puede moverse!" in b.ultimo
    assert b.rival.pokemon.hp == vida_rival
    assert b.jugador.pokemon.estado == "congelado"


def test_congelado_se_descongela_con_20_por_ciento():
    b = batalla(["charizard"], ["snorlax"], rng=RngFijo(0.1))      # 0.1 < 0.2: se descongela
    solo_movimientos(b.rival.pokemon, "refugio")
    b.jugador.pokemon.estado = "congelado"
    ejecutar_turno(b, "mover", 2)
    lista = b.ultimo
    assert lista.index("¡Charizard se descongeló!") < lista.index("Charizard usó Danza Espada.")
    assert b.jugador.pokemon.estado is None


def test_un_ataque_de_fuego_descongela_al_rival():
    b = batalla(["blaziken"], ["snorlax"], rng=RngFijo(0.99))
    solo_movimientos(b.rival.pokemon, "refugio")
    b.rival.pokemon.estado = "congelado"
    ejecutar_turno(b, "mover", 0)                       # Lanzallamas
    assert "¡Snorlax rival se descongeló!" in b.ultimo
    assert b.rival.pokemon.estado is None


def test_rayo_hielo_puede_congelar():
    b = batalla(["articuno"], ["snorlax"], rng=RngFijo(0.05))      # 0.05 < 0.1: se activa
    solo_movimientos(b.rival.pokemon, "refugio")
    ejecutar_turno(b, "mover", 0)                       # Rayo Hielo
    paso = next(p for p in b.pasos if p["texto"] == "¡Snorlax rival quedó congelado!")
    assert paso["anim"]["estado"] == "congelado"
    assert paso["escena"]["rival"]["estado"] == "congelado"


# ------------------------------------------------------------ movimientos nuevos
def test_paz_mental_sube_ataque_y_defensa_especial():
    b = batalla(["gardevoir"], ["snorlax"])
    solo_movimientos(b.rival.pokemon, "refugio")
    ejecutar_turno(b, "mover", 1)                       # Paz Mental
    etapas = b.jugador.pokemon.etapas
    assert etapas["atq_esp"] == 1 and etapas["def_esp"] == 1
    flechas = [p["anim"] for p in b.pasos if p["anim"] and p["anim"]["tipo"] == "stat"
               and p["anim"]["lado"] == "jugador"]
    assert len(flechas) == 2 and all(f["sube"] for f in flechas)


def test_golpe_cuerpo_no_afecta_a_gengar():
    b = batalla(["snorlax"], ["gengar"])
    solo_movimientos(b.rival.pokemon, "refugio")
    vida = b.rival.pokemon.hp
    ejecutar_turno(b, "mover", 0)                       # Golpe Cuerpo (Normal)
    assert b.rival.pokemon.hp == vida
    assert "No afecta a Gengar rival..." in b.ultimo
