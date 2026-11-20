"""Pruebas de la logica principal: efectividad, dano, etapas y precision."""
import random

from app.game.damage import acierta, calcular_dano, efectividad
from app.game.data_loader import cargar_datos
from app.game.models import Combatiente

DATOS = cargar_datos()


def crear(slug: str) -> Combatiente:
    return Combatiente.crear(DATOS.especies[slug], DATOS.movimientos)


def mov(mid: str):
    return DATOS.movimientos[mid]


def test_efectividad_de_tipos():
    tabla = DATOS.tabla_tipos
    assert efectividad("fuego", ("planta",), tabla) == 2.0
    assert efectividad("fuego", ("agua",), tabla) == 0.5
    assert efectividad("normal", ("fuego",), tabla) == 1.0


def test_inmunidades_dan_cero():
    tabla = DATOS.tabla_tipos
    assert efectividad("electrico", ("tierra",), tabla) == 0.0
    assert efectividad("tierra", ("volador",), tabla) == 0.0


def test_fuego_hace_mas_dano_a_planta_que_a_agua():
    charizard = crear("charizard")
    contra_planta = calcular_dano(charizard, crear("venusaur"), mov("lanzallamas"),
                                  DATOS.tabla_tipos, critico=False, azar=1.0)
    contra_agua = calcular_dano(charizard, crear("blastoise"), mov("lanzallamas"),
                                DATOS.tabla_tipos, critico=False, azar=1.0)
    assert contra_planta.efectividad == 2.0
    assert contra_agua.efectividad == 0.5
    assert contra_planta.dano > contra_agua.dano


def test_rayo_no_afecta_a_dugtrio_pero_ataque_rapido_si():
    """Caso limite: inmunidad de tipo. Ataque Rapido (Normal) si lo daña."""
    pikachu, dugtrio = crear("pikachu"), crear("dugtrio")
    rayo = calcular_dano(pikachu, dugtrio, mov("rayo"), DATOS.tabla_tipos)
    rapido = calcular_dano(pikachu, dugtrio, mov("ataque_rapido"), DATOS.tabla_tipos)
    assert rayo.dano == 0 and rayo.efectividad == 0.0
    assert rapido.dano > 0


def test_movimiento_de_estado_no_hace_dano():
    resultado = calcular_dano(crear("charizard"), crear("venusaur"),
                              mov("danza_espada"), DATOS.tabla_tipos)
    assert resultado.dano == 0


def test_stab_aumenta_el_dano():
    """Charizard (fuego) con Lanzallamas tiene STAB; con Terremoto no."""
    charizard, snorlax = crear("charizard"), crear("snorlax")
    con_stab = calcular_dano(charizard, snorlax, mov("lanzallamas"),
                             DATOS.tabla_tipos, critico=False, azar=1.0)
    assert con_stab.stab is True
    sin_stab = calcular_dano(charizard, snorlax, mov("terremoto"),
                             DATOS.tabla_tipos, critico=False, azar=1.0)
    assert sin_stab.stab is False


def test_golpe_critico_aumenta_el_dano():
    atacante, defensor = crear("blaziken"), crear("snorlax")
    normal = calcular_dano(atacante, defensor, mov("terremoto"),
                           DATOS.tabla_tipos, critico=False, azar=1.0)
    critico = calcular_dano(atacante, defensor, mov("terremoto"),
                            DATOS.tabla_tipos, critico=True, azar=1.0)
    assert critico.dano > normal.dano


def test_misma_semilla_da_el_mismo_resultado():
    def simular(semilla):
        rng = random.Random(semilla)
        a, d = crear("sceptile"), crear("swampert")
        return [calcular_dano(a, d, mov("gigadrenado"), DATOS.tabla_tipos, rng=rng).dano
                for _ in range(10)]
    assert simular(42) == simular(42)


def test_danza_espada_sube_dos_etapas_y_respeta_el_limite():
    charizard = crear("charizard")
    assert charizard.cambiar_etapa("ataque", 2) == 2
    assert charizard.etapas["ataque"] == 2
    charizard.cambiar_etapa("ataque", 2)
    charizard.cambiar_etapa("ataque", 2)       # llega a +6
    assert charizard.cambiar_etapa("ataque", 2) == 0
    assert charizard.etapas["ataque"] == 6


def test_subir_ataque_aumenta_el_dano():
    atacante, defensor = crear("charizard"), crear("snorlax")
    antes = calcular_dano(atacante, defensor, mov("ataque_ala"),
                          DATOS.tabla_tipos, critico=False, azar=1.0).dano
    atacante.cambiar_etapa("ataque", 2)
    despues = calcular_dano(atacante, defensor, mov("ataque_ala"),
                            DATOS.tabla_tipos, critico=False, azar=1.0).dano
    assert despues > antes


def test_quemadura_reduce_el_ataque_fisico():
    blaziken = crear("blaziken")
    ataque_normal = blaziken.stat_efectivo("ataque")
    blaziken.estado = "quemadura"
    assert blaziken.stat_efectivo("ataque") == ataque_normal // 2


def test_un_pokemon_con_hp_cero_esta_debilitado():
    pikachu = crear("pikachu")
    pikachu.recibir_dano(10_000)
    assert pikachu.hp == 0 and pikachu.debilitado


def test_curar_no_supera_el_hp_maximo():
    pikachu = crear("pikachu")
    pikachu.recibir_dano(30)
    assert pikachu.curar(1000) == 30
    assert pikachu.hp == pikachu.hp_max


def test_precision_100_siempre_acierta_y_sin_precision_nunca_falla():
    rng = random.Random(1)
    a, d = crear("pikachu"), crear("snorlax")
    assert all(acierta(mov("ataque_rapido"), a, d, rng) for _ in range(200))
    assert all(acierta(mov("danza_espada"), a, d, rng) for _ in range(200))


def test_bajar_precision_hace_fallar_mas_veces():
    a, d = crear("pikachu"), crear("snorlax")
    def aciertos():
        rng = random.Random(7)
        return sum(acierta(mov("ataque_rapido"), a, d, rng) for _ in range(500))
    antes = aciertos()
    a.cambiar_etapa("precision", -3)
    assert aciertos() < antes


def test_tipos_nuevos_fantasma_psiquico_y_roca():
    tabla = DATOS.tabla_tipos
    assert efectividad("normal", ("fantasma",), tabla) == 0.0
    assert efectividad("fantasma", ("fantasma",), tabla) == 2.0
    assert efectividad("fantasma", ("psiquico",), tabla) == 2.0
    assert efectividad("psiquico", ("psiquico",), tabla) == 0.5
    for tipo in ("fuego", "hielo", "volador"):
        assert efectividad("roca", (tipo,), tabla) == 2.0
    assert efectividad("agua", ("roca",), tabla) == 2.0
    assert efectividad("fuego", ("roca",), tabla) == 0.5


def test_roca_afilada_contra_charizard_es_muy_eficaz():
    golem, charizard = crear("golem"), crear("charizard")
    res = calcular_dano(golem, charizard, mov("roca_afilada"), DATOS.tabla_tipos,
                        critico=False, azar=1.0)
    assert res.efectividad == 2.0 and res.stab is True



def test_tipo_dragon():
    tabla = DATOS.tabla_tipos
    assert efectividad("dragon", ("dragon",), tabla) == 2.0
    assert efectividad("hielo", ("dragon",), tabla) == 2.0
    for tipo in ("fuego", "agua", "planta", "electrico"):
        assert efectividad(tipo, ("dragon",), tabla) == 0.5
