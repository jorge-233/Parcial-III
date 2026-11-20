"""Genera los archivos JSON de app/data (tipos, movimientos y Pokemon)."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "app" / "data"

TIPOS = ["normal", "fuego", "agua", "planta", "electrico", "tierra", "volador", "hielo",
         "fantasma", "psiquico", "roca", "dragon"]

# Solo se guardan las relaciones distintas de 1x (atacante -> defensor)
EFECTIVIDAD = {
    "normal": {"roca": 0.5, "fantasma": 0},
    "fuego": {"planta": 2, "hielo": 2, "fuego": 0.5, "agua": 0.5, "roca": 0.5, "dragon": 0.5},
    "agua": {"fuego": 2, "tierra": 2, "roca": 2, "agua": 0.5, "planta": 0.5, "dragon": 0.5},
    "planta": {"agua": 2, "tierra": 2, "roca": 2, "fuego": 0.5, "planta": 0.5, "volador": 0.5,
               "dragon": 0.5},
    "electrico": {"agua": 2, "volador": 2, "electrico": 0.5, "planta": 0.5, "tierra": 0,
                  "dragon": 0.5},
    "tierra": {"fuego": 2, "electrico": 2, "roca": 2, "planta": 0.5, "volador": 0},
    "volador": {"planta": 2, "electrico": 0.5, "roca": 0.5},
    "hielo": {"planta": 2, "tierra": 2, "volador": 2, "dragon": 2, "fuego": 0.5, "agua": 0.5,
              "hielo": 0.5},
    "fantasma": {"fantasma": 2, "psiquico": 2, "normal": 0},
    "psiquico": {"psiquico": 0.5},
    "roca": {"fuego": 2, "hielo": 2, "volador": 2, "tierra": 0.5},
    "dragon": {"dragon": 2},
}


def mov(nombre, tipo, cat, poder=None, prec=None, prio=0, crit=False, efectos=()):
    return {"nombre": nombre, "tipo": tipo, "categoria": cat, "poder": poder,
            "precision": prec, "prioridad": prio, "alto_critico": crit,
            "efectos": list(efectos)}


def estado(nombre, prob):
    return {"tipo": "estado", "estado": nombre, "prob": prob}


def stat(objetivo, nombre, etapas, prob=1.0):
    return {"tipo": "stat", "objetivo": objetivo, "stat": nombre, "etapas": etapas, "prob": prob}


CURA = lambda f: {"tipo": "cura", "fraccion": f}

MOVIMIENTOS = {
    "lanzallamas": mov("Lanzallamas", "fuego", "especial", 90, 100, efectos=[estado("quemadura", 0.1)]),
    "ataque_ala": mov("Ataque Ala", "volador", "fisico", 60, 100),
    "danza_espada": mov("Danza Espada", "normal", "estado", efectos=[stat("propio", "ataque", 2)]),
    "fuego_fatuo": mov("Fuego Fatuo", "fuego", "estado", prec=85, efectos=[estado("quemadura", 1.0)]),
    "envite_igneo": mov("Envite Ígneo", "fuego", "fisico", 120, 100,
                        efectos=[{"tipo": "retroceso", "fraccion": 0.33}]),
    "terremoto": mov("Terremoto", "tierra", "fisico", 100, 100),
    "surf": mov("Surf", "agua", "especial", 90, 100),
    "rayo_hielo": mov("Rayo Hielo", "hielo", "especial", 90, 100, efectos=[estado("congelado", 0.1)]),
    "refugio": mov("Refugio", "normal", "estado", efectos=[stat("propio", "defensa", 1)]),
    "descanso": mov("Descanso", "normal", "estado", efectos=[{"tipo": "descanso"}]),
    "hidrobomba": mov("Hidrobomba", "agua", "especial", 110, 80),
    "latigo_cepa": mov("Látigo Cepa", "planta", "fisico", 45, 100),
    "somnifero": mov("Somnífero", "planta", "estado", prec=75, efectos=[estado("sueno", 1.0)]),
    "sintesis": mov("Síntesis", "planta", "estado", efectos=[CURA(0.5)]),
    "hoja_aguda": mov("Hoja Aguda", "planta", "fisico", 90, 100, crit=True),
    "gigadrenado": mov("Gigadrenado", "planta", "especial", 75, 100,
                       efectos=[{"tipo": "drenaje", "fraccion": 0.5}]),
    "ataque_rapido": mov("Ataque Rápido", "normal", "fisico", 40, 100, prio=1),
    "rayo": mov("Rayo", "electrico", "especial", 90, 100, efectos=[estado("paralisis", 0.1)]),
    "trueno": mov("Trueno", "electrico", "especial", 110, 70, efectos=[estado("paralisis", 0.3)]),
    "onda_trueno": mov("Onda Trueno", "electrico", "estado", prec=90, efectos=[estado("paralisis", 1.0)]),
    "respiro": mov("Respiro", "volador", "estado", efectos=[CURA(0.5)]),
    "bofeton_lodo": mov("Bofetón Lodo", "tierra", "especial", 20, 100,
                        efectos=[stat("rival", "precision", -1)]),
    "tajo": mov("Tajo", "normal", "fisico", 70, 100, crit=True),
    "ataque_arena": mov("Ataque Arena", "tierra", "estado", prec=100,
                        efectos=[stat("rival", "precision", -1)]),
    "tornado": mov("Tornado", "volador", "especial", 40, 100),
    "ventisca": mov("Ventisca", "hielo", "especial", 110, 70, efectos=[estado("congelado", 0.1)]),
    "golpe_cuerpo": mov("Golpe Cuerpo", "normal", "fisico", 85, 100, efectos=[estado("paralisis", 0.3)]),
    "puno_hielo": mov("Puño Hielo", "hielo", "fisico", 75, 100, efectos=[estado("congelado", 0.1)]),
    "bola_sombra": mov("Bola Sombra", "fantasma", "especial", 80, 100,
                       efectos=[stat("rival", "def_esp", -1, 0.2)]),
    "psiquico": mov("Psíquico", "psiquico", "especial", 90, 100,
                    efectos=[stat("rival", "def_esp", -1, 0.1)]),
    "hipnosis": mov("Hipnosis", "psiquico", "estado", prec=60, efectos=[estado("sueno", 1.0)]),
    "paz_mental": mov("Paz Mental", "psiquico", "estado",
                      efectos=[stat("propio", "atq_esp", 1), stat("propio", "def_esp", 1)]),
    "roca_afilada": mov("Roca Afilada", "roca", "fisico", 100, 80, crit=True),
    "rizo_defensa": mov("Rizo Defensa", "normal", "estado", efectos=[stat("propio", "defensa", 1)]),
    "puno_fuego": mov("Puño Fuego", "fuego", "fisico", 75, 100, efectos=[estado("quemadura", 0.1)]),
    "llamarada": mov("Llamarada", "fuego", "especial", 110, 85, efectos=[estado("quemadura", 0.1)]),
    "canto": mov("Canto", "normal", "estado", prec=55, efectos=[estado("sueno", 1.0)]),
    "pulso_dragon": mov("Pulso Dragón", "dragon", "especial", 85, 100),
    "garra_dragon": mov("Garra Dragón", "dragon", "fisico", 80, 100),
    "danza_dragon": mov("Danza Dragón", "dragon", "estado",
                        efectos=[stat("propio", "ataque", 1), stat("propio", "velocidad", 1)]),
    "recuperacion": mov("Recuperación", "psiquico", "estado", efectos=[CURA(0.5)]),
    "mordisco": mov("Mordisco", "normal", "fisico", 60, 100),
    # Solo se usa cuando no quedan PP
    "forcejeo": mov("Forcejeo", "normal", "fisico", 50, None,
                    efectos=[{"tipo": "retroceso_max", "fraccion": 0.25}]),
}

# PP de cada movimiento
PP = {
    "lanzallamas": 15, "ataque_ala": 35, "danza_espada": 20, "fuego_fatuo": 15, "envite_igneo": 15,
    "terremoto": 10, "surf": 15, "rayo_hielo": 10, "refugio": 40, "descanso": 5, "hidrobomba": 5,
    "latigo_cepa": 25, "somnifero": 15, "sintesis": 5, "hoja_aguda": 15, "gigadrenado": 10,
    "ataque_rapido": 30, "rayo": 15, "trueno": 10, "onda_trueno": 20, "respiro": 10,
    "bofeton_lodo": 10, "tajo": 20, "ataque_arena": 15, "tornado": 35, "ventisca": 5,
    "golpe_cuerpo": 15, "puno_hielo": 15, "bola_sombra": 15, "psiquico": 10, "hipnosis": 20,
    "paz_mental": 20, "roca_afilada": 5, "rizo_defensa": 40, "puno_fuego": 15, "llamarada": 5,
    "canto": 15, "pulso_dragon": 10, "garra_dragon": 15, "danza_dragon": 20, "recuperacion": 5,
    "mordisco": 25, "forcejeo": None,
}

# slug: (dex, nombre, tipo, (hp, atq, def, atq_esp, def_esp, vel), movimientos)
POKEMON = {
    "charizard": (6, "Charizard", "fuego", (78, 84, 78, 109, 85, 100),
                  ["lanzallamas", "ataque_ala", "danza_espada", "fuego_fatuo"]),
    "blaziken": (257, "Blaziken", "fuego", (80, 120, 70, 110, 70, 80),
                 ["lanzallamas", "envite_igneo", "danza_espada", "terremoto"]),
    "blastoise": (9, "Blastoise", "agua", (79, 83, 100, 85, 105, 78),
                  ["surf", "rayo_hielo", "refugio", "descanso"]),
    "swampert": (260, "Swampert", "agua", (100, 110, 90, 85, 90, 60),
                 ["hidrobomba", "terremoto", "rayo_hielo", "descanso"]),
    "venusaur": (3, "Venusaur", "planta", (80, 82, 83, 100, 100, 80),
                 ["latigo_cepa", "somnifero", "sintesis", "terremoto"]),
    "sceptile": (254, "Sceptile", "planta", (70, 85, 65, 105, 85, 120),
                 ["hoja_aguda", "gigadrenado", "ataque_rapido", "danza_espada"]),
    "pikachu": (25, "Pikachu (compañero)", "electrico", (45, 80, 50, 75, 60, 120),
                ["rayo", "trueno", "ataque_rapido", "onda_trueno"]),
    "zapdos": (145, "Zapdos", "electrico", (90, 90, 85, 125, 90, 100),
               ["rayo", "onda_trueno", "ataque_ala", "respiro"]),
    "dugtrio": (51, "Dugtrio", "tierra", (35, 100, 50, 50, 70, 120),
                ["terremoto", "bofeton_lodo", "tajo", "ataque_arena"]),
    "pidgeot": (18, "Pidgeot", "volador", (83, 80, 75, 70, 70, 101),
                ["ataque_ala", "tornado", "ataque_rapido", "respiro"]),
    "articuno": (144, "Articuno", "hielo", (90, 85, 100, 95, 125, 85),
                 ["rayo_hielo", "ventisca", "ataque_ala", "respiro"]),
    "snorlax": (143, "Snorlax", "normal", (160, 110, 65, 65, 110, 30),
                ["golpe_cuerpo", "terremoto", "puno_hielo", "descanso"]),
    "gengar": (94, "Gengar", "fantasma", (60, 65, 60, 130, 75, 110),
               ["bola_sombra", "hipnosis", "rayo", "puno_fuego"]),
    "gardevoir": (282, "Gardevoir", "psiquico", (68, 65, 65, 125, 115, 80),
                  ["psiquico", "paz_mental", "hipnosis", "bola_sombra"]),
    "golem": (76, "Golem", "roca", (80, 120, 130, 55, 65, 45),
              ["roca_afilada", "terremoto", "rizo_defensa", "puno_fuego"]),
    "mewtwo": (150, "Mewtwo", "psiquico", (106, 110, 90, 154, 90, 130),
               ["psiquico", "bola_sombra", "rayo_hielo", "recuperacion"]),
    "moltres": (146, "Moltres", "fuego", (90, 100, 90, 125, 85, 90),
                ["llamarada", "ataque_ala", "fuego_fatuo", "respiro"]),
    "lapras": (131, "Lapras", "hielo", (130, 85, 80, 85, 95, 60),
               ["surf", "rayo_hielo", "canto", "rayo"]),
    "eevee": (133, "Eevee (compañero)", "normal", (65, 75, 70, 65, 85, 75),
              ["golpe_cuerpo", "ataque_rapido", "mordisco", "ataque_arena"]),
    "rayquaza": (384, "Rayquaza", "dragon", (105, 150, 90, 150, 90, 95),
                 ["garra_dragon", "pulso_dragon", "terremoto", "danza_dragon"]),
    "kyogre": (382, "Kyogre", "agua", (100, 100, 90, 150, 140, 90),
               ["hidrobomba", "surf", "ventisca", "trueno"]),
    "groudon": (383, "Groudon", "tierra", (100, 150, 140, 100, 90, 90),
                ["terremoto", "roca_afilada", "puno_fuego", "danza_espada"]),
}

NOMBRES_STATS = ("hp", "ataque", "defensa", "atq_esp", "def_esp", "velocidad")


def main():
    (DATA / "type_chart.json").write_text(
        json.dumps({"tipos": TIPOS, "efectividad": EFECTIVIDAD}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    for mid, m in MOVIMIENTOS.items():
        m["pp"] = PP[mid]
    (DATA / "moves.json").write_text(
        json.dumps(MOVIMIENTOS, indent=2, ensure_ascii=False), encoding="utf-8")
    pokemon = {}
    for slug, (dex, nombre, tipo, stats, movs) in POKEMON.items():
        pokemon[slug] = {
            "id": dex, "nombre": nombre, "tipos": [tipo],
            "stats": dict(zip(NOMBRES_STATS, stats)),
            "movimientos": movs, "sprite": f"img/{slug}.png",
        }
    (DATA / "pokemon.json").write_text(
        json.dumps(pokemon, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(MOVIMIENTOS)} movimientos, {len(pokemon)} Pokemon, {len(TIPOS)} tipos")


if __name__ == "__main__":
    main()
