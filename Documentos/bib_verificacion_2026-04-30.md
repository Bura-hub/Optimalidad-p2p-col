# Verificacion de bibliografia — Auditoria CrossRef 2026-04-30

**Autor:** Brayan S. Lopez-Mendez | **Sesion:** Tier 1.1 deep-research Ruflo
**Archivo verificado:** `Documentos/references.bib` (entradas marcadas `VERIFICAR`)

---

## Resumen ejecutivo

De las **6 entradas marcadas `VERIFICAR`** en el `.bib`, la auditoria
contra CrossRef revelo errores en TODAS:

- **5 entradas con DOI INCORRECTO** (apuntan a papers distintos al
  citado): Tietjen2021Retail, Colombia2022P2P,
  Guerrero2023RiskMicrogrid, Tavakoli2023RiskAversion,
  BernalTorres2020Solar.
- **1 entrada con DOI correcto pero autores incorrectos**:
  Sopha2020Prosumer.

Los DOIs estimados a partir de codigos PII fueron sistematicamente
incorrectos — el offset numerico (off-by-N en el ultimo bloque del DOI)
es la causa probable. **Recomendacion: nunca estimar DOIs por PII;
siempre resolverlos contra CrossRef o el sitio editorial**.

---

## Correcciones requeridas

### 1. `BernalTorres2020Solar` (L221) — REEMPLAZAR ENTRADA COMPLETA

| Campo | Actual (.bib) | Correcto (CrossRef) |
|---|---|---|
| Autores | Bernal-Torres, C.A.; Henao-Bravo, E.E. | **Castaño-Gomez, M.; Garcia-Rendon, J.J.** |
| Journal | Cuadernos de Economia | **Lecturas de Economia** |
| Volumen | 39 | **n93** (sin volumen tradicional) |
| Issue | 80 | n93a338727 |
| Year | 2020 | 2020 ✓ |
| DOI | 10.15446/cuad.econ.v39n80.79498 ❌ | **10.17533/udea.le.n93a338727** |

**BibTeX corregido**:
```bibtex
@article{Castano2020Solar,
  author  = {Castaño-Gómez, Manuela and García-Rendón, John Jairo},
  title   = {Análisis de los incentivos económicos en la capacidad
             instalada de energía solar fotovoltaica en {Colombia}},
  journal = {Lecturas de Economía},
  number  = {93},
  year    = {2020},
  doi     = {10.17533/udea.le.n93a338727}
}
```

**Confianza:** alta (resultado directo de busqueda CrossRef con titulo
exacto). Renombrar key `BernalTorres2020Solar` -> `Castano2020Solar` en
todo `.tex` que lo referencie.

---

### 2. `Tietjen2021Retail` (L259) — REEMPLAZAR AUTORES Y DOI

| Campo | Actual | Correcto |
|---|---|---|
| Autores | Tietjen, Lessmann, Pahle | **McRae, Shaun D.; Wolak, Frank A.** |
| Journal | JEEM | JEEM ✓ |
| Volumen | 109 | **(verificar — CrossRef solo dio year)** |
| Year | 2021 | 2021 ✓ |
| DOI | 10.1016/j.jeem.2021.102513 ❌ | **10.1016/j.jeem.2021.102541** (off by 28) |

**BibTeX corregido**:
```bibtex
@article{McRae2021Retail,
  author  = {McRae, Shaun D. and Wolak, Frank A.},
  title   = {Retail pricing in {Colombia} to support the efficient
             deployment of distributed generation and electric stoves},
  journal = {Journal of Environmental Economics and Management},
  year    = {2021},
  doi     = {10.1016/j.jeem.2021.102541}
}
```

**Confianza:** alta. Renombrar key `Tietjen2021Retail` -> `McRae2021Retail`.

**Nota:** la version IADB working paper (DOI 10.18235/0002192) cita
"electric vehicles" no "stoves"; el paper de JEEM 2021 es el version
final.

---

### 3. `Colombia2022P2P` (L276) — COMPLETAR AUTORES Y CORREGIR DOI

| Campo | Actual | Correcto |
|---|---|---|
| Autores | "Autores por verificar" | **Cárdenas-Álvarez, J.P.; España, J.M.; Ortega, S.** |
| Journal | Energy Research & SS | Energy Research & SS ✓ |
| Year | 2022 | 2022 ✓ |
| DOI | 10.1016/j.erss.2022.102714 ❌ | **10.1016/j.erss.2022.102737** (off by 23) |

**BibTeX corregido**:
```bibtex
@article{Cardenas2022P2P,
  author  = {Cárdenas-Álvarez, Juan Pablo and España, Juan Manuel and Ortega, Santiago},
  title   = {What is the value of peer-to-peer energy trading? {A}
             discrete choice experiment with residential electricity
             users in {Colombia}},
  journal = {Energy Research {\&} Social Science},
  year    = {2022},
  doi     = {10.1016/j.erss.2022.102737},
  note    = {Estudio con 1.101 usuarios del Valle de Aburra, Medellin}
}
```

**Confianza:** alta. Renombrar key `Colombia2022P2P` -> `Cardenas2022P2P`.

---

### 4. `Sopha2020Prosumer` (L301) — REEMPLAZAR AUTORES (DOI correcto)

| Campo | Actual | Correcto |
|---|---|---|
| Autores | Sopha, Klöckner, Hertwich | **Hahnel, Ulf J.J.; Herberz, Mario; Peña-Bello, Alejandro; Parra, David; Brosch, Tobias** |
| Journal | Energy Policy | Energy Policy ✓ |
| Volumen | 137 | 137 ✓ |
| Year | 2020 | 2020 ✓ |
| DOI | 10.1016/j.enpol.2019.111098 | 10.1016/j.enpol.2019.111098 ✓ |

**BibTeX corregido**:
```bibtex
@article{Hahnel2020Prosumer,
  author  = {Hahnel, Ulf J.J. and Herberz, Mario and Peña-Bello,
             Alejandro and Parra, David and Brosch, Tobias},
  title   = {Becoming prosumer: Revealing trading preferences and
             decision-making strategies in peer-to-peer energy communities},
  journal = {Energy Policy},
  volume  = {137},
  pages   = {111098},
  year    = {2020},
  doi     = {10.1016/j.enpol.2019.111098}
}
```

**Confianza:** alta. Renombrar key `Sopha2020Prosumer` -> `Hahnel2020Prosumer`.

**Nota:** los autores correctos coinciden con `PenaBello2022Prosumer`
(Nature Energy 2022) — es el mismo grupo de investigacion (Hahnel,
Herberz, Pena-Bello, Parra). Coherente.

---

### 5. `Guerrero2023RiskMicrogrid` (L327) — REEMPLAZAR ENTRADA COMPLETA

| Campo | Actual | Correcto |
|---|---|---|
| Autores | Guerrero, J.M. y otros | **Herding, R.; Ross, E.; Jones, W.R.; Endler, E.; Charitopoulos, V.M.; Papageorgiou, L.G.** |
| Journal | e-Prime | **Advances in Applied Energy** |
| Year | 2024 | 2024 ✓ |
| DOI | 10.1016/j.prime.2024.100439 ❌ | **10.1016/j.adapen.2024.100180** |

El DOI 10.1016/j.prime.2024.100439 apunta a un paper sobre "transistores
GNR" — no relacionado.

**BibTeX corregido**:
```bibtex
@article{Herding2024RiskMicrogrid,
  author  = {Herding, Robert and Ross, Emma and Jones, Wayne R. and
             Endler, Elizabeth and Charitopoulos, Vassilis M. and
             Papageorgiou, Lazaros G.},
  title   = {Risk-aware microgrid operation and participation in the
             day-ahead electricity market},
  journal = {Advances in Applied Energy},
  volume  = {15},
  pages   = {100180},
  year    = {2024},
  doi     = {10.1016/j.adapen.2024.100180}
}
```

**Confianza:** alta. Renombrar key `Guerrero2023RiskMicrogrid` ->
`Herding2024RiskMicrogrid`.

---

### 6. `Tavakoli2023RiskAversion` (L338) — REEMPLAZAR ENTRADA COMPLETA

| Campo | Actual | Correcto |
|---|---|---|
| Autores | Tavakoli, Mahdi y otros | **Möbius, T.; Riepin, I.; Müsgens, F.; van der Weijde, A.H.** |
| Journal | Energy Economics | Energy Economics ✓ |
| Year | 2023 | 2023 ✓ |
| DOI | 10.1016/j.eneco.2023.106886 ❌ | **10.1016/j.eneco.2023.106767** (off by 119) |

El DOI 10.1016/j.eneco.2023.106886 apunta a "Social media and energy
justice" — no relacionado.

**BibTeX corregido**:
```bibtex
@article{Mobius2023RiskAversion,
  author  = {Möbius, Thomas and Riepin, Iegor and Müsgens, Felix and
             van der Weijde, Adriaan H.},
  title   = {Risk aversion and flexibility options in electricity markets},
  journal = {Energy Economics},
  year    = {2023},
  doi     = {10.1016/j.eneco.2023.106767}
}
```

**Confianza:** alta. Renombrar key `Tavakoli2023RiskAversion` ->
`Mobius2023RiskAversion`.

---

## Plan de aplicacion

1. **Backup**: copiar `Documentos/references.bib` a
   `Documentos/references.bib.bak_2026-04-30` antes de editar.
2. **Reemplazar las 6 entradas** con los BibTeX corregidos arriba.
3. **Renombrar las keys** en TODOS los `\cite{}` de `Documentos/FinalTesis/*.tex`:
   - `BernalTorres2020Solar` → `Castano2020Solar`
   - `Tietjen2021Retail` → `McRae2021Retail`
   - `Colombia2022P2P` → `Cardenas2022P2P`
   - `Sopha2020Prosumer` → `Hahnel2020Prosumer`
   - `Guerrero2023RiskMicrogrid` → `Herding2024RiskMicrogrid`
   - `Tavakoli2023RiskAversion` → `Mobius2023RiskAversion`
4. **Eliminar la marca `note = {VERIFICAR ...}`** de cada entrada.
5. **Compilar la tesis** y revisar que las citas resuelvan correctamente.
6. **Actualizar `Documentos/notas_modelo_tesis.md` §A.7** con la fecha
   de cierre de la verificacion bibliografica.

## Riesgos detectados

- Si las entradas estaban siendo citadas en el manuscrito por temas
  asociados (p.ej. "preferencias de prosumidores" via Sopha), las
  ideas siguen siendo validas — solo cambian autor/journal/DOI. Pero
  si se citaba por **autoridad institucional** (p.ej. "Sopha del NTNU
  Noruega"), revisar que la nueva atribucion (Hahnel, Universidad de
  Geneva) sea coherente con el argumento.
- El DOI offset sistematico (off by 23-119) sugiere que la version
  inicial del .bib uso una herramienta de estimacion de DOIs por PII
  con bug. Cualquier OTRA entrada agregada por la misma via deberia
  re-verificarse contra CrossRef.

## Comandos para reproducir

```bash
# Verificar un DOI especifico:
curl -s "https://api.crossref.org/works/<DOI>" | jq '.message | {author, title, "container-title", DOI}'

# Buscar por titulo:
curl -s "https://api.crossref.org/works?query.bibliographic=<terms>&rows=3" | jq '.message.items[] | {author, title, DOI}'
```

## Persistencia en memoria semantica

Cada correccion queda registrada en namespace `bibliografia` con key
`bib-fix-<old_key>` para futura recuperacion.
