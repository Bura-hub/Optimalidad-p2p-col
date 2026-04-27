# Índice de archivos del proyecto

**Tesis:** Análisis de Optimalidad y Validación Regulatoria de Mercados P2P en Colombia  
**Autor:** Brayan S. Lopez-Mendez | **Udenar, 2026**  
**Fecha de última actualización:** 2026-04-17

Este documento describe el propósito de cada archivo del repositorio cuyo nombre no es
autoexplicativo, fue generado automáticamente, o requiere verificación antes de la entrega
final. Los archivos de código Python (`core/`, `scenarios/`, `analysis/`, `data/`) están
documentados en sus propios módulos mediante docstrings.

---

## Directorio raíz

| Archivo | Descripción | Generado por | Estado |
|---|---|---|---|
| `main_simulation.py` | Punto de entrada único del simulador. Orquesta los 5 modos de ejecución (sintético, real, análisis, horizonte completo, GSA). | manual | estable |
| `diagnostico_datos.py` | Script de diagnóstico de los datos MTE: verifica columnas, nulos, rango temporal y cobertura PV por institución. Correr antes de `--data real`. | manual | estable |
| `requirements.txt` | Dependencias Python del proyecto. Instalar con `pip install -r requirements.txt`. Incluye: numpy, scipy, pandas, matplotlib, tqdm, openpyxl, salib. | manual | estable |
| `outputs/REPORTE_AVANCES.md` | Reporte de avance para asesores. §1–§4 son **sobreescritos automáticamente** por `main_simulation.py` en cada ejecución. §5–§9 son secciones manuales que **no se sobreescriben**. | `main_simulation.py` (§1–§4); manual (§5–§9) | actualizar §1 con run `--full` |
| `README.md` | Documentación técnica del proyecto: estructura, comandos, parámetros, figuras. No se regenera automáticamente. | manual | estable |
| `FASE_3_RESUMEN.md` | Resumen del cierre de la Fase 3 (documentación académica): commits realizados, cobertura de la propuesta, pendientes para el jurado. | manual | estable |
| `resultados_comparacion.xlsx` | Resumen de la comparación de los 5 escenarios (P2P vs C1–C4): métricas por hora, por agente y globales. **Se sobreescribe en cada ejecución.** Respaldar antes de correr `--full`. | `main_simulation.py` | actualizar con run `--full` |
| `resultados_analisis.xlsx` | Resultados de análisis de sensibilidad y factibilidad (SA-1, SA-2, FA-1, FA-2). Se genera solo con `--analysis`. **Se sobreescribe.** | `main_simulation.py --analysis` | actualizar con `--data real --full --analysis` |
| `p2p_breakdown.xlsx` | Desglose hora a hora del mercado P2P: flujos de energía por par vendedor-comprador, precios de equilibrio, métricas de clearing. Se genera siempre. | `main_simulation.py` | actualizar con run `--full` |
| `p2p_breakdown_flujos.csv` | Versión CSV del desglose de flujos P2P: columnas hora, vendedor, comprador, P_ij (kWh), pi_i (COP/kWh). Útil para análisis externo. | `main_simulation.py` | actualizar con run `--full` |
| `p2p_breakdown_resumen_horario.csv` | Resumen horario del mercado P2P: energía total transada, precio medio, SC, SS, IE por hora. | `main_simulation.py` | actualizar con run `--full` |
| `resultados_gsa.xlsx` | Índices de sensibilidad Sobol (S1, ST, S2) del GSA Saltelli. Generado por `--gsa`. Solo existe si se corrió el análisis GSA. | `main_simulation.py --gsa` | pendiente run n_base ≥ 64 |
| `resultados_tests.xlsx` | Resultados del bootstrap por bloques (Wilcoxon, Cohen's d, IC 95 %). Hoja: Bootstrap_P2P_vs_C4. Solo existe si se corrió `tests/statistical_tests.py`. | `tests/statistical_tests.py` | pendiente datos `--full` |

---

## Documentos/

| Archivo | Descripción | Verificación requerida |
|---|---|---|
| `PropuestaTesis.txt` | Texto completo de la propuesta de tesis en formato plano (UTF-8). Fuente autoritativa de los objetivos, actividades 1.0–4.2 y referencias [1]–[15]. | No |
| `notas_modelo_tesis.md` | Notas técnicas de diseño del modelo: fórmula de IE, condición de degeneración C1=C3, derivaciones de las funciones de bienestar, decisiones de diseño históricas. Consultar antes de modificar `core/` o `scenarios/`. | No |
| `Inventario_Act_1_0.md` | Inventario formal de elementos del sistema (Activity 1.0): agentes, escenarios C1–C4, parámetros de la Tabla I canónica y requisitos de datos por escenario. | No |
| `Revision_Bibliografica_Act_1_2.md` | Revisión bibliográfica para inferencia de parámetros (Activity 1.2): 4 secciones con tablas de calibración para b_n (LCOE), λ_n (elasticidad), θ_n (preferencias P2P), η_i (aversión al riesgo). | Sí — confirmar autores de refs [22][24][26][27] |
| `Matriz_Trazabilidad.md` | Tabla de trazabilidad: mapea cada actividad de la propuesta (1.0–4.2) al código que la implementa y a las figuras de evidencia. | No |
| `references.bib` | Bibliografía consolidada en formato BibTeX IEEE (27 entradas). Entradas marcadas con `VERIFICAR` requieren confirmación de autoría en la plataforma editorial (DOIs ya verificados). | Sí — ver nota abajo |
| `contexto.txt` | Texto extraído del PDF `Modelo_Base_Sofía_Chacon.pdf`: análisis matemático, computacional y operativo del modelo EMS P2P (Chacón et al., 2025). Documento técnico de ~40 páginas. No se modifica. | No |
| `p2p_explicacion.txt` | Explicación técnica del sistema P2P en texto plano: introducción a comunidades energéticas, dinámica de replicadores y juego de Stackelberg. Fue redactado como material de contexto. No forma parte del código. | No |
| `conversacion_WEEF.txt` | Transcripción de conversación de contexto para la presentación en WEEF (World Engineering Education Forum). No forma parte de la tesis ni del código. | No |
| `informe_preguntas_contexto_WEEF.md` | Informe de preguntas y respuestas de contexto para WEEF: justificaciones del modelo, metodología y resultados presentados al panel. No forma parte de la entrega de tesis. | No |
| `Modelo_Base_Sofía_Chacon.pdf` | PDF del trabajo de grado de Sofía Chacón Chamorro (referencia [5]). Fuente primaria del modelo base. No se modifica. | No |
| `Propuesta de tesis Brayan Lopez.pdf` | PDF de la propuesta de tesis presentada al comité académico. Versión formal; el texto de referencia es `PropuestaTesis.txt`. | No |

### Verificación pendiente en references.bib

| Entrada BibTeX | DOI | Autores pendientes |
|---|---|---|
| `Colombia2022P2P` | 10.1016/j.erss.2022.102714 | Verificar en Energy Research & Social Science (2022, vol. 90) |
| `Sopha2020Prosumer` | 10.1016/j.enpol.2019.111098 | Verificar en Energy Policy (2020, vol. 137) |
| `Guerrero2023RiskMicrogrid` | 10.1016/j.prime.2024.100439 | Verificar en e-Prime: Advances in EEE (2024) |
| `Tavakoli2023RiskAversion` | 10.1016/j.eneco.2023.106886 | Verificar en Energy Economics (2023) |
| `BernalTorres2020Solar` | 10.15446/cuad.econ.v39n80.79498 | Verificar en Cuadernos de Economía, 39(80), 2020 |
| `Tietjen2021Retail` | 10.1016/j.jeem.2021.102513 | Verificar en Journal of Environmental Economics and Management, 109 (2021) |

---

## Documentos/copy/ — Código del modelo base (Chacón et al., 2025)

**IMPORTANTE:** Estos archivos son el modelo base de referencia de Sofía Chacón et al. (2025)
([5] de la propuesta). **No se modifican.** Su comportamiento es el oráculo que valida el código
Python. Si hay discrepancia entre el código Python y estos archivos, prevalece la interpretación
de estos archivos.

| Archivo | Descripción |
|---|---|
| `JoinFinal.m` | **Script principal.** Resuelve el equilibrio Nash-Stackelberg para una comunidad de 8 agentes usando Replicator Dynamics + Lagrangian Relaxation. Equivalente en Python: `core/ems_p2p.py`. Lee `Demandaóptima_Comunidad8pp.xlsx`. |
| `Bienestar6p.py` | **Oráculo de validación en Python.** Implementación del optimizador estático SLSQP de las funciones de bienestar del modelo para 6 agentes. Lo usa `Documentos/copy/generate_reference_h14.py` para generar el caso de referencia del golden test. |
| `ConArtLatin.m` | Construcción de la matriz de restricciones de tipo "latin" para la asignación P2P de 6 agentes. Lee `Demandaóptima_Comunidad6pp.xlsx`. Versión de 6 agentes de `JoinFinal.m`. |
| `OptimizacinCon.m` | Versión con optimización por restricciones explícitas (8 agentes). Alternativa a `JoinFinal.m` con formulación de constraint diferente. |
| `Generadores.m` | Carga perfiles de generación y demanda desde Excel (8 agentes), calcula G_klim y clasifica agentes como vendedores o compradores. Equivalente a `core/market_prep.py`. |
| `Generadoresfiltro.m` | Igual que `Generadores.m` pero con filtro adicional para excluir agentes con generación cero. |
| `SolutionOptGen.m` | Calcula la solución óptima de generación para cada agente. Variante de `Generadores.m` con resolución numérica del problema de optimización local. |
| `GraficasWel.m` | Genera las gráficas de trayectorias de bienestar W_j(t) y W_i(t), precios π_i(t) y asignaciones P_ij(t). Se ejecuta después de `JoinFinal.m` (usa variables del workspace). |
| `Grafocomunidad.m` | Genera el grafo de la comunidad energética: nodos representan agentes, aristas representan transacciones posibles. Comunidad de 8 nodos con matriz de distancias aleatorias. |
| `generate_reference_h14.py` | **Script de generación del oráculo.** Instancia `Bienestar6p.py` con parámetros de `JoinFinal.m` para hora t=14 y datos sintéticos de `data/base_case_data.py`. Ejecutar **una sola vez** para regenerar `reference_h14.json`. |
| `reference_h14.json` | **Oráculo del golden test.** Contiene P_ij, pi_i, P_total, W_total para hora 14 calculados con SLSQP. Cargado por `tests/golden_test_sofia.py`. Solo regenerar si se cambian los parámetros canónicos. |
| `generar_datos_prueba.py` | Genera datos de prueba sintéticos en formato CSV/Excel compatibles con los scripts MATLAB. No se usa en el pipeline Python principal. |
| `Prueba3Prosumidores6.csv` / `.xlsx` | Datos de prueba para 6 prosumidores generados por `generar_datos_prueba.py`. Usados en pruebas manuales de los scripts MATLAB. |
| `Demandaóptima_Comunidad6pp.xlsx` | Perfiles de demanda y generación óptimos para la comunidad de 6 agentes (base del modelo original). Leído por `ConArtLatin.m`. |

---

## outputs/

Los archivos en `outputs/` son generados automáticamente y **no se commitean** (excepto
`bootstrap_42.json`). Son resultados de ejecuciones anteriores, útiles como referencia histórica.

| Archivo | Descripción | Generado por |
|---|---|---|
| `backup_resultados_comparacion_20260416.xlsx` | Copia de seguridad de `resultados_comparacion.xlsx` del 2026-04-16, antes de actualización. Preservado para comparación con versiones posteriores. | `main_simulation.py` |
| `backup_resultados_analisis_20260416.xlsx` | Copia de seguridad de `resultados_analisis.xlsx` del 2026-04-16. | `main_simulation.py` |
| `bootstrap_42.json` | Resultados del bootstrap por bloques con seed=42 (smoke test con datos sintéticos). **No es el resultado definitivo** — se sobreescribe cuando se corra con datos reales (serie diaria de 215 días del run `--full`). | `tests/statistical_tests.py` |
| `run_20260416_2220.log` | Log de la ejecución del 2026-04-16 a las 22:20. Contiene stdout completo del run `--data real --analysis`. Útil para depuración si el pipeline falla. | `main_simulation.py` (redirigido) |
| `gsa_checkpoint_<ts>.parquet` | Checkpoints del GSA Saltelli guardados cada 100 muestras. Si el proceso se interrumpe, el análisis puede reanudarse cargando el último checkpoint. Se crean al correr `--gsa`. | `analysis/global_sensitivity.py` |
| `daily_series_<ts>.csv` | Series diarias de beneficio neto P2P y C4 (columnas `nb_p2p`, `nb_c4`). Generado por el run `--full`. Requerido por `tests/statistical_tests.py`. No existe aún. | `main_simulation.py --full` |
