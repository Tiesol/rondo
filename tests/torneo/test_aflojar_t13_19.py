"""T13.19: "Aflojar reglas solo esta vez", solo en Propuestas, plegado, con el valor actual de
cada regla, y "Usar mitades de cancha" solo cuando sirve (F6 y F7)."""

from dominio.config import Reglas
from torneo.forms.reprogramar import CamposAflojar


def test_cada_campo_muestra_el_valor_actual_y_no_viene_vacio() -> None:
    reglas = Reglas()
    form = CamposAflojar(reglas=reglas, modalidades={"F7"})
    assert form.initial["turnos_libres"] == reglas.turnos_libres_mismo_dia
    assert form.initial["max_por_dia"] == reglas.max_partidos_por_dia
    assert f"hoy: {reglas.max_partidos_por_dia}" in form.fields["max_por_dia"].help_text
    assert "hoy:" in form.fields["turnos_libres"].help_text
    assert "hoy:" in form.fields["minutos_extra"].help_text


def test_dejar_los_valores_de_hoy_no_afloja_nada() -> None:
    reglas = Reglas()
    datos = {
        "turnos_libres": str(reglas.turnos_libres_mismo_dia),
        "max_por_dia": str(reglas.max_partidos_por_dia),
        "minutos_extra": "0",
    }
    form = CamposAflojar(datos, reglas=reglas, modalidades={"F7"})
    assert form.is_valid()
    assert form.relajar().vacio


def test_mitades_no_aparece_si_chocan_solo_partidos_de_f11() -> None:
    assert "usar_mitades" not in CamposAflojar(reglas=Reglas(), modalidades={"F11"}).fields


def test_mitades_con_aviso_si_se_mezclan_modalidades() -> None:
    form = CamposAflojar(reglas=Reglas(), modalidades={"F7", "F11"})
    assert "Solo para F6 y F7" in form.fields["usar_mitades"].help_text
