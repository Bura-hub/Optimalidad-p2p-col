# Interfaz del núcleo para los módulos que lo consumen

**Estado al 2026-09-17.** Contrato de llamada del núcleo del mercado entre pares,
para el módulo que lo integra en la plataforma MTE. Congelación prevista de
`core/`: **26 de septiembre de 2026**.

Lo que cambia respecto de la copia fijada en `a392cbd`: **el mercado de cada
hora ya no se resuelve integrando la dinámica hasta un horizonte, sino
calculando en forma cerrada el reposo del juego** (D48). El precio lo fija el
piso del vendedor marginal (D63 a D70). Las dos vías anteriores siguen ahí, sin
cambiar ni un bit, para validar y dibujar.

---

## 1. Qué ficheros necesita la copia

A los once de la copia actual hay que añadir **dos**:

| Fichero | Por qué |
|---|---|
| `core/reposo_mercado.py` | **Nuevo.** Es donde vive el mercado de una hora |
| `data/cedenar_tariff.py` | El techo de cada comprador sale de los componentes del costo unitario oficial |

De los once, cambian cuatro: `core/almacen.py`, `core/coupled_ode_convergence.py`,
`core/ems_p2p.py` y `core/replicator_buyers.py`. Los otros siete no.

---

## 2. Tres formas de llamar, de la más simple a la más pesada

**La recomendada para una plataforma es la primera.**

### 2.1 El núcleo puro, `resuelve_reposo`

Una función sin estado, sin procesos y sin integrador. Cuesta unos 5 (ms) por
hora, y como no integra nada **da lo mismo en cualquier máquina**, que es lo que
no ocurría con la vía anterior (H-84).

```python
from core.reposo_mercado import resuelve_reposo

r = resuelve_reposo(
        s,            # (J,) excedente neto de cada vendedor, kWh
        d,            # (I,) déficit neto de cada comprador, kWh
        b,            # (J,) costo lineal de cada vendedor, COP/kWh
        techo,        # (I,) o escalar: costo unitario de cada comprador
        piso_j,       # (J,) o escalar: alternativa de cada vendedor
        modo_presupuesto="sigma",     # "sigma" | "algoritmo3" | "c136"
        sigma=None,                   # None = (I-1)/I
        pi_gs=None,                   # solo con "algoritmo3"
        regla_precio="uniforme",      # "uniforme" | "puja"
        despacho_vendedores="piso",   # "piso" | "costo" | "llenado"
        mu_cuantal=1.0,               # 0.0 = la forma cerrada estricta de 05ed9c3
)
```

**Los cinco primeros son posicionales; el resto, solo por nombre.** Con los
defectos escritos arriba se obtiene la configuración de producción.

Lanza `ValueError`, nunca devuelve un resultado silencioso: entradas no finitas
o negativas, longitudes que no casan, opciones desconocidas, y cualquier
identidad rota (la cobertura de cada vendedor, el piso marginal, la suma del
presupuesto, la conservación del ingreso, la descomposición de la prima). No
queda ningún `assert` en el módulo: las 58 salidas de error son `ValueError`.

### 2.2 El motor, `EMSP2P.run_single_hour`

Igual que antes, con `SolverParams(metodo="reposo", ...)`. Añade la restricción
de participación, el almacén y las líneas del registro.

### 2.3 La tupla del trabajador

Sigue existiendo y **acepta las longitudes antiguas**: una tupla de 22 campos
resuelve hoy exactamente como resolvía en `a392cbd`, por la vía alternada. Ver
el apartado 5.

---

## 3. Qué devuelve: `ReposoHora`

| Campo | Qué es |
|---|---|
| `P` | (J, I) energía de cada pareja (kWh), emparejamiento de rango uno |
| `q` | (I,) energía que recibe cada comprador (kWh) |
| `s_despachado` | (J,) energía que coloca cada vendedor (kWh) |
| `E` | volumen de la hora (kWh) |
| `piso`, `piso_marginal` | el piso del juego, que es el del vendedor marginal (COP/kWh) |
| `S`, `ell` | presupuesto de precios y nivel del grupo marginal |
| `pi_reposo` | (I,) precio del reposo de cada comprador (COP/kWh) |
| `p_u` | precio uniforme de la hora que conserva el ingreso (COP/kWh) |
| `p_liquidado` | (I,) lo que paga cada comprador: `min(p_u, techo_i)` con la regla uniforme |
| `regimen` | `interiores`, `topados`, `excluidos`, `suma_no_cabe`, `compradores_cortos`, `un_comprador`, `mixto`, `sin_ganancia`, `sin_mercado` y, desde D71, `cuantal` |
| `regimen_cerrado` | el régimen que habría dado la forma cerrada; igual a `regimen` salvo en las horas cuantales |
| `apartamiento` | cuánto se aparta, en fracción de E, la respuesta cuantal del reparto cerrado; la hora es frágil si pasa de 1e-3. Se publica siempre |
| `mu_cuantal` | con qué μ se resolvió la rama cuantal (0 = apagada) |
| `excluidos`, `excluidos_bajo_piso` | compradores sin energía: en su techo, o fuera por quedar bajo el piso del juego |
| `vendedores_excluidos`, `vendedores_no_despachados` | vendedores sin ganancia posible, y los que el mercado deja fuera por piso alto |
| `orden_merito` | el orden en que se despachó |
| `n_soluciones` | cuántos reposos había; 1 en todas las horas reales medidas |
| `excedente`, `ingreso_vendedores`, `parte_vendedor` | el excedente de la hora, lo que cobra cada vendedor y la parte que se lleva el lado vendedor |
| `renta_inframarginal`, `parte_juego` | la prima descompuesta (D69): lo que gana el vendedor por estar bajo el marginal, y lo que gana el lado vendedor en la negociación |
| `modo_presupuesto`, `sigma`, `regla_precio`, `despacho_vendedores` | con qué se resolvió |

Funciones auxiliares públicas del mismo módulo: `despacho_competitivo`,
`presupuesto_precios`, `ingreso_por_vendedor`, `cotas_optimalidad` y `captura`.

---

## 4. De dónde salen las cinco entradas

| Entrada | Cómo se arma |
|---|---|
| `s`, `d` | excedente y déficit netos de la hora, después de `core.market_prep.classify_agents` |
| `b` | `data.xm_prices.get_b_for_real_data(N, nombres)` |
| `techo` | `data.cedenar_tariff.cu_components_per_agent_hourly`, suma de componentes del costo unitario oficial, matriz (N, T) constante dentro del mes |
| `piso_j` | `core.opciones_externas.deduccion_art25` y `piso_residual`: permuta mientras la inyección acumulada del mes no supera la importación del mes, y bolsa desde la hora de corte (art. 25, C-175, C-177) |

**El piso es heterogéneo entre vendedores dentro de la misma hora**, y eso es
justo lo que obligó a la regla nueva: con un solo piso de juego, el vendedor en
permuta cobraba bajo su alternativa.

---

## 5. La tupla del trabajador: 41 campos

En este orden:

```
 1 k                    15 t_span                29 presupuesto_eval_acoplado
 2 G_klim_k             16 n_points              30 arranque_acoplado
 3 D_k                  17 min_iter              31 criterio_estacionario
 4 G_raw_k              18 tol                   32 tol_reparto
 5 seller_ids           19 max_iter              33 modo_presupuesto
 6 buyer_ids            20 ode_method            34 sigma_nivel
 7 a_all                21 buyer_competition     35 regla_precio
 8 b_all                22 metodo                36 despacho_vendedores
 9 lam_all              23 t_span_acoplado       37 mu_entropia
10 theta_all            24 pi_gb_j               38 nivel_acoplado
11 etha_all             25 guarda_trayectorias   39 costo_vendedor
12 pi_gs                26 (reservado)           40 piso_juego
13 pi_gb                27 rtol_acoplado         41 mu_cuantal
14 tau_buyers           28 horizonte_max_acoplado
```

**Compatibilidad hacia atrás.** Las longitudes 22, 24, 25, 26, 28, 29, 30, 32,
36, 38 y 40 se rellenan solas con los defectos. La de 40 rellena
`mu_cuantal = 1,0`, igual que D64 rellenó el despacho de producción: una tupla
de 40 campos resuelve con la rama cuantal en las horas frágiles, y para el
comportamiento de 05ed9c3 hay que pasar 0,0. Una tupla de 22 campos
resuelve hoy igual que en `a392cbd`, al bit. Para pedir el mercado nuevo basta
llegar a 36 (los campos 37 a 40 solo actúan por la vía acoplada), o llamar al
núcleo directamente.

---

## 6. Qué sobrevive, qué queda inerte y qué es nuevo

Con `metodo="reposo"`:

**Inertes, porque no se integra nada.** `t_span_acoplado`, `rtol_acoplado`,
`horizonte_max_acoplado`, `presupuesto_eval_acoplado`, `arranque_acoplado`,
`criterio_estacionario`, `tol_reparto`, `ode_method`, `t_span`, `n_points`,
`tau`, `tau_buyers`, `min_iter`, `tol`, `max_iter`, `mu_entropia`,
`nivel_acoplado`, `costo_vendedor` y `piso_juego`. No se rechazan: se validan,
se ignoran, y el resultado no depende de ellos. Los tres últimos son las
palancas de la dinámica regularizada y de la vía acoplada (D49, D50 y D68), que
sirven para comprobar que el reposo es donde la dinámica se detiene; el módulo
no las necesita.

**Sin trayectoria.** `guarda_trayectorias` no produce nada por esta vía: no hay
integración que guardar. El almacén escribe la tabla de trayectorias vacía.

**Rechazado en voz alta.** Un costo cuadrático `a_j` distinto de cero (CAL-32):
el reposo lo supone cero y no lo silencia.

**Nuevos y con efecto.** `modo_presupuesto`, `sigma_nivel`, `regla_precio`,
`despacho_vendedores` y `mu_cuantal` (D71). `merito` se acepta como alias de
`costo`, con aviso.

---

## 7. La restricción de participación

Con el piso marginal, **ningún vendedor despachado puede cobrar por debajo de su
alternativa**: es un teorema del emparejamiento de rango uno, y el núcleo lo
comprueba como identidad. Por eso la restricción de participación queda como
guarda que debe salir inerte (D67).

Recomendación para el módulo: **no implementar el lazo de retiro**, sino la
comprobación. Si alguna hora la incumple, parar y reportar, que es lo que hace
aquí la corrida (sale con código 3) y la compuerta de salida de la matriz.

```python
ingreso = r.ingreso_vendedores          # COP por vendedor
ok = all(ingreso[j] >= piso_j[j] * r.s_despachado[j] - 1e-9 * max(1, piso_j[j])
         for j in range(len(s)) if r.s_despachado[j] > 0)
```

---

## 8. Determinismo y tolerancias

- El resultado **no depende de la plataforma** en las horas no frágiles: no hay
  integrador. En las horas cuantales (D71), la respuesta usa `exp` y `log`, que
  dependen de la CPU: el reparto de esas horas y el `apartamiento`, que se
  publica en todas, pueden diferir en el último bit entre máquinas. Para
  comparar entre máquinas, en esos campos se usa tolerancia y no igualdad.
- Identidad de energía: 1e-9 relativa al volumen de la hora.
- Precios: 1e-7 (COP/kWh) separan dos precios distintos.
- Conservación del ingreso en la liquidación: 1e-9 relativa.
- El almacén guarda en precisión sencilla; las comprobaciones del motor y del
  núcleo van en doble.

---

## 9. Lo que cambió o puede cambiar antes del 26 de septiembre

- **`despacho_vendedores` NO cambia** (decisión del 2026-09-19). La medición M-B
  no pudo decidir D64 porque los regímenes que discriminan son rígidos y la
  dinámica no llega al reposo en un tiempo de cómputo razonable. D64 queda como
  regla declarada, sostenida por el costo de oportunidad del vendedor. Si algún
  día pasara a `"costo"`, el núcleo no necesitaría ningún insumo nuevo: usa el
  `b` que ya recibe.
- **La rama cuantal (D71), adoptada.** En las horas frágiles, la forma cerrada
  no es un reposo estable de la dinámica, y el núcleo publica el reposo del
  juego regularizado con μ = 1, también en forma cerrada (una bisección por
  hora, sin integrar):
  - **Cuándo pasa:** el precio común queda muy cerca del techo de un comprador
    que no recibe energía. En los datos ocurre cuando el interior (Cesmag)
    queda a menos de ~7-8 (COP/kWh) sobre el techo de ASC, casi siempre en
    abril de 2025.
  - **Cuántas horas:** 216 de 15 363 horas con mercado en los 13 casos de la
    tesis (0,40 % de la energía; cambia de manos el 0,034 %).
  - **Cómo se reconocen:** por `regimen == "cuantal"`. `regimen_cerrado` dice
    qué habría dado la forma cerrada, y `apartamiento`, cuánto se aparta.
  - **La llamada no cambia:** `mu_cuantal=1.0` es el defecto. **Las horas no
    frágiles dan lo mismo al bit.** Con `mu_cuantal=0.0` todo es igual que en
    05ed9c3.
  - **Límite declarado:** el reparto de esas horas depende de μ, y μ = 1 es una
    elección de modelado (D49), no una medida.
- **Los arreglos de precios (commit P1)**, en las dos funciones que importa el
  módulo. **Los valores que ve hoy no cambian**, comprobado al bit contra
  05ed9c3:
  - el vector `b` de los cinco nombres;
  - la llamada `apply_creg101066_ceiling(np.full(24, p), "YYYY-MM-DD",
    level="PES", csv_path=<tabla de una fila>)`, el día 1 y el último día del
    mes.

  Lo que cambia:
  - **Ahora fallan en voz alta** tres casos que antes daban un número inventado:
    - **un mes fuera de la tabla de techos.** La fila única tiene que llevar la
      etiqueta **del mes pedido**, con su valor arrastrado si es el caso. Si
      lleva la del mes del que se arrastra, 05ed9c3 propagaba el valor y ahora
      lanza `ValueError`: es el único punto de su uso actual en que P1 se nota;
    - un `pi_bolsa` con NaN o infinito;
    - un nombre de agente que no está exactamente en la tabla.
  - **Ahora funcionan** dos casos que antes fallaban o se equivocaban:
    - un horizonte que no llega a la medianoche del día siguiente devuelve el
      techo correcto, y no un `KeyError`;
    - una fecha con zona horaria se convierte a la hora de Bogotá.
  - **Una fecha sin zona sigue significando hora local de Bogotá**, como antes.

  Además, importar `data/xm_prices.py` ya no silencia los avisos de todo el
  proceso.
- **La caché de bolsa (commit P2)** no alcanza al módulo por código: es de la
  tesis.
- Nada más está previsto.
