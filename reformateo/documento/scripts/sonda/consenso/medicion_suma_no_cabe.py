"""M-C: la regla del regimen «la suma no cabe sobre el piso», con cuatro arranques.

QUE DECIDE. D53: si la regla de saturacion por aptitud (paso 5 del nucleo) es
EL reposo de ese regimen o solo una regla declarada. Es el unico regimen cuya
regla se derivo sin un reposo interior que la respalde, y ademas es el que
reparte energia de forma desigual: el vendedor sirve primero a los techos altos
y a los demas no les queda.

COMO. Las horas de ese regimen de los almacenes de E0 (unas veintiocho) y de
CV2 (unas treinta y siete), cada una integrada desde CUATRO arranques
distintos: la oferta repartida a partes iguales (como JoinFinal.m) o en
proporcion al lado corto (el arranque factible, D45), cruzados con los precios
en el presupuesto sigma (D50) o en el punto medio de la banda. Si los cuatro
terminan en el mismo sitio, el reposo no depende de por donde se entre.

POR QUE LAS DOS: veintiocho horas son una muestra pobre para decidir el rotulo
de un regimen que pesa el 14 % de la energia. CV2 es el mismo mercado con el
componente de comercializar por dos: el comercializador descuenta el doble
sobre lo permutado, de modo que el piso de quien esta en permuta BAJA y la
banda se ensancha, y sus horas de este regimen son un contraste y no una
repeticion. El arnes las carga desde que `paso_a_paso.carga` acepta
`factor_cv` (D7), que en el piso hace lo mismo que `main_simulation.py
--factor-cv 2` (en produccion el factor entra ademas en la liquidacion de los
escenarios, que el mercado de la hora no ve; ver el docstring de la carga).

ACEPTACION: el mismo reposo en los cuatro arranques (<= 1e-3·E (kWh) y <= 0,5
(COP/kWh)) y coincidente con la regla del paso 5. Si hay varios reposos, se
documenta la multiplicidad y la regla se publica como declarada, con la energia
afectada.

LA TOLERANCIA ES LA DECLARADA, no la que el corredor deduce de k (medio 3 de
la revision de 4c): 1e-3·E en reparto y 0,5 (COP/kWh) en precio, en las cuatro
corridas. Si con ella alguna hora no valida, eso es un resultado.

DOS JUICIOS (medio 4). `veredicto.py` da el generico: cuantas horas llegan a la
regla del paso 5 con los cuatro arranques (los cuatro son una sola familia, el
mismo modelo). Y `veredicto(resultados)` de este guion compara ADEMAS los cuatro
arranques ENTRE SI, sobre el estado final de los que llegaron a teq 160: si dos
difieren en mas de la tolerancia, la hora tiene varios reposos, y se suma la
energia afectada, que es lo que el plan pide publicar.

COSTO. Este regimen es de los baratos: en la hora 2120 de E0 la dinamica llegaba
a la esquina hacia t = 20 con unas 64 000 evaluaciones (sec. 3 del informe del
consenso). Con k = 100 hasta teq 160 es del orden de un minuto por corrida;
sesenta y cinco horas por cuatro arranques son 260 corridas.
"""
import numpy as np

GRUPO = "suma_no_cabe"
# Cuantas horas de cada caso, con el reparto que pide el plan de medicion.
CUANTAS = {"E0": 28, "CV2": 37}
MU = 1.0
TOPE = 1800.0

MEDICION = "M-C"
QUE_DECIDE = "D53: la regla de saturacion es el reposo, o es regla declarada"

CORTES = [0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6]     # teq 0 a 160 con k = 100
K = 100.0
TEQ_FINAL = 160.0

# Los cuatro arranques: oferta x precios. Son UNA familia: el mismo modelo.
ARRANQUES = (("iguales", "sigma"), ("factible", "sigma"),
             ("iguales", "medio"), ("factible", "medio"))
FAMILIA = "V3a cuatro arranques"

# La tolerancia que el plan fija para M-C (medio 3).
TOLERANCIA = dict(tol_q_rel=1e-3, tol_p=0.5, clase="declarada M-C",
                  motivo="la del plan para M-C: 1e-3*E y 0,5 (COP/kWh)")


def specs(horas):
    fuera = []
    for caso, cuantas in CUANTAS.items():
        for h in horas.get(caso, {}).get(GRUPO, [])[:cuantas]:
            for oferta, nivel in ARRANQUES:
                fuera.append(dict(
                    medicion=MEDICION, familia=FAMILIA,
                    caso=caso, fecha=h["fecha"], grupo=GRUPO,
                    etq=f"oferta {oferta} + precios {nivel}",
                    var=dict(mu_ent=MU, k_lento=K, arranque=oferta),
                    cortes=CORTES, tope=TOPE, tolerancia=TOLERANCIA,
                    nivel=nivel, piso_juego="marginal"))
    return fuera


def entre_arranques(corridas, tol=TOLERANCIA) -> dict:
    """Los arranques de UNA hora comparados entre si, sobre su estado final.

    Solo entran los que LLEGARON: a teq 160 y con el estado final QUIETO (las
    derivadas del reparto y de los precios bajo 1e-3 en los dos ultimos
    puntos, `veredicto.esta_quieta`; N5 de la re-revision de 4c). Un arranque
    cortado antes, o que en teq 160 todavia se mueve, no dice donde se queda:
    compararlo con los demas haria pasar una convergencia lenta por
    multiplicidad. Devuelve cuantos se compararon, cuantos no llegaron (y por
    que), la mayor diferencia de reparto y de precio entre dos de los que
    llegaron, y si hay multiplicidad.
    """
    from veredicto import esta_quieta
    en_160 = [c for c in corridas
              if c.get("filas") and not c.get("cortada")
              and abs(float(c["filas"][-1]["teq"]) - TEQ_FINAL) < 1e-6]
    llegaron = [c for c in en_160 if esta_quieta(c)]
    E = max(float(corridas[0].get("E", 0.0)), 1e-12) if corridas else 1e-12
    dq = dp = 0.0
    for a in range(len(llegaron)):
        for b in range(a + 1, len(llegaron)):
            fa, fb = llegaron[a]["filas"][-1], llegaron[b]["filas"][-1]
            dq = max(dq, float(np.max(np.abs(np.asarray(fa["q"], float)
                                             - np.asarray(fb["q"], float)))))
            dp = max(dp, float(np.max(np.abs(np.asarray(fa["p"], float)
                                             - np.asarray(fb["p"], float)))))
    multiple = bool(len(llegaron) >= 2
                    and (dq > tol["tol_q_rel"] * E or dp > tol["tol_p"]))
    return dict(comparados=len(llegaron),
                cortados=len(corridas) - len(en_160),
                moviendose=len(en_160) - len(llegaron),
                dq=dq, dp=dp, E=E, multiple=multiple)


def veredicto(resultados) -> str:
    """Medio 4: los cuatro arranques entre si, y la energia con varios reposos."""
    horas = {}
    for res in resultados:
        sp = res.get("spec", {})
        if sp.get("medicion") != MEDICION or not res.get("filas"):
            continue
        if res.get("recorte_movio"):
            continue
        horas.setdefault((sp["caso"], sp["fecha"]), []).append(res)
    lineas = ["", "  M-C - LOS CUATRO ARRANQUES ENTRE SI", ""]
    if not horas:
        return "\n".join(lineas + ["  ninguna hora con corridas utiles"])
    E_total = E_multiple = 0.0
    multiples, sin_comparar = [], []
    for (caso, fecha), corridas in sorted(horas.items()):
        r = entre_arranques(corridas)
        E_total += r["E"]
        if r["comparados"] < 2:
            sin_comparar.append((caso, fecha, r))
        elif r["multiple"]:
            E_multiple += r["E"]
            multiples.append((caso, fecha, r))
    n = len(horas)
    llegaron_igual = n - len(multiples) - len(sin_comparar)
    # N5: tres casos distintos, y se separan. «No llegaron» no es multiplicidad.
    lineas.append(f"  {n} horas: {llegaron_igual} llegaron al MISMO sitio; "
                  f"{len(multiples)} llegaron a SITIOS DISTINTOS (varios "
                  f"reposos); {len(sin_comparar)} NO LLEGARON (menos de dos "
                  f"arranques quietos en teq 160: no se pueden comparar)")
    frac = E_multiple / E_total if E_total > 0 else 0.0
    lineas.append(f"  energia afectada por la multiplicidad: {E_multiple:.4f} "
                  f"de {E_total:.4f} (kWh) de la muestra = {100 * frac:.2f} %")
    for caso, fecha, r in multiples[:20]:
        lineas.append(f"    VARIOS REPOSOS {caso} {fecha}: max|dq| = "
                      f"{r['dq']:.3e} (kWh, E = {r['E']:.4f}), max|dp| = "
                      f"{r['dp']:.3f} (COP/kWh), {r['comparados']} arranques "
                      f"quietos")
    for caso, fecha, r in sin_comparar[:10]:
        lineas.append(f"    no llegaron {caso} {fecha}: {r['cortados']} "
                      f"arranques cortados antes de teq 160 y "
                      f"{r['moviendose']} todavia en movimiento en teq 160")
    if multiples:
        lineas.append("  => la regla del paso 5 se publica como DECLARADA, con "
                      "esa energia afectada (D53)")
    return "\n".join(lineas)
