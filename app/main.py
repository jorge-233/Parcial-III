"""Rutas web de PokéBattle."""
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.game.battle import MAX_EQUIPO, Batalla, crear_batalla, ejecutar_turno, foto, revancha
from app.game.data_loader import cargar_datos
from app.game.descripciones import describir
from app.game.models import calcular_stats

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="PokéBattle")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

NOMBRES_TIPO = {"electrico": "Eléctrico", "psiquico": "Psíquico", "dragon": "Dragón"}
NOMBRES_STAT = {"hp": "PS", "ataque": "Ataque", "defensa": "Defensa", "atq_esp": "Ataque Esp.",
                "def_esp": "Defensa Esp.", "velocidad": "Velocidad"}
NOMBRES_CATEGORIA = {"fisico": "Físico", "especial": "Especial", "estado": "Estado"}
templates.env.filters["tipo"] = lambda t: NOMBRES_TIPO.get(t, t.capitalize())
templates.env.filters["stat"] = lambda s: NOMBRES_STAT.get(s, s)
templates.env.filters["categoria"] = lambda c: NOMBRES_CATEGORIA.get(c, c)
templates.env.filters["describir"] = describir

DATOS = cargar_datos()

APRENDEN = {mid: [e for e in DATOS.especies.values() if mid in e.movimientos]
            for mid in DATOS.movimientos}

# Los combates viven en memoria: se pierden si el servidor se reinicia.
BATALLAS: dict[str, Batalla] = {}
MAX_BATALLAS = 200
COMBATE_PERDIDO = "Ese combate no existe o ya expiró."
COOKIE_COMBATE = "combate"


def combate_en_curso(request: Request) -> Batalla | None:
    b = BATALLAS.get(request.cookies.get(COOKIE_COMBATE, ""))
    return b if b is not None and not b.terminada else None


templates.env.globals["combate_en_curso"] = combate_en_curso


def _guardar(b: Batalla) -> None:
    BATALLAS[b.id] = b
    while len(BATALLAS) > MAX_BATALLAS:
        BATALLAS.pop(next(iter(BATALLAS)))


def _obtener(batalla_id: str) -> Batalla:
    b = BATALLAS.get(batalla_id)
    if b is None:
        raise HTTPException(status_code=404, detail=COMBATE_PERDIDO)
    return b


@app.exception_handler(StarletteHTTPException)
def pagina_de_error(request: Request, exc: StarletteHTTPException):
    partes = request.url.path.strip("/").split("/")
    volver = None
    if exc.status_code == 400 and len(partes) >= 2 and partes[0] == "batalla":
        volver = f"/batalla/{partes[1]}"
    return templates.TemplateResponse(request, "error.html", {
        "codigo": exc.status_code,
        "mensaje": exc.detail if isinstance(exc.detail, str) else "Algo salió mal.",
        "combate_perdido": exc.detail == COMBATE_PERDIDO,
        "volver": volver,
    }, status_code=exc.status_code)


def _pagina_inicio(request: Request, error: str | None = None, seleccion=(), status_code=200):
    return templates.TemplateResponse(request, "index.html", {
        "especies": DATOS.especies.values(),
        "entrenadores": DATOS.entrenadores.values(),
        "jugador": DATOS.jugador,
        "tipos": DATOS.tipos,
        "n_movimientos": len(DATOS.movimientos),
        "max_equipo": MAX_EQUIPO,
        "error": error,
        "seleccion": list(seleccion),
    }, status_code=status_code)


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return _pagina_inicio(request)


@app.get("/pokemon/{slug}", response_class=HTMLResponse)
def detalle_pokemon(request: Request, slug: str):
    especie = DATOS.especies.get(slug)
    if especie is None:
        raise HTTPException(status_code=404, detail=f"No existe el Pokémon '{slug}'.")
    movimientos = [DATOS.movimientos[m] for m in especie.movimientos]
    orden = list(DATOS.especies)
    i = orden.index(slug)
    return templates.TemplateResponse(request, "pokemon.html", {
        "especie": especie, "movimientos": movimientos,
        "stats_nivel": calcular_stats(especie.stats_base),
        "anterior": DATOS.especies[orden[i - 1]],
        "siguiente": DATOS.especies[orden[(i + 1) % len(orden)]],
    })


@app.get("/movimientos", response_class=HTMLResponse)
def indice_movimientos(request: Request, tipo: str | None = None):
    if tipo is not None and tipo not in DATOS.tipos:
        raise HTTPException(status_code=404, detail=f"No existe el tipo '{tipo}'.")
    movimientos = sorted(
        (m for m in DATOS.movimientos.values() if tipo is None or m.tipo == tipo),
        key=lambda m: (DATOS.tipos.index(m.tipo), m.nombre))
    return templates.TemplateResponse(request, "movimientos.html", {
        "movimientos": movimientos, "tipos": DATOS.tipos, "tipo_actual": tipo,
        "aprenden": APRENDEN,
    })


@app.post("/batalla/nueva")
def nueva_batalla(request: Request, equipo: list[str] = Form(default=[])):
    try:
        b = crear_batalla(DATOS, equipo)
    except ValueError as error:
        return _pagina_inicio(request, error=str(error), seleccion=equipo, status_code=400)
    _descartar_en_curso(request)
    _guardar(b)
    return RedirectResponse(f"/batalla/{b.id}", status_code=303)


def _descartar_en_curso(request: Request) -> None:
    """Un combate nuevo reemplaza al que quedo sin terminar."""
    anterior = combate_en_curso(request)
    if anterior is not None:
        BATALLAS.pop(anterior.id, None)


def _destino_seguro(ruta: str) -> str:
    """Evita redirigir fuera de la aplicacion."""
    if not ruta.startswith("/") or ruta.startswith("//") or ruta.startswith("/batalla/"):
        return "/"
    return ruta


@app.post("/batalla/{batalla_id}/abandonar")
def abandonar(batalla_id: str, volver: str = Form(default="/")):
    BATALLAS.pop(batalla_id, None)
    respuesta = RedirectResponse(_destino_seguro(volver), status_code=303)
    respuesta.delete_cookie(COOKIE_COMBATE)
    return respuesta


def tomar_reproduccion(b: Batalla) -> dict | None:
    """Los pasos se entregan una sola vez; al recargar se ve el estado final."""
    if not b.pasos_nuevos:
        return None
    b.pasos_nuevos = False
    return {"inicial": b.escena_inicial, "pasos": b.pasos}


@app.get("/batalla/{batalla_id}", response_class=HTMLResponse)
def ver_batalla(request: Request, batalla_id: str):
    b = _obtener(batalla_id)
    respuesta = templates.TemplateResponse(request, "batalla.html", {
        "b": b, "escena": foto(b), "reproduccion": tomar_reproduccion(b),
        "jugador": DATOS.jugador,
    })
    if b.terminada:
        respuesta.delete_cookie(COOKIE_COMBATE)
    else:
        respuesta.set_cookie(COOKIE_COMBATE, b.id, httponly=True, samesite="lax")
    return respuesta


def _accion(batalla_id: str, tipo: str, indice: int) -> RedirectResponse:
    b = _obtener(batalla_id)
    try:
        ejecutar_turno(b, tipo, indice)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return RedirectResponse(f"/batalla/{b.id}", status_code=303)


@app.post("/batalla/{batalla_id}/mover")
def mover(batalla_id: str, indice: int = Form(...)):
    return _accion(batalla_id, "mover", indice)


@app.post("/batalla/{batalla_id}/cambiar")
def cambiar(batalla_id: str, indice: int = Form(...)):
    return _accion(batalla_id, "cambiar", indice)


@app.post("/batalla/{batalla_id}/revancha")
def nueva_revancha(batalla_id: str):
    nueva = revancha(DATOS, _obtener(batalla_id))
    _guardar(nueva)
    return RedirectResponse(f"/batalla/{nueva.id}", status_code=303)
