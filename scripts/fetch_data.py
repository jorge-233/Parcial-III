"""Actualiza estadisticas e imagenes desde PokeAPI.

Uso: python scripts/fetch_data.py
Conserva tipos y movimientos de pokemon.json; solo cambia stats, numero e imagen.
"""
import json
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
POKEMON_JSON = RAIZ / "app" / "data" / "pokemon.json"
IMG_DIR = RAIZ / "app" / "static" / "img"
API = "https://pokeapi.co/api/v2/pokemon/{}"

NOMBRES_STATS = {
    "hp": "hp", "attack": "ataque", "defense": "defensa",
    "special-attack": "atq_esp", "special-defense": "def_esp", "speed": "velocidad",
}

# Los companeros de Let's Go tienen estadisticas propias
OVERRIDES = {
    "pikachu": {
        "nombre": "Pikachu (compañero)",
        "stats": {"hp": 45, "ataque": 80, "defensa": 50,
                  "atq_esp": 75, "def_esp": 60, "velocidad": 120},
    },
    "eevee": {
        "nombre": "Eevee (compañero)",
        "stats": {"hp": 65, "ataque": 75, "defensa": 70,
                  "atq_esp": 65, "def_esp": 85, "velocidad": 75},
    },
}


def pedir(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "pokebattle-proyecto-academico"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def descargar_imagen(slug: str, otros: dict) -> None:
    """Render de HOME o, si falla, el arte oficial."""
    for fuente in ("home", "official-artwork"):
        url = (otros.get(fuente) or {}).get("front_default")
        if not url:
            continue
        try:
            (IMG_DIR / f"{slug}.png").write_bytes(pedir(url))
            print(f"   imagen: {fuente}")
            return
        except OSError as error:
            print(f"   no se pudo descargar {fuente}: {error}")
    print("   se conserva la imagen anterior")


def main():
    pokemon = json.loads(POKEMON_JSON.read_text(encoding="utf-8"))
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    for slug, datos in pokemon.items():
        print(f"-> {slug}")
        api = json.loads(pedir(API.format(slug)))

        datos["id"] = api["id"]
        datos["stats"] = {NOMBRES_STATS[s["stat"]["name"]]: s["base_stat"] for s in api["stats"]}

        for clave, valor in OVERRIDES.get(slug, {}).items():
            datos[clave] = valor

        descargar_imagen(slug, api["sprites"]["other"])
        datos["sprite"] = f"img/{slug}.png"

    POKEMON_JSON.write_text(json.dumps(pokemon, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Listo: pokemon.json actualizado y sprites descargados.")


if __name__ == "__main__":
    main()
