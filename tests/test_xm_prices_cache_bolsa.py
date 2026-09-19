"""
La cache de bolsa de `data/xm_prices.py` (tarea P, commit P2; informe del
modulo MTE del 2026-09-17, defectos 1, 7 y 8). Actividad 2.1.

Defecto 1: el descargador ponia las fechas por la posicion de la fila, pedia
dos veces el dia frontera de cada bloque de 28 dias y recortaba la cola sin
mirar; la cache de la tesis quedo corrida de 1 a 7 dias desde el 2025-07-30.
Defecto 7: el lector rellenaba con la mediana lo que faltara. Defecto 8: el
recorte medio por mes promediaba sobre todas las horas.

Ninguna prueba sale a la red: el API se sustituye por uno falso que devuelve,
para cada hora, un valor que codifica su propia fecha, de modo que una hora
mal ubicada se ve. Las de la cache canonica leen el fichero versionado.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import data.xm_prices as xm  # noqa: E402

CACHE = RAIZ / "data" / "precios_bolsa_xm_api.csv"
MODULO = (RAIZ / "SALIDAS_SERVIDOR" / "entrega_informe_precios_2026-09-18"
          / "2026-09-17_xm_bolsa_2025-04-03_2026-01-31.csv")
BASE = pd.Timestamp("2025-01-01")
# SHA-256 del contenido de la cache con fin de linea LF (el de git).
SHA_CACHE = "a9a447e24086dee34777f5e461a715e69093a284079d627618654cbcdad877b5"


def _valor(ts: pd.Timestamp) -> float:
    """Precio falso que dice de que hora es: dias desde 2025-01-01, y la hora."""
    return float((ts.normalize() - BASE).days * 100 + ts.hour + 1)


class ApiFalsa:
    """Imita POST /hourly: rango INCLUSIVO en los dos extremos, fecha en texto."""

    def __init__(self, quita_dia=None, quita_hora=None, sin_fecha=False):
        self.cuerpos = []
        self.quita_dia = quita_dia
        self.quita_hora = quita_hora
        self.sin_fecha = sin_fecha

    def __call__(self, url, cuerpo, registro=None):
        assert url == xm.XM_API_HORARIO
        self.cuerpos.append(dict(cuerpo))
        items = []
        for d in pd.date_range(cuerpo["StartDate"], cuerpo["EndDate"], freq="D"):
            if self.quita_dia is not None and d == pd.Timestamp(self.quita_dia):
                continue
            valores = {"code": "Sistema"}
            for h in range(1, 25):
                if (self.quita_hora is not None
                        and (d, h) == (pd.Timestamp(self.quita_hora[0]),
                                       self.quita_hora[1])):
                    continue
                valores[f"Hour{h:02d}"] = f"{_valor(d + pd.Timedelta(hours=h - 1)):.5f}"
            items.append({"Date": None if self.sin_fecha else d.strftime("%Y-%m-%d"),
                          "HourlyEntities": [{"Id": "Sistema", "Values": valores}]})
        return {"Items": items}


# ─── Defecto 1: el descargador ──────────────────────────────────────────────

def test_cada_hora_queda_en_su_fecha(monkeypatch, tmp_path):
    api = ApiFalsa()
    monkeypatch.setattr(xm, "_xm_post", api)
    s = xm.download_via_api("2025-07-01", "2026-02-01",
                            save_path=str(tmp_path / "c.csv"), as_series=True)
    idx = pd.date_range("2025-07-01", "2026-02-01", freq="1h", inclusive="left")
    assert s.index.equals(idx) and len(s) == 5160
    assert (s.to_numpy() == np.array([_valor(t) for t in idx])).all()
    # el vector que devuelve por defecto es el mismo
    monkeypatch.setattr(xm, "_xm_post", ApiFalsa())
    v = xm.download_via_api("2025-07-01", "2026-02-01")
    assert np.array_equal(v, s.to_numpy())


def test_los_bloques_no_se_solapan_y_cubren_el_horizonte(monkeypatch):
    api = ApiFalsa()
    monkeypatch.setattr(xm, "_xm_post", api)
    xm.download_via_api("2025-04-04", "2026-02-01")
    ini = [pd.Timestamp(c["StartDate"]) for c in api.cuerpos]
    fin = [pd.Timestamp(c["EndDate"]) for c in api.cuerpos]
    assert ini[0] == pd.Timestamp("2025-04-04")
    assert fin[-1] == pd.Timestamp("2026-01-31")
    for a, b in zip(fin[:-1], ini[1:]):
        assert b == a + pd.Timedelta(days=1)
    assert all((f - i).days + 1 <= 28 for i, f in zip(ini, fin))
    assert all(c["MetricId"] == "PrecBolsNaci" and c["Entity"] == "Sistema"
               for c in api.cuerpos)


def test_la_cache_escrita_lleva_las_fechas_reales(monkeypatch, tmp_path):
    monkeypatch.setattr(xm, "_xm_post", ApiFalsa())
    ruta = tmp_path / "c.csv"
    xm.download_via_api("2025-10-30", "2025-11-03", save_path=str(ruta))
    d = pd.read_csv(ruta, encoding="utf-8-sig")
    assert list(d.columns) == ["Fecha", "Hora", "Precio_COP_kWh"]
    ts = pd.to_datetime(d["Fecha"]) + pd.to_timedelta(d["Hora"] - 1, unit="h")
    assert (d["Precio_COP_kWh"].to_numpy() == [_valor(t) for t in ts]).all()
    assert d["Hora"].between(1, 24).all() and len(d) == 4 * 24
    assert not (tmp_path / "c.csv.tmp").exists()


def test_sin_fecha_es_error_y_no_se_reconstruye(monkeypatch):
    monkeypatch.setattr(xm, "_xm_post", ApiFalsa(sin_fecha=True))
    with pytest.raises(ValueError, match="posicion"):
        xm.download_via_api("2025-10-01", "2025-10-05")


def test_un_dia_que_falta_es_error(monkeypatch):
    monkeypatch.setattr(xm, "_xm_post", ApiFalsa(quita_dia="2025-10-03"))
    with pytest.raises(ValueError, match="2025-10-03"):
        xm.download_via_api("2025-10-01", "2025-10-05")


def test_una_hora_que_falta_es_error(monkeypatch):
    monkeypatch.setattr(xm, "_xm_post",
                        ApiFalsa(quita_hora=("2025-10-02", 17)))
    with pytest.raises(ValueError, match="24 horas"):
        xm.download_via_api("2025-10-01", "2025-10-05")


def test_fecha_repetida_igual_se_descarta_distinta_falla():
    t = pd.DataFrame([[1.0] * 24, [2.0] * 24, [2.0] * 24],
                     index=pd.to_datetime(["2025-10-01", "2025-10-02",
                                           "2025-10-02"]))
    assert len(xm._deduplica_fechas(t)) == 2
    t.iloc[2, 5] = 9.0
    with pytest.raises(ValueError, match="valores distintos"):
        xm._deduplica_fechas(t)


def test_save_csv_no_acepta_un_vector_sin_fechas(tmp_path):
    with pytest.raises(TypeError, match="indice horario"):
        xm._save_csv(np.ones(24), str(tmp_path / "x.csv"))


def test_una_peticion_por_segundo_y_registro(monkeypatch, tmp_path):
    import time
    import urllib.request

    class Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"Items": []}).encode()

    esperas = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout: Resp())
    monkeypatch.setattr(time, "sleep", lambda s: esperas.append(s))
    reg = tmp_path / "registro.log"
    xm._XM_ULTIMA_PETICION[0] = time.monotonic()
    xm._xm_post(xm.XM_API_HORARIO, {"MetricId": "PrecBolsNaci"}, str(reg))
    xm._xm_post(xm.XM_API_HORARIO, {"MetricId": "PrecBolsNaci"}, str(reg))
    assert len(esperas) == 2 and all(0.9 < e <= xm._XM_PAUSA_S for e in esperas)
    lineas = reg.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2 and all("PrecBolsNaci" in l and "\t200\t" in l
                                    for l in lineas)


# ─── Defecto 7: el lector no inventa horas ──────────────────────────────────

def _cache_corta(tmp_path) -> Path:
    idx = pd.date_range("2026-01-28", "2026-02-01", freq="1h", inclusive="left")
    ruta = tmp_path / "corta.csv"
    xm._save_csv(pd.Series([_valor(t) for t in idx], index=idx), str(ruta))
    return ruta


def test_rango_del_todo_fuera_devuelve_none(tmp_path):
    assert xm.load_xm_prices(str(_cache_corta(tmp_path)),
                             "2026-03-01", "2026-03-05") is None


def test_rango_en_parte_fuera_none_o_error_sin_mediana(tmp_path):
    ruta = str(_cache_corta(tmp_path))
    assert xm.load_xm_prices(ruta, "2026-01-28", "2026-02-05") is None
    with pytest.raises(ValueError, match="faltan 96 de 192"):
        xm.load_xm_prices(ruta, "2026-01-28", "2026-02-05", estricto=True)


def test_rango_cubierto_por_fecha(tmp_path):
    p = xm.load_xm_prices(str(_cache_corta(tmp_path)), "2026-01-29 05:00",
                          "2026-01-30")
    idx = pd.date_range("2026-01-29 05:00", "2026-01-30", freq="1h",
                        inclusive="left")
    assert np.array_equal(p, [_valor(t) for t in idx])


def test_hora_fuera_de_1_a_24_es_error(tmp_path):
    ruta = tmp_path / "cero.csv"
    ruta.write_text("fecha,hora,cop_kwh\n2025-10-01,0,100.0\n"
                    "2025-10-01,1,101.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="1..24"):
        xm.load_xm_prices(str(ruta), "2025-10-01", "2025-10-02")


def test_hora_repetida_con_otro_precio_es_error(tmp_path):
    ruta = tmp_path / "rep.csv"
    ruta.write_text("Fecha,Hora,Precio_COP_kWh\n2025-10-01,1,100.0\n"
                    "2025-10-01,1,101.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="repetidas"):
        xm.load_xm_prices(str(ruta), "2025-10-01", "2025-10-02")


def test_adj_no_rellena():
    assert np.array_equal(xm._adj(np.arange(30.0), 24), np.arange(24.0))
    with pytest.raises(ValueError, match="mediana"):
        xm._adj(np.arange(20.0), 24)


def test_get_pi_bolsa_no_reescribe_la_canonica(monkeypatch, tmp_path):
    """Horizonte que la canonica no cubre: descarga a una cache con su nombre."""
    canonica = _cache_corta(tmp_path)
    antes = canonica.read_bytes()
    monkeypatch.setattr(xm, "CACHE_BOLSA", str(canonica))
    monkeypatch.setattr(xm, "_cache_de_horizonte",
                        lambda base, a, b: tmp_path / f"h_{a}_{b}.csv")
    api = ApiFalsa()
    monkeypatch.setattr(xm, "_xm_post", api)
    p = xm.get_pi_bolsa(48, t_start="2025-10-01", t_end="2025-10-03",
                        apply_ceiling=False)
    assert xm.ULTIMA_FUENTE == "api_xm:h_2025-10-01_2025-10-03.csv"
    assert canonica.read_bytes() == antes
    assert (tmp_path / "h_2025-10-01_2025-10-03.csv").exists()
    # la segunda vez sale de esa cache, sin red
    n = len(api.cuerpos)
    q = xm.get_pi_bolsa(48, t_start="2025-10-01", t_end="2025-10-03",
                        apply_ceiling=False)
    assert len(api.cuerpos) == n and np.array_equal(p, q)
    assert xm.ULTIMA_FUENTE == "cache_api:h_2025-10-01_2025-10-03.csv"
    # y lo que la canonica si cubre sale de ella
    xm.get_pi_bolsa(24, t_start="2026-01-29", t_end="2026-01-30",
                    apply_ceiling=False)
    assert xm.ULTIMA_FUENTE == f"cache_api:{canonica.name}"


# ─── Defecto 8: el recorte medio del mes ────────────────────────────────────

def test_delta_mean_es_el_de_las_horas_recortadas():
    pi = np.full(720, 100.0)            # noviembre de 2025, tope 829,27159
    pi[:10] = 929.27159
    _, diag = xm.apply_creg101066_ceiling(pi, "2025-11-01",
                                          return_diagnostics=True)
    mes = diag["by_month"]["2025-11"]
    assert mes["hours_capped"] == 10
    assert mes["delta_mean"] == pytest.approx(100.0)
    assert mes["delta_total"] == pytest.approx(1000.0)
    _, diag = xm.apply_creg101066_ceiling(np.full(24, 100.0), "2025-11-01",
                                          return_diagnostics=True)
    assert diag["by_month"]["2025-11"]["delta_mean"] == 0.0


# ─── La cache canonica regenerada ───────────────────────────────────────────

def test_la_cache_canonica_es_la_regenerada_el_2026_09_18():
    contenido = CACHE.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(contenido).hexdigest() == SHA_CACHE


def test_la_cache_canonica_cubre_su_horizonte_por_fecha():
    d = pd.read_csv(CACHE, encoding="utf-8-sig")
    ts = pd.to_datetime(d["Fecha"]) + pd.to_timedelta(d["Hora"] - 1, unit="h")
    idx = pd.date_range("2025-04-04", "2026-02-01", freq="1h", inclusive="left")
    assert pd.DatetimeIndex(ts).equals(idx)
    assert np.isfinite(d["Precio_COP_kWh"]).all()


def test_el_dia_del_informe_trae_los_valores_de_xm():
    """2025-10-10: 207,59 / 109,99 / 116,59 / 165,59 / 220,59 / 220,59 (00 a 20 h)."""
    d = pd.read_csv(CACHE, encoding="utf-8-sig")
    dia = d[d["Fecha"] == "2025-10-10"].set_index("Hora")["Precio_COP_kWh"]
    assert dia.loc[[1, 5, 9, 13, 17, 21]].tolist() == \
        [207.59, 109.99, 116.59, 165.59, 220.59, 220.59]


def test_la_cache_canonica_coincide_con_la_del_modulo():
    if not MODULO.exists():
        pytest.skip("sin la descarga del modulo (SALIDAS_SERVIDOR no se versiona)")
    m = pd.read_csv(MODULO)
    mi = pd.to_datetime(m["fecha"]) + pd.to_timedelta(m["hora"], unit="h")
    ms = pd.Series(m["cop_kwh"].to_numpy(float), index=mi)
    d = pd.read_csv(CACHE, encoding="utf-8-sig")
    di = pd.to_datetime(d["Fecha"]) + pd.to_timedelta(d["Hora"] - 1, unit="h")
    ds = pd.Series(d["Precio_COP_kWh"].to_numpy(float), index=di)
    comun = ds.index.intersection(ms.index)
    assert len(comun) == len(ds) == 7272
    assert (ds.loc[comun] - ms.loc[comun]).abs().max() <= 0.005 + 1e-9
