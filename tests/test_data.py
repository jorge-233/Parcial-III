"""Pruebas de los datos: que los JSON sean consistentes y los 22 Pokemon esten."""
from app.game.data_loader import cargar_datos
from app.game.models import calcular_stats

DATOS = cargar_datos()


def test_hay_22_pokemon_con_4_movimientos_validos():
    assert len(DATOS.especies) == 22
    for especie in DATOS.especies.values():
        assert len(especie.movimientos) == 4
        assert all(m in DATOS.movimientos for m in especie.movimientos)


def test_cada_tipo_tiene_al_menos_un_pokemon():
    usados = {t for e in DATOS.especies.values() for t in e.tipos}
    assert usados == set(DATOS.tipos)


def test_pikachu_companero_tiene_mas_stats_que_el_normal():
    stats = DATOS.especies["pikachu"].stats_base
    assert stats["velocidad"] == 120
    assert sum(stats.values()) == 430      # el Pikachu normal suma 320


def test_calculo_de_stats_a_nivel_50():
    stats = calcular_stats(DATOS.especies["pikachu"].stats_base)
    assert stats["hp"] == 120
    assert stats["velocidad"] == 140     # (2*120+31)*50//100 + 5


def test_hay_12_tipos_y_43_movimientos_con_pp():
    assert len(DATOS.tipos) == 12
    assert {"fantasma", "psiquico", "roca", "dragon"} <= set(DATOS.tipos)
    assert len(DATOS.movimientos) == 43
    sin_pp = [m.id for m in DATOS.movimientos.values() if m.pp is None]
    assert sin_pp == ["forcejeo"]


def test_pokemon_pedidos_con_sus_tipos():
    esperado = {"mewtwo": "psiquico", "moltres": "fuego", "lapras": "hielo", "eevee": "normal",
                "rayquaza": "dragon", "kyogre": "agua", "groudon": "tierra"}
    for slug, tipo in esperado.items():
        assert DATOS.especies[slug].tipos == (tipo,)


def test_eevee_companero_de_lets_go():
    eevee = DATOS.especies["eevee"]
    assert eevee.nombre == "Eevee (compañero)"
    assert sum(eevee.stats_base.values()) == 435      # el Eevee normal suma 325


def test_los_ataques_de_hielo_pueden_congelar():
    for mid in ("rayo_hielo", "ventisca", "puno_hielo"):
        efectos = DATOS.movimientos[mid].efectos
        assert {"tipo": "estado", "estado": "congelado", "prob": 0.1} in efectos


def test_ethan_es_el_personaje_del_jugador():
    assert DATOS.jugador["nombre"] == "Ethan"
    assert DATOS.jugador["sprite"].endswith("ethan.png")
