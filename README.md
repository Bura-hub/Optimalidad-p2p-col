# Tesis: Análisis de Optimalidad y Validación Regulatoria de Mercados P2P en Colombia
**Autor:** Brayan S. Lopez-Mendez  
**Asesores:** Andrés Pantoja / Germán Obando  
**Maestría en Ingeniería Electrónica — Universidad de Nariño, 2026**

---

## Estructura del proyecto

```
tesis_p2p/
├── core/                        # Modelo P2P base (Chacón et al., 2025)
│   ├── generation_limit.py      # Algoritmo 1: G_klim + DR program
│   ├── replicator_sellers.py    # Algoritmo 2: RD vendedores + LR
│   ├── replicator_buyers.py     # Algoritmo 3: RD compradores + LR
│   ├── settlement.py            # Liquidación residual + métricas
│   └── ems_p2p.py               # Motor EMS principal (7 pasos)
│
├── scenarios/                   # Escenarios regulatorios colombianos
│   ├── scenario_c1_creg174.py   # C1: Autogeneración individual CREG 174/2021
│   ├── scenario_c4_creg101072.py# C4: Autogeneración colectiva CREG 101 072/2025 ★
│   └── [c2_bilateral.py]        # TODO: Contratos PPA
│   └── [c3_spot.py]             # TODO: Exposición mercado mayorista
│
├── data/
│   ├── base_case_data.py        # Datos de validación (6 agentes, 24h)
│   └── [xm_data_loader.py]      # TODO: Cargador datos reales XM
│
├── analysis/                    # TODO: Análisis de sensibilidad
├── tests/
│   └── validate_base_model.py   # Validación contra modelo base
└── notebooks/                   # TODO: Jupyter notebooks comparativos
```

## Estado actual (Objetivo 1 — Actividades 1.0 y 1.1)

✅ Implementados:
- Algoritmo 1 completo (G_klim + DR)
- Algoritmos 2 y 3 (RD + LR vendedores y compradores)
- Motor EMS completo con juego de Stackelberg iterativo
- Escenarios C1 (CREG 174) y C4 (CREG 101 072)
- Suite de validación contra resultados del modelo base

🔲 Pendiente:
- Escenarios C2 (contratos bilaterales) y C3 (mercado spot)
- Cargador de datos reales XM (precios de bolsa históricos)
- Calibración de parámetros con datos de comunidad real
- Análisis de sensibilidad (Objetivo 4)
- Notebooks de visualización comparativa

## Cómo ejecutar la validación

```bash
cd tesis_p2p
python tests/validate_base_model.py
```

## Resultados de validación (datos sintéticos)

| Test | Resultado | Referencia modelo base |
|------|-----------|----------------------|
| Limitación generación | Agente 1 restringido ✓ | Solo agente 1 limitado |
| DR reduce transacciones | Funcional ✓ | ~24% ventas, ~53% compras |
| Mercado P2P hora 14h | Converge ✓ | 2 vendedores, 4 compradores |
| SC hora 14h | 0.608 | ~similar |
| SS hora 14h | 0.761 | ~similar |

## Parámetros clave para calibración (Actividad 1.2)

| Parámetro | Descripción | Rango bibliográfico |
|-----------|-------------|---------------------|
| `a_n, b_n, c_n` | Costos de generación | Ver Tabla I Chacón et al. |
| `lambda_n, theta_n` | Preferencias autoconsumo | Calibrar con perfiles reales |
| `beta_i` | Urgencia de adquisición | 0.1 – 10.0 |
| `alpha_n` | Fracción flexible DR | 0.0 – 0.5 |
| `pi_gs, pi_gb` | Precios de red | Datos XM Colombia |
| `PDE_n` | Distribución excedentes C4 | Proporcional a capacidad |

## Notas sobre dimensiones

- Potencia: kW
- Energía: kWh  
- Precios: $/kWh (ajustar escala para COP/kWh con datos reales)
- Horizonte base: 24 horas (escalar a 6 meses para tesis)
