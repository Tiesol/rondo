"""T11.11: el atraso estimado de los partidos que siguen en una cancha."""

from datetime import datetime, timedelta

from dominio.hoy import EnCancha, atrasos, sin_iniciar

DIA = datetime(2026, 10, 24)


def en(hora: str, **cambios: object) -> EnCancha:
    h, m = map(int, hora.split(":"))
    base = {
        "id": hora,
        "programado": DIA.replace(hour=h, minute=m),
        "minutos_partido": 45,
        "minutos_turno": 50,
    }
    return EnCancha(**(base | cambios))  # type: ignore[arg-type]


def test_un_partido_que_empezo_tarde_atrasa_a_los_siguientes() -> None:
    empezado = en("10:00", inicio_real=DIA.replace(hour=10, minute=15))
    ahora = DIA.replace(hour=10, minute=30)
    resultado = atrasos([empezado, en("10:50"), en("11:40")], ahora)
    assert resultado == {"10:50": 15, "11:40": 15}


def test_si_va_a_horario_no_hay_atraso() -> None:
    empezado = en("10:00", inicio_real=DIA.replace(hour=10))
    assert atrasos([empezado, en("10:50")], DIA.replace(hour=10, minute=20)) == {}


def test_un_partido_sin_empezar_pasada_su_hora_atrasa_desde_ahora() -> None:
    ahora = DIA.replace(hour=10, minute=20)
    assert atrasos([en("10:00"), en("10:50")], ahora) == {"10:00": 20, "10:50": 20}


def test_con_el_segundo_tiempo_empezado_cuenta_su_final_esperado() -> None:
    # Empezó a tiempo pero el descanso fue largo: el 2.º tiempo empezó 10:35 y dura 20.
    jugando = en(
        "10:00",
        inicio_real=DIA.replace(hour=10),
        fin_esperado=DIA.replace(hour=10, minute=55),
    )
    assert atrasos([jugando, en("10:50")], DIA.replace(hour=10, minute=40)) == {"10:50": 10}


def test_lo_terminado_libera_la_cancha() -> None:
    hecho = en("10:00", inicio_real=DIA.replace(hour=10), fin_real=DIA.replace(hour=10, minute=40))
    assert atrasos([hecho, en("10:50")], DIA.replace(hour=10, minute=41)) == {}


def test_sin_iniciar_pasada_media_hora() -> None:
    partido = en("10:00")
    assert not sin_iniciar(partido, DIA.replace(hour=10, minute=29))
    assert sin_iniciar(partido, DIA.replace(hour=10, minute=31))
    assert not sin_iniciar(en("10:00", inicio_real=DIA), DIA + timedelta(hours=2))
