"""Pruebas de las rutas de FastAPI con TestClient."""
import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
EQUIPO = {"equipo": ["charizard", "blastoise"]}


def crear_combate() -> str:
    respuesta = client.post("/batalla/nueva", data=EQUIPO, follow_redirects=False)
    return respuesta.headers["location"]


def test_inicio_responde_y_muestra_pokemon_y_rivales():
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    for texto in ("Charizard", "Pikachu", "Misty", "¡Combatir!"):
        assert texto in respuesta.text


def test_ficha_de_un_pokemon_muestra_sus_movimientos():
    respuesta = client.get("/pokemon/charizard")
    assert respuesta.status_code == 200
    assert "Lanzallamas" in respuesta.text


def test_pokemon_inexistente_devuelve_404():
    assert client.get("/pokemon/missingno").status_code == 404


def test_crear_combate_redirige_a_la_pantalla_de_batalla():
    respuesta = client.post("/batalla/nueva", data=EQUIPO, follow_redirects=False)
    assert respuesta.status_code == 303
    assert re.fullmatch(r"/batalla/\w{8}", respuesta.headers["location"])


def test_la_pantalla_de_batalla_muestra_los_movimientos():
    pantalla = client.get(crear_combate())
    assert pantalla.status_code == 200
    assert "Lanzallamas" in pantalla.text
    assert "Historial del combate" in pantalla.text


def test_equipo_vacio_o_demasiado_grande_se_rechaza():
    vacio = client.post("/batalla/nueva", data={})
    assert vacio.status_code == 400
    assert "al menos 1" in vacio.text
    siete = {"equipo": ["charizard", "blaziken", "blastoise", "swampert", "venusaur", "sceptile", "pikachu"]}
    grande = client.post("/batalla/nueva", data=siete)
    assert grande.status_code == 400
    assert "máximo" in grande.text


def test_pokemon_inexistente_en_el_equipo_se_rechaza():
    assert client.post("/batalla/nueva", data={"equipo": ["missingno"]}).status_code == 400


def test_usar_un_movimiento_avanza_el_turno():
    url = crear_combate()
    respuesta = client.post(url + "/mover", data={"indice": 0}, follow_redirects=False)
    assert respuesta.status_code == 303
    assert "Turno 1" in client.get(url).text


def test_movimiento_inexistente_o_texto_invalido_se_rechaza():
    url = crear_combate()
    assert client.post(url + "/mover", data={"indice": 9}).status_code == 400
    assert client.post(url + "/mover", data={"indice": "abc"}).status_code == 422


def test_combate_inexistente_devuelve_404_con_pagina_amable():
    respuesta = client.get("/batalla/noexiste")
    assert respuesta.status_code == 404
    assert "Este combate ya no existe" in respuesta.text
    assert "Empezar otro combate" in respuesta.text
    assert client.post("/batalla/noexiste/mover", data={"indice": 0}).status_code == 404


def test_revancha_crea_un_combate_nuevo():
    url = crear_combate()
    respuesta = client.post(url + "/revancha", follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] != url


def datos_de_animacion(html: str) -> str:
    inicio = html.index('id="datos-combate"')
    return html[html.index(">", inicio) + 1: html.index("</script>", inicio)]


def test_la_animacion_se_entrega_una_sola_vez():
    url = crear_combate()
    primera = datos_de_animacion(client.get(url).text)
    assert '"pasos"' in primera and "quiere combatir" in primera     # presentacion
    assert datos_de_animacion(client.get(url).text) == "null"         # al recargar ya no
    client.post(url + "/mover", data={"indice": 0}, follow_redirects=False)
    despues = datos_de_animacion(client.get(url).text)
    assert '"pasos"' in despues and "\"texto\"" in despues   # el rival es al azar: no fijamos el texto
    assert datos_de_animacion(client.get(url).text) == "null"


def test_accion_invalida_muestra_error_con_boton_para_volver():
    url = crear_combate()
    respuesta = client.post(url + "/mover", data={"indice": 9})
    assert respuesta.status_code == 400
    assert "Ese movimiento no existe." in respuesta.text
    assert f'href="{url}"' in respuesta.text


def test_inicio_muestra_a_ethan_y_los_pokemon_nuevos():
    texto = client.get("/").text
    for nombre in ("Ethan", "Gengar", "Gardevoir", "Golem"):
        assert nombre in texto


def test_la_pantalla_de_batalla_tiene_la_escena_y_el_menu():
    texto = client.get(crear_combate()).text
    for fragmento in ('id="escena"', 'id="cuadro-texto"', "Luchar", "Nv.50", "/static/js/batalla.js"):
        assert fragmento in texto



def test_indice_de_movimientos_muestra_todos_con_su_efecto():
    respuesta = client.get("/movimientos")
    assert respuesta.status_code == 200
    for texto in ("Lanzallamas", "Pulso Dragón", "Forcejeo", "10 % de probabilidad de quemar",
                  "Mewtwo", "PP"):
        assert texto in respuesta.text


def test_la_pantalla_de_batalla_muestra_los_pp():
    texto = client.get(crear_combate()).text
    assert "PP 15/15" in texto          # Lanzallamas de Charizard


def test_desde_otra_pagina_se_puede_volver_al_combate():
    url = crear_combate()
    client.get(url)                                  # al ver el combate se recuerda (cookie)
    for pagina in ("/movimientos", "/", "/pokemon/charizard"):
        texto = client.get(pagina).text
        assert "Volver al combate" in texto
        assert f'href="{url}"' in texto


def test_al_terminar_el_combate_ya_no_se_ofrece_volver():
    from app.main import BATALLAS
    url = crear_combate()
    client.get(url)
    BATALLAS[url.rsplit("/", 1)[1]].ganador = "jugador"
    client.get(url)                                  # el combate terminado borra la cookie
    assert "Volver al combate" not in client.get("/movimientos").text


def test_la_ventana_de_movimientos_esta_dentro_del_combate():
    texto = client.get(crear_combate()).text
    assert 'id="dialogo-movs"' in texto and "Movimientos de tu equipo" in texto
    assert 'data-abrir="dialogo-movs"' in texto
    assert 'href="/movimientos" target' not in texto     # ya no se sale de la pagina


def test_abandonar_borra_el_combate_y_quita_el_aviso():
    from app.main import BATALLAS
    url = crear_combate()
    client.get(url)
    assert "Abandonar" in client.get("/movimientos").text
    respuesta = client.post(url + "/abandonar", data={"volver": "/movimientos"}, follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/movimientos"       # te deja donde estabas
    assert url.rsplit("/", 1)[1] not in BATALLAS
    assert "Volver al combate" not in client.get("/movimientos").text
    assert client.get(url).status_code == 404


def test_abandonar_no_redirige_fuera_de_la_app():
    url = crear_combate()
    respuesta = client.post(url + "/abandonar", data={"volver": "//sitio-externo.com"}, follow_redirects=False)
    assert respuesta.headers["location"] == "/"


def test_un_combate_nuevo_reemplaza_al_que_estaba_sin_terminar():
    from app.main import BATALLAS
    primero = crear_combate()
    client.get(primero)
    segundo = crear_combate()
    client.get(segundo)
    assert primero.rsplit("/", 1)[1] not in BATALLAS               # no se acumulan
    assert segundo.rsplit("/", 1)[1] in BATALLAS
    texto = client.get("/").text
    assert texto.count("Tienes un combate en curso") == 1
