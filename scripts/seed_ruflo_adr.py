"""Sembrado de ADRs en memoria semantica Ruflo (namespace 'adr').

Almacena un resumen-puntero por ADR existente en docs/adr/. La busqueda
semantica recupera el slug y Claude lee el archivo .md cuando lo necesita.

Idempotente: re-ejecutar sobrescribe.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "docs" / "adr"

# Resumen sintetico por ADR (lo que se vectoriza para busqueda).
ADR_SUMMARIES = {
    "0001-cal1-stackelberg-iters": (
        "CAL-1 stackelberg_iters=2 convergencia juego Stackelberg P_star "
        "una iteracion delta SC cero segunda iteracion captura ajuste "
        "marginal precios actividad 2.1"
    ),
    "0002-cal2-etha": (
        "CAL-2 etha=0.1 coeficiente competencia compradores inerte rango "
        "0.01 a 5.0 discrepancia JoinFinal articulo sin impacto "
        "actividad 2.1"
    ),
    "0003-cal3-alpha-dr": (
        "CAL-3 alpha_p=0.20 alpha_c=0.10 demand response fraccion demanda "
        "flexible punto inflexion 72 porciento mejora maxima literatura DR "
        "Luthander Parra prosumidores actividad 2.1 4.1"
    ),
    "0004-cal4-tau-scaling": (
        "CAL-4 tau_buyers/tau_sellers=10 escalado ODE alternativa WI WJ "
        "JoinFinal modelo conjunto vs implementacion secuencial filtros "
        "paso bajo equilibrio IE -0.39 actividad 2.1"
    ),
    "0005-cal5-theta": (
        "CAL-5 theta=0.5 insensibilidad dinamica solo afecta reporting "
        "Wj_total Wi_total no afecta solve_sellers solve_buyers "
        "JoinFinal vs ConArtLatin actividad 2.1"
    ),
    "0006-cal6-bn-lcoe-solar": (
        "CAL-6 b_n LCOE solar 225 COP/kWh homogeneo modo real Cesmag 210 "
        "Fronius IRENA UPME doble calibracion sintetico vector unidades "
        "optimizacion vs real COP/kWh hallazgo D2 cerrado actividad 1.1 1.2"
    ),
    "0007-cal7-stackelberg-alternancia": (
        "CAL-7 alternancia Stackelberg secuencial vs ODE conjunta "
        "JoinFinal ode15s mismo punto fijo Nash invariante factorizacion "
        "operador contractivo paralelizacion ProcessPoolExecutor golden "
        "test SLSQP hallazgo A3 cerrado actividad 2.1"
    ),
    "0008-cal8-pi-gs-cedenar": (
        "CAL-8 pi_gs Cedenar tarifa mensual diferenciada vector per-agente "
        "799 oficial Udenar HUDN 959 comercial Mariana UCC Cesmag "
        "supersede 650 fallback CSV tarifas_cedenar_mensual desercion "
        "P2P AGPE C1 5/5 a 3/5 IR estables impacto +37% beneficio "
        "actividad 1.1 3.1 3.2 3.3 superseded parcialmente por ADR 0009"
    ),
    "0009-cal9-pi-gs-temporal": (
        "CAL-9 pi_gs matriz N x T mes a mes en C1 C2 C3 C4 cada hora "
        "liquida con CU del mes que la contiene CREG 174 y 101 072 "
        "liquidan mensualmente spread 766.80 a 816.98 oficial NT2 "
        "as_pi_gs_array helper canonico backward compatible "
        "supersede parcialmente CAL-8 fase 2 vector N para full y "
        "single_day perfil diario conserva CAL-8 promedio horizonte "
        "tests 43/43 actividad 1.1 3.1 3.2 3.3"
    ),
    "0010-cal10-creg174-tipo-1-2-componente-c": (
        "CAL-10 + CAL-10b + CAL-10b.2 CREG 174/2021 art. 25 permuta "
        "Excedentes hasta importacion y excedentes a precio horario de "
        "bolsa busqueda intramensual hora cruce inyeccion acumulada vs "
        "retiro acumulado componente C Comercializacion Cvm,i,j puro "
        "CREG 119/2007 sin COT correccion literalidad descontado en "
        "permuta autoconsumo a pi_gs completo asimetria red vs no red "
        "CAL-10 C_FRACTION 13.85 % proporcional aproximacion CAL-10b "
        "Cvm+COT (REVERTIDO en CAL-10b.2) CAL-10b.2 solo Cvm desde "
        "tarifas_cedenar_mensual.csv 13 meses cvm_per_agent_hourly "
        "analogo pi_gs_per_agent_hourly NaN fallback as_component_c_array "
        "verificacion WebSearch gestornormativo.creg.gov.co art. 25 "
        "candado legal Cvm,i,j exacto excluye sobretasas posteriores "
        "CREG 101 028/2023 COT no autorizado para permuta CAL-10b RPE "
        "+0.029 P2P invariante 52446938 COP empatados estadisticamente "
        "CAL-10b.2 valor C oficial NT2 172-181 vs 212-223 antes tests "
        "67/67 actividad 1.1 3.1 3.2 3.3"
    ),
    "0011-cal11-c2-ppa-bilateral-modelo-formal": (
        "CAL-11 auditoria formalizacion C2 PPA bilateral physical "
        "Pay-as-Produced precio fijo escalar pi_ppa = pi_gb + f * "
        "(pi_gs - pi_gb) default f=0.5 postulado normativo reparto "
        "simetrico comunitario no empirico subastas UPME CLPE 02-2019 "
        "95.65 COP/kWh CLPE 03-2021 155.8 subasta 2024 76.44 contratos "
        "bilaterales mayoristas XM 2023 284.25 regulado 2024 320.82 "
        "precio bolsa real pydataxm 2019 225.71 2021 139.33 2023 564.20 "
        "2024 682.48 f empirico colombiano negativo -3.08 a +0.029 "
        "teorema invarianza bienestar agregado notas seccion 3.8 "
        "Gini varia con f reportar SA-3 brechas declaradas out-of-scope "
        "CFD financiera Baseload plazo contractual precios diferenciados "
        "por agente CREG 174 102072 contexto comunitario sin intermediario "
        "spread queda en comunidad scripts/audit_xm_yearly_means.py "
        "data/audit_xm_yearly_summary.csv tests/test_c2_bilateral.py "
        "9 tests verdes 66/66 sin regresion actividad 3.1 3.2 3.3 4.2"
    ),
    "0012-cal12-c2-fom-peajes": (
        "CAL-12 correccion Front-of-Meter PPA C2 alcance regulatorio "
        "pi_ppa solo reemplaza componente G del CU CREG 119/2007 arts "
        "6-8 peajes T+D+Cvm+PR+Rm+COT siempre pagados al OR STN sin "
        "exencion por contrato bilateral arts 9-14 savings_cons sobre "
        "G no CU pre-CAL-12 era BTM legacy implicito asumia pi_ppa "
        "reemplaza CU completo sobreestimaba ahorro 488 COP/kWh oficial "
        "NT2 abril 2026 G=310.96 CU=799.16 helper nuevo "
        "g_component_per_agent_hourly desde columna Gm CSV "
        "tarifas_cedenar_mensual transcripcion PDFs cedenar_pdfs "
        "13 meses cobertura completa parametro pi_G en run_c2_bilateral "
        "y run_comparison default punto medio pi_gb G no pi_gb pi_gs "
        "teorema invarianza preservado bajo FoM tests/test_c2_bilateral "
        "16 tests verdes 7 nuevos CAL-12 9 CAL-11 preservados via "
        "pi_G=None legacy comportamiento suite global 74/74 verdes "
        "sin regresion KPI C2 caera 50-75 porciento conclusion P2P "
        "vs C2 reforzada pendiente re-corrida full analysis 52 min "
        "actividad 3.1 3.2 3.3 4.2"
    ),
    "0013-cal13-c2-no-regulado": (
        "CAL-13 C2 alineado con ley colombiana opcion A comunidad MTE "
        "como usuario no-regulado agregado Ley 143/1994 art 41 mercado "
        "mayorista contratos bilaterales CREG 086/1996 art 1 mod 039/2001 "
        "precio libre solo no-regulados Decreto 388/2007 umbral 55 MWh "
        "mes 100 kW potencia conectada CREG 174/2021 art 23 num 1.a "
        "AGPE FNCER vende precio libre destino no-regulados pre-CAL-13 "
        "C2 contrafactico CAL-12 corregia alcance pero AGPE residencial "
        "consumidor residencial regulado no existe legalmente decision "
        "5 instituciones MTE constituidas asociacion cooperativa o "
        "comunidad energetica persona juridica comun usuario no-regulado "
        "agregado firma PPAs con AGPE miembros precio libre savings_cons "
        "sobre G+Cvm+COT no solo G usuario no-regulado se ahorra Cvm+COT "
        "margen comercializador minorista no tiene comercializador "
        "contrata directamente generador via representante MEM sigue "
        "pagando T+D+PR+Rm al OR STN ejemplo abril 2026 oficial NT2 "
        "G=310.96 Cvm=176.41 COT=38.73 G+Cvm+COT=526.10 peajes T+D+PR+Rm "
        "=273.06 CU=799.16 default pi_ppa CAL-13 punto medio pi_gb "
        "G+Cvm+COT no pi_gb G ni pi_gb CU helper nuevo "
        "g_plus_commercialization_per_agent_hourly cedenar_tariff lee "
        "columnas Gm Cvm COT CSV tarifas_cedenar_mensual transcripcion "
        "PDFs cedenar_pdfs 13 meses parametro pi_G mantiene nombre "
        "compatibilidad CAL-12 semantica generalizada rango negociable "
        "ahorro comercializacion teorema invarianza preservado "
        "tests/test_c2_bilateral 21 tests verdes 5 nuevos CAL-13 "
        "16 preservados CAL-11/12 suite global 79/79 verdes sin "
        "regresion KPI C2 estimado 25-35M COP cota intermedia entre "
        "BTM legacy 51M y FoM regulado 12-25M conclusion P2P 52.4M "
        "vs C2 mantiene reforzada legalmente viable no contrafactico "
        "supuesto verificable empiricamente con admin MTE actividad "
        "3.1 3.2 3.3 4.2"
    ),
    "0014-cal14-creg101066-pes-ceiling": (
        "CAL-14 techo CREG 101 066 2024 PES Precio Escasez Superior "
        "absoluto pi_bolsa horario data/xm_prices.py capa de datos "
        "load_creg_ceiling apply_creg101066_ceiling get_pi_bolsa "
        "apply_ceiling=True default tabla mensual PEI PE PES "
        "data/precios_escasez_creg.csv 7 meses jul-2025 a ene-2026 "
        "verificados sheet Comportamiento_PBNal_Horario Excel oficial XM "
        "03_Informe_Precios_y_Transacciones distincion PB Precio Bolsa "
        "marginal de oferta vs PTB Precio Transacciones Bolsa efectivo "
        "tras OEF pydataxm PrecBolsNaci entrega PB no PTB cache picos "
        "2224 COP/kWh agosto 2025 max PES 898.02 ago violacion regulatoria "
        "min(PB,PES) aproxima PTB sin modelar OEF horario afecta C1 Tipo 2 "
        "C3 C4 escenarios sin cambios codigo solo dato recibido decision "
        "PES techo absoluto descarta PE intermedio PEI inferior "
        "alternativas spec docs/superpowers/specs/2026-05-01-cal14 "
        "12 tests verdes Grupo A loader Grupo B capping Grupo C integracion "
        "Grupo D regresion vs PB oficial XM tolerancia 15% ene-2026 "
        "excluido follow-up CAL-15 gap 35% pydataxm vs PTB oficial "
        "investigar metrica sospecha datos provisionales 92 tests global "
        "sin regresion smoke daily 0 horas cap full ~12 horas 0.23 porciento "
        "horizonte delta 3676 COP/kWh actividad 3.x"
    ),
}


def store(key: str, value: str, namespace: str = "adr") -> bool:
    flat = value.replace("\n", " | ").replace('"', "'")
    cmd = (
        f'npx @claude-flow/cli@latest memory store '
        f'--key "{key}" --value "{flat}" --namespace "{namespace}" --upsert'
    )
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=True,
    )
    return proc.returncode == 0 and "Data stored successfully" in (proc.stdout + proc.stderr)


def main() -> int:
    if not ADR_DIR.is_dir():
        print(f"[adr] ERROR: {ADR_DIR} no existe")
        return 1

    ok = 0
    for adr_path in sorted(ADR_DIR.glob("0*.md")):
        slug = adr_path.stem  # ej: 0001-cal1-stackelberg-iters
        # Extrae titulo H1 del archivo
        first_line = adr_path.read_text(encoding="utf-8").splitlines()[0]
        title = re.sub(r"^#+\s*", "", first_line).strip()

        summary = ADR_SUMMARIES.get(slug, "")
        value = (
            f"adr_id: {slug.split('-')[0]} | titulo: {title} | "
            f"path: docs/adr/{slug}.md | resumen: {summary}"
        )
        key = f"adr-{slug}"
        print(f"[adr] storing {key} ({len(value)} chars)...")
        if store(key, value):
            ok += 1
        else:
            print(f"  FAIL {key}")

    total = len(list(ADR_DIR.glob("0*.md")))
    print(f"[adr] hecho: {ok}/{total} ADRs sembrados en namespace 'adr'")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
