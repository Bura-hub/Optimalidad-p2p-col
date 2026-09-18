"""M-A: la forma cerrada frente a la dinamica regularizada, regimen por regimen.

QUE DECIDE. Si cada regimen se publica en la tesis como «el reposo al que la
dinamica llega» o como «regla declarada». Es la medicion que rotula los
resultados, no la que los produce: la matriz ya corrio.

COMO. Diez horas de cada regimen (`selecciona_horas.py`), integradas con la
exploracion entropica del vendedor (mu = 1 (COP/kWh), D49), los precios
arrancando en el presupuesto sigma (`nivel="sigma"`, D50) y el piso del juego
en el del vendedor marginal (D63), con las dos aceleraciones del arnes
(k = 100 y k = 1 000) hasta el tiempo equivalente 160. En cada punto de control
se mide la distancia al reposo que `core/reposo_mercado.py` calcula para esa
misma hora.

EL BRAZO SIN ACELERAR (critico 2 de la revision de 4c). En los grupos libres
(«interiores» y «la suma no cabe») cada hora se integra tambien con k = 1
hasta t = 160, con el tope de 3 600 (s). Alli la sonda del consenso midio que
cabe: la 109 y la K1 152 llegaron a t = 40 con 50 000 a 100 000 evaluaciones,
y la 2120 a la esquina hacia t = 20 con 64 000. Es el unico brazo que se juzga
con la tolerancia ESTRICTA del plan, que sin el era codigo muerto. Va en una
familia aparte («V3a sin acelerar») de la de las dos aceleraciones («V3a
acelerada»), porque responden preguntas distintas: si la aceleracion llega al
reposo con la tolerancia floja, y si la dinamica sin acelerar llega con la
estricta. Una corrida que no cabe se corta y se publica como «cortada», que es
informacion, no un fallo. En los grupos rigidos no hay brazo k = 1: alli se
estimaron 1e9 evaluaciones por hora.

ACEPTACION, fijada de antemano (sec. 11 de fable-report.md): en teq 80 y en
teq 160, max|q - q_cerrada| <= 1e-3·E (kWh) y max|p - p_cerrada| <= 0,05
(COP/kWh) con compradores libres y sin acelerar; 1 % de E y 0,5 (COP/kWh) con
topados o con aceleracion. Un regimen con el 95 % o mas de sus horas dentro se
publica como reposo verificado, con cinco horas juzgadas como minimo.

COSTO. De 1e6 a 1e7 evaluaciones del lado derecho por corrida acelerada (sec. 4
del informe del consenso), es decir de 1 a 10 (min) a 60 (us) por evaluacion
en el servidor; el brazo sin acelerar, de 5e4 a 1e5 hasta t = 40 en las horas
medidas, del orden de un minuto hasta t = 160. Tope de 3 600 (s) por corrida.
Seis grupos por diez horas por dos aceleraciones son 120 corridas, mas 20 del
brazo sin acelerar: 140.
"""
GRUPOS = ("interiores", "topados", "suma_no_cabe", "mixto", "dos_vendedores",
          "compradores_cortos_sin_cesmag")
CASOS = ("E0", "K1", "E4", "E5")
POR_GRUPO = 10
MU = 1.0
TOPE = 3600.0

MEDICION = "M-A"
QUE_DECIDE = ("reposo verificado o regla declarada, por regimen")

# Los cortes estan en tiempo del integrador; el equivalente es t·k. Con las dos
# aceleraciones los puntos de control caen en teq 0, 2, 5, 10, 20, 40, 80 y 160,
# de modo que los dos criterios (teq 80 y teq 160) existen en las dos.
CORTES = {1000.0: [0, 2e-3, 5e-3, 1e-2, 2e-2, 4e-2, 8e-2, 0.16],
          100.0: [0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6],
          1.0: [0, 2, 5, 10, 20, 40, 80, 160]}
ACELERACIONES = (100.0, 1000.0)
# Donde el brazo sin acelerar cabe (ver el encabezado).
GRUPOS_LIBRES = ("interiores", "suma_no_cabe")
ACELERADA = "V3a acelerada"
SIN_ACELERAR = "V3a sin acelerar"

# Si no hay seleccion escrita, las horas que la sonda del consenso ya midio
# (sec. 3 de consenso-report.md). No sustituyen a la muestra: son para que una
# noche no se pierda entera si la seleccion no corrio.
RESPALDO = {
    "interiores": [("E0", "2025-05-09 13:00"), ("K1", "2025-05-11 08:00"),
                   ("E4", "2025-05-07 07:00")],
    "topados": [("E0", "2025-05-10 10:00")],
    "mixto": [("E0", "2025-05-10 13:00"), ("E0", "2025-05-11 11:00")],
    "suma_no_cabe": [("E0", "2025-07-01 08:00")],
}


def horas_del_grupo(horas, grupo, cuantas=POR_GRUPO):
    """Las horas de ese grupo, en el orden de preferencia de los casos."""
    fuera = []
    for caso in CASOS:
        for h in horas.get(caso, {}).get(grupo, []):
            fuera.append((caso, h["fecha"], h))
            if len(fuera) >= cuantas:
                return fuera
    return fuera


def specs(horas):
    fuera = []
    for grupo in GRUPOS:
        elegidas = horas_del_grupo(horas, grupo)
        respaldo = not elegidas
        if respaldo:
            elegidas = [(c, f, None) for c, f in RESPALDO.get(grupo, [])]
        brazos = [(k, ACELERADA) for k in ACELERACIONES]
        if grupo in GRUPOS_LIBRES:
            brazos.append((1.0, SIN_ACELERAR))
        for caso, fecha, _info in elegidas:
            for k, familia in brazos:
                fuera.append(dict(
                    medicion=MEDICION, familia=familia,
                    caso=caso, fecha=fecha, grupo=grupo,
                    etq=f"V3a k{k:g}{' (respaldo)' if respaldo else ''}",
                    var=dict(mu_ent=MU, k_lento=k),
                    cortes=CORTES[k], tope=TOPE,
                    nivel="sigma", piso_juego="marginal"))
    return fuera
