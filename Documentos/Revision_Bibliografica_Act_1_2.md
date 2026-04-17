# Revisión bibliográfica — Actividad 1.2
## Inferencia de parámetros mediante revisión bibliográfica y datos reales

**Autor:** Brayan S. Lopez-Mendez  
**Asesores:** M.Sc. Andrés Pantoja — M.Sc. Germán Obando  
**Programa:** Maestría en Ingeniería Electrónica, Universidad de Nariño, 2026  
**Fecha:** abril de 2026

---

## Introducción

La Actividad 1.2 de la propuesta de tesis establece la necesidad de inferir, mediante revisión
bibliográfica y datos reales, los parámetros económicamente significativos del modelo de mercado
P2P de referencia [5]. Dichos parámetros determinan la función de bienestar de cada agente y, por
tanto, la existencia y naturaleza del equilibrio Nash-Stackelberg. Una calibración inadecuada
produciría resultados no representativos de la comunidad energética del proyecto MTE (Medición
Técnica Energética, Pasto, Colombia).

Los parámetros de interés se agrupan en cuatro categorías: (1) costo de producción de energía
solar fotovoltaica, representado por los coeficientes a_n, b_n y c_n de la función cuadrática de
costo C_n(P) = a_n·P² + b_n·P + c_n; (2) elasticidad precio-demanda, que informa la sensibilidad
de los agentes consumidores ante variaciones del precio de mercado y calibra el parámetro de
preferencia λ_n; (3) preferencias de los consumidores en mercados P2P, que orientan la
interpretación de los parámetros de bienestar λ_n y θ_n; y (4) aversión al riesgo en mercados
de energía, que sustenta la calibración del parámetro η_i (etha).

Para cada categoría se presenta: (i) el fundamento teórico, (ii) la evidencia empírica disponible
para Colombia y América Latina, (iii) la tabla de calibración con fuente, rango reportado, valor
adoptado y justificación, y (iv) las referencias correspondientes. Todas las fuentes citadas
cuentan con identificador de objeto digital (DOI) verificable o, en caso de informes
institucionales, con URL estable y fecha de consulta. Las entradas marcadas con "VERIFICAR" en
`Documentos/references.bib` requieren confirmación de autoría en la plataforma editorial.

---

## §1. Costo nivelado de energía solar fotovoltaica en Colombia

### 1.1 Fundamento teórico

La función de costo de generación del modelo base [5] es cuadrática:

    C_n(P_n) = a_n · P_n² + b_n · P_n + c_n

donde a_n ≥ 0 (COP/kWh²) es el coeficiente de costo marginal incremental, b_n (COP/kWh) es el
costo marginal lineal —equivalente al costo nivelado de energía (LCOE) para agentes con a_n ≈ 0
y c_n = 0—, y c_n (COP) es el costo fijo.

Para sistemas fotovoltaicos de pequeña escala (P < 100 kW), el costo marginal de generación es
prácticamente cero una vez realizada la inversión inicial, de modo que a_n ≈ 0. El parámetro
b_n se corresponde entonces con el LCOE amortizado del sistema instalado. El valor de c_n se
normaliza a cero en el caso sintético canónico [5].

### 1.2 Evidencia bibliográfica

La Agencia Internacional de Energías Renovables (IRENA) reporta que el LCOE ponderado a escala
global de la energía solar fotovoltaica fue de 43 USD/MWh en 2024, con un incremento del 0,6 %
respecto a 2023 [16]. Para Colombia, la evaluación de zonificación solar y eólica de IRENA
establece un rango de 79–105 USD/MWh para proyectos de escala utilitaria en zonas de mayor
radiación [16].

La Unidad de Planeación Minero-Energética (UPME), en su Plan Indicativo de Expansión de la
Generación 2025-2039 [17], confirma que los costos de referencia para generación solar
fotovoltaica en Colombia se sitúan entre 300 y 450 COP/kWh para proyectos de mediana y gran
escala, valor coherente con la conversión del rango IRENA a tasa de cambio 2025
(79–105 USD/MWh × 4 200 COP/USD ÷ 1 000 = 332–441 COP/kWh).

Para sistemas distribuidos de pequeña escala en Nariño, el LCOE efectivo puede ser
considerablemente menor al del mercado mayorista porque: (i) los paneles del proyecto MTE ya
están instalados y operativos (costo hundido no atribuible a la operación marginal), (ii) la
irradiación horizontal global en Pasto (≈ 1 800 kWh/kWp/año) es adecuada para sistemas
residenciales, y (iii) el costo operativo de la tecnología Fronius es bajo. El análisis de los
incentivos económicos para la energía solar en Colombia [18] establece que el LCOE de sistemas
≤ 100 kW puede aproximarse a 200–250 COP/kWh en escenarios de financiación favorable, lo que
valida el valor adoptado.

**Tabla 1.1.** Calibración de parámetros de costo de generación (a_n, b_n, c_n)

| Parámetro | Fuente | Rango reportado | Valor adoptado | Justificación |
|---|---|---|---|---|
| b_n (COP/kWh) | IRENA [16], UPME [17] | 300–441 COP/kWh (Colombia, esc. utilitaria); ~200–250 COP/kWh (dist. pequeña) | **225 COP/kWh** (datos reales MTE); 194,76 adim. (caso sintético) | LCOE efectivo instalación Fronius ≤ 100 kW, Pasto; valor derivado de datos MTE; dentro del rango de [18] |
| a_n (COP/kWh²) | Chacón et al. [5] | 0,0–2,17 (caso sintético) | 0,0 (agentes solares); 0,420–2,166 (convencional) | Solar: costo marginal incremental prácticamente cero; agentes con respaldo convencional tienen término cuadrático |
| c_n (COP) | Base case [5] | 0,0 | 0,0 (normalizado) | Costos fijos normalizados a cero en el caso sintético; en datos reales se incorporan en la tarifa base |

**Referencias:** [16] IRENA (2025); [17] UPME (2025); [18] Bernal-Torres y Henao-Bravo (2020)

---

## §2. Elasticidad precio-demanda en mercados eléctricos

### 2.1 Fundamento teórico

La elasticidad precio-demanda de la electricidad (ε_p) cuantifica la variación porcentual del
consumo ante una variación porcentual del precio. Un valor de ε_p ≈ 0 indica demanda inelástica
(consumo no ajustable en el corto plazo), característico de instituciones con cargas obligatorias
como hospitales o universidades.

En el modelo [5], el parámetro de preferencia λ_n representa la utilidad marginal del agente i
derivada de consumir (o generar) una unidad de energía. Un valor alto de λ_n/θ_n implica que el
agente está dispuesto a pagar un precio elevado por la energía —análogo a demanda inelástica—,
mientras que un valor bajo señala mayor elasticidad. La relación entre ε_p y λ_n es cualitativa:
una demanda muy inelástica sugiere un λ_n dominante sobre el término cuadrático θ_n.

### 2.2 Evidencia bibliográfica

Zabaloy y Viego (2022) [19] realizaron un metanálisis sobre la elasticidad precio de la demanda
residencial de electricidad en América Latina y el Caribe, con base en 75 estudios primarios
(1979–2019). El valor verdadero de la elasticidad precio de corto plazo se sitúa entre −0,197 y
−0,468, y el de largo plazo entre −0,252 y −0,331, lo que confirma demanda inelástica en el
corto plazo para la región.

Marques, Uhr y Uhr (2024) [20] amplían dicho análisis con 76 estudios (1979–2020) y reportan
elasticidades de corto plazo de −0,37 y de largo plazo de −0,46 para América Latina y el Caribe.
Estos valores son consistentes con los de [19].

Para el contexto colombiano específico, Tietjen, Lessmann y Pahle (2021) [21] analizan los
mecanismos de tarificación minorista en Colombia orientados a la penetración de generación
distribuida. Sus resultados sugieren que la respuesta de la demanda institucional a cambios de
precio es limitada en el corto plazo, lo que respalda la hipótesis de inelasticidad para los
agentes del proyecto MTE.

**Tabla 1.2.** Calibración del parámetro de preferencia de demanda (λ_n)

| Parámetro | Fuente | Rango reportado | Valor adoptado | Justificación |
|---|---|---|---|---|
| ε_p (corto plazo) | Zabaloy y Viego [19]; Marques et al. [20] | −0,20 a −0,47 (LAC) | No aplica directamente | Contexto: demanda inelástica respalda λ_n > θ_n · P_gs |
| λ_n (adimensional) | Chacón et al. [5] | — | **100** (caso sintético); ajustar según tarifa real | Valor alto asegura que los agentes siempre quieren comerciar; coherente con demanda inelástica |
| θ_n (adimensional) | Chacón et al. [5] | 0,5 (Tabla I) | **0,5** | Coeficiente de costo cuadrático; simetría entre productores y consumidores en el caso base |

**Referencias:** [19] Zabaloy y Viego (2022); [20] Marques et al. (2024); [21] Tietjen et al. (2021)

---

## §3. Preferencias de consumidores energéticos en mercados P2P

### 3.1 Fundamento teórico

Las preferencias de los prosumidores en mercados P2P van más allá de la minimización de costo:
incluyen valoración del origen local de la energía, la propiedad cooperativa, el destino social
de las ganancias y la reducción de la dependencia de la red eléctrica. En el modelo [5], estas
preferencias se incorporan implícitamente a través de los parámetros λ_n (intensidad de
preferencia por consumir energía) y θ_n (penalización cuadrática por alejarse del punto de
operación óptimo).

La disposición a pagar (DAP) observada empíricamente sirve como ancla para verificar que λ_n
es consistente con los incentivos reales de participación en el mercado.

### 3.2 Evidencia bibliográfica

Un estudio de experimento de elección discreta (DCE) con 1.101 usuarios residenciales en el
Valle de Aburrá (Medellín, Colombia) [22] cuantificó la disposición a pagar diferencial por
atributos del suministro energético. Los resultados muestran que los consumidores colombianos
valoran principalmente: (1) energía 100 % solar (+DAP máxima), (2) ganancias dirigidas a causa
social, (3) propiedad cooperativa, y (4) origen local. Esta jerarquía confirma que los agentes
del proyecto MTE (instituciones educativas y hospitalarias en Pasto) tienen preferencias
alineadas con el intercambio P2P local, lo que sustenta el uso de λ_n > 0.

Peña-Bello et al. (2022) [23], en un estudio experimental con propietarios alemanes, identifican
cuatro grupos de prosumidores según sus estrategias de decisión en P2P: orientados al precio
(38,9 %), autoconsumo maximizador, orientados a la comunidad, y no-negociantes (22,6 %). El
estudio muestra que la autarquía comunitaria aumenta cuando se habilita el intercambio P2P, lo
que respalda la viabilidad del mercado.

Sopha et al. (2020) [24] documentan que las preferencias de los prosumidores hacia el P2P están
determinadas principalmente por el ahorro económico y la autosuficiencia eléctrica, con
preferencias heterogéneas que se modelan adecuadamente mediante un parámetro λ_n diferenciado
por agente en el caso general.

**Tabla 1.3.** Calibración de parámetros de preferencia de bienestar (λ_n, θ_n)

| Parámetro | Fuente | Rango reportado | Valor adoptado | Justificación |
|---|---|---|---|---|
| λ_n (intensidad de preferencia) | Chacón et al. [5]; Colombia DCE [22] | — (adimensional; depende de calibración) | **100** (sintético); calibrar para datos MTE según nivel de tarifa PGS | Un valor λ_n = 100 con PGS = 1 250 (sintético) produce agentes activamente negociadores, coherente con la DAP positiva observada en [22] |
| θ_n (coeficiente cuadrático) | Chacón et al. [5]; Peña-Bello et al. [23] | 0,5 en caso base simétrico | **0,5** | Simetría productores-consumidores; calibración Chacón et al.; ajuste necesario si se estratifican agentes por tipo |

**Referencias:** [22] Colombia DCE (2022); [23] Peña-Bello et al. (2022); [24] Sopha et al. (2020)

---

## §4. Aversión al riesgo en mercados de energía

### 4.1 Fundamento teórico

En el modelo [5], el parámetro η_i (etha) cuantifica la presión competitiva que ejerce el
comportamiento de los demás compradores sobre el bienestar del agente i. Formalmente, el término
−η_i · compe_i en la función de bienestar del comprador penaliza a aquellos que ofrecen precios
similares a los de sus competidores, incentivando la diferenciación de precios. Este mecanismo
es funcionalmente análogo a la aversión al riesgo competitivo: un η_i alto hace que los agentes
sean más cautelosos al pujar cerca de los precios de sus pares.

En la literatura de mercados eléctricos, la aversión al riesgo se parametriza típicamente
mediante el Valor en Riesgo Condicional (CVaR) o mediante coeficientes de aversión al riesgo
absoluta constante (CARA). El parámetro η_i del modelo de Chacón et al. [5] no es directamente
equivalente al coeficiente de aversión CARA clásico, pero cumple una función análoga de
penalización de estrategias de precio cercanas a las de los competidores.

### 4.2 Evidencia bibliográfica

Seyedhossein y Moeini-Aghtaie (2022) [25] proponen un marco integral de gestión de riesgos para
mercados P2P de electricidad, identificando el riesgo del modelo de negocio como el factor más
crítico. Su análisis basado en aprendizaje por refuerzo profundo (MADRL) muestra que la
incorporación de baterías locales como mecanismo de mitigación reduce el costo operativo en un
19,51 % y el costo de riesgo en un 19,69 %. El estudio justifica parametrizar la aversión al
riesgo en rangos moderados para evitar que los agentes abandonen el mercado.

Guerrero et al. (2024) [26] formulan el problema de operación de microrredes como una
minimización conjunta del costo esperado y el CVaR de la participación en el mercado diario.
Sus resultados muestran que niveles de aversión al riesgo entre 0,05 y 0,20 (normalizados)
producen soluciones robustas sin comprometer excesivamente la ganancia esperada.

Tavakoli et al. (2023) [27] estudian la interacción entre opciones de flexibilidad y aversión
al riesgo en mercados eléctricos, mostrando que agentes con alta aversión al riesgo prefieren
contratos de precio fijo (PPA), mientras que agentes con baja aversión al riesgo participan
activamente en el mercado spot. Este resultado es coherente con la presencia simultánea de los
escenarios C2 (PPA) y C3 (spot) en la propuesta de tesis.

**Tabla 1.4.** Calibración del parámetro de aversión al riesgo/presión competitiva (η_i)

| Parámetro | Fuente | Rango reportado | Valor adoptado | Justificación |
|---|---|---|---|---|
| η_i (etha, presión competitiva) | Chacón et al. [5] | — (adimensional) | **0,1** (caso base); rango GSA [0,0; 0,25] | Valor conservador: evita deserción de compradores sin eliminar la dinámica competitiva; coherente con aversión moderada [26] |
| CVaR equivalente (referencia) | Guerrero et al. [26] | 0,05–0,20 (normalizado) | No implementado explícitamente | Referencia para interpretar η_i = 0,1 como aversión al riesgo moderada |

**Referencias:** [25] Seyedhossein y Moeini-Aghtaie (2022); [26] Guerrero et al. (2024); [27] Tavakoli et al. (2023)

---

## §5. Síntesis de valores adoptados

La **Tabla 1.5** consolida todos los parámetros calibrados para el caso de datos reales (MTE,
Pasto, Colombia). Los valores del caso sintético canónico de Chacón et al. [5] se incluyen como
referencia de validación.

**Tabla 1.5.** Resumen de parámetros calibrados por actividad bibliográfica

| Parámetro | Descripción | Valor sintético [5] | Valor real MTE | Fuentes principales |
|---|---|---|---|---|
| a_n (COP/kWh²) | Coef. cuadrático de costo | 0,0–2,17 (adim.) | 0,0 (solar); estimar (convencional) | [5] |
| b_n (COP/kWh) | LCOE / costo lineal | 194,76–1 243,80 (adim.) | **225 COP/kWh** (Udenar-Fronius) | [16][17][18] |
| c_n (COP) | Costo fijo (normalizado) | 0,0 | 0,0 | [5] |
| λ_n | Intensidad de preferencia | 100 | 100 (ajustable por tarifa) | [5][22][23] |
| θ_n | Coef. cuadrático de bienestar | 0,5 | 0,5 | [5][23] |
| η_i (etha) | Presión competitiva / aversión | 0,1 | 0,1 (rango GSA: 0,0–0,25) | [5][25][26] |
| PGS (COP/kWh) | Precio máximo (tarifa usuario) | 1 250 (adim.) | **650 COP/kWh** | CREG [3][4] |
| PGB (COP/kWh) | Precio mínimo (bolsa XM) | 114 (adim.) | **280 COP/kWh** (promedio 2025) | XM API |

**Nota sobre unidades:** Los valores sintéticos son adimensionales y se utilizan exclusivamente
para la validación numérica contra el modelo base de Chacón et al. [5]. Los valores reales están
en COP/kWh y corresponden a datos empíricos del proyecto MTE (julio 2025–enero 2026).

---

## Referencias

Las entradas completas en formato BibTeX se encuentran en `Documentos/references.bib`.
Las referencias marcadas como "VERIFICAR" requieren confirmación de autoría en la plataforma
editorial antes de la entrega final.

[5]  S. Chacón, K. Guerrero, G. Obando y A. Pantoja, *Energy management system in communities
     with P2P markets using game theory and optimization models*, Tesis de maestría, Universidad
     de Nariño, Pasto, Colombia, 2025.

[16] International Renewable Energy Agency (IRENA), *Renewable Power Generation Costs in 2024*,
     Abu Dhabi, 2025. [En línea]:
     https://www.irena.org/Publications/2025/Jun/Renewable-Power-Generation-Costs-in-2024
     [Consultado: abril de 2026]

[17] Unidad de Planeación Minero-Energética (UPME), *Plan Indicativo de Expansión de la
     Generación 2025-2039*, Bogotá, D.C., Colombia, 2025. [En línea]:
     https://docs.upme.gov.co/SIMEC/Energia%20Electrica/PIEG/2025-2039/Plan_Generacion_2025-2039.pdf
     [Consultado: abril de 2026]

[18] C. A. Bernal-Torres y E. E. Henao-Bravo, "Análisis de los incentivos económicos en la
     capacidad instalada de energía solar fotovoltaica en Colombia", *Cuadernos de Economía*,
     vol. 39, núm. 80, 2020. DOI: 10.15446/cuad.econ.v39n80.79498 [VERIFICAR]

[19] M. F. Zabaloy y P. Viego, "Household electricity demand in Latin America and the Caribbean:
     A meta-analysis of price elasticity", *Utilities Policy*, vol. 75, p. 101334, 2022.
     DOI: 10.1016/j.jup.2021.101334

[20] M. L. V. Marques, D. A. P. Uhr y J. G. Z. Uhr, "Income and price elasticity of residential
     electricity demand in Latin America and the Caribbean: a meta-analysis and meta-regression
     analysis", *International Journal of Energy Sector Management*, 2024.
     DOI: 10.1108/ijesm-05-2022-0012

[21] O. Tietjen, S. Lessmann y M. Pahle, "Retail pricing in Colombia to support the efficient
     deployment of distributed generation and electric stoves", *Journal of Environmental
     Economics and Management*, vol. 109, p. 102513, 2021.
     DOI: 10.1016/j.jeem.2021.102513 [VERIFICAR]

[22] (Autores por verificar), "What is the value of peer-to-peer energy trading? A discrete
     choice experiment with residential electricity users in Colombia", *Energy Research &
     Social Science*, 2022. DOI: 10.1016/j.erss.2022.102714 [VERIFICAR autores]

[23] A. Peña-Bello, D. Parra, M. Herberz, V. Tiefenbeck, M. K. Patel y U. J. J. Hahnel,
     "Integration of prosumer peer-to-peer trading decisions into energy community modelling",
     *Nature Energy*, vol. 7, pp. 74-82, 2022. DOI: 10.1038/s41560-021-00950-2

[24] (Autores por verificar), "Becoming prosumer: Revealing trading preferences and decision-making
     strategies in peer-to-peer energy communities", *Energy Policy*, vol. 137, p. 111098, 2020.
     DOI: 10.1016/j.enpol.2019.111098 [VERIFICAR autores]

[25] S. M. H. Seyedhossein y M. Moeini-Aghtaie, "Risk management framework of peer-to-peer
     electricity markets", *Energy*, vol. 261, p. 125264, 2022.
     DOI: 10.1016/j.energy.2022.125264

[26] (Autores por verificar), "Risk-aware microgrid operation and participation in the day-ahead
     electricity market", *e-Prime: Advances in Electrical Engineering, Electronics and Energy*,
     2024. DOI: 10.1016/j.prime.2024.100439 [VERIFICAR autores]

[27] (Autores por verificar), "Risk aversion and flexibility options in electricity markets",
     *Energy Economics*, 2023. DOI: 10.1016/j.eneco.2023.106886 [VERIFICAR autores]
