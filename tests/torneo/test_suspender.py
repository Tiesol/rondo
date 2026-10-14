"""T5.5: suspender un día y agregar un día entre semana. Datos inventados."""

from datetime import date
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client
from django.utils import timezone

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Corrida, Equipo, Franja, Partido, Torneo
from torneo.permisos import MESA, ORGANIZACION
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture
from torneo.servicios.programador import programar_torneo, verificar_torneo


@pytest.fixture(autouse=True)
def rapido(settings: Any) -> None:
    settings.PROGRAMADOR_SEGUNDOS = 10
    settings.PROGRAMADOR_TRABAJADORES = 4


@pytest.fixture
def torneo() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn: CategoriaNivel = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(4):
        club, _ = Club.objects.get_or_create(nombre=f"Club {i}")
        Equipo.objects.create(club=club, categoria=cn, nombre=f"Equipo {i}")
    generar_fixture(cn, semilla=1)
    programar_torneo(torneo)
    return torneo


def entrar(client: Client, grupo: str) -> Client:
    usuario = User.objects.create_user(grupo[:4], password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    client.force_login(usuario)
    return client


def dia_con_partidos() -> str:
    primero = Partido.objects.filter(inicio__isnull=False, fase="grupos").order_by("inicio").first()
    assert primero is not None and primero.inicio is not None
    return timezone.localtime(primero.inicio).date().isoformat()


@pytest.mark.django_db
def test_suspender_pide_confirmar_y_dice_que_va_a_pasar(client: Client, torneo: Torneo) -> None:
    dia = dia_con_partidos()
    org = entrar(client, ORGANIZACION)
    del_dia = Partido.objects.filter(inicio__isnull=False).count()
    respuesta = org.post(f"/calendario/{dia}/suspender/")  # B7: sin confirmar, no hace nada
    assert respuesta.status_code == 200
    assert "¿Estás seguro?" in respuesta.content.decode()
    assert Partido.objects.filter(inicio__isnull=False).count() == del_dia
    assert not torneo.franjas.filter(suspendida=True).exists()
    html = org.get(f"/calendario/{dia}/suspender/").content.decode()
    assert "Se suspenden los" in html or "Se suspende el partido del" in html
    assert 'value="2026-10-29"' in html  # B1: por defecto, el próximo jueves


@pytest.mark.django_db
def test_suspender_deja_pendientes_y_las_propuestas_los_ubican_el_jueves(
    client: Client, torneo: Torneo
) -> None:
    dia = dia_con_partidos()
    del_dia = [
        p.pk
        for p in Partido.objects.filter(inicio__isnull=False)
        if timezone.localtime(p.inicio).date().isoformat() == dia
    ]
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(f"/calendario/{dia}/suspender/", {"confirmado": "1"} | datos_jueves())
    assert set(Partido.objects.filter(pk__in=del_dia).values_list("estado", flat=True)) == {
        "pendiente"
    }
    assert all(
        f.suspendida
        for f in torneo.franjas.filter(tipo="regular")
        if timezone.localtime(f.inicio).date().isoformat() == dia
    )
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    assert respuesta["Location"] == f"/corridas/{corrida.pk}/propuestas/"
    assert corrida.resultado["propuestas"], "hay que poder ubicarlos en otro día"
    jueves = Franja.objects.get(tipo=Franja.Tipo.ENTRE_SEMANA)
    assert (
        timezone.localtime(jueves.inicio).weekday(),
        timezone.localtime(jueves.inicio).hour,
    ) == (3, 16)
    # B1: lo suspendido se ubica primero en ese jueves.
    mejor = corrida.resultado["propuestas"][0]
    en_el_jueves = [m for m in mejor if m["despues"][1].startswith("2026-10-29")]
    assert len(en_el_jueves) == len([m for m in mejor if m["antes"] is None])
    org.post(f"/corridas/{corrida.pk}/aplicar/0/", {"confirmado": "1"})
    assert verificar_torneo(torneo) == {}
    for partido in Partido.objects.filter(pk__in=del_dia):
        assert partido.inicio is not None
        assert timezone.localtime(partido.inicio).date().isoformat() != dia


def datos_jueves() -> dict[str, str]:
    return {"dia": "2026-10-29", "desde": "16:00", "hasta": "20:00"}


@pytest.mark.django_db
def test_b1_nunca_propone_nada_antes_de_ahora(
    client: Client, torneo: Torneo, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import datetime

    ahora = datetime(2026, 10, 25, 9, 0)  # el domingo 25, a las 9: el sábado ya pasó
    monkeypatch.setattr("torneo.servicios.programador.ahora_local", lambda: ahora)
    monkeypatch.setattr("torneo.servicios.reprogramar.ahora_local", lambda: ahora)
    org = entrar(client, ORGANIZACION)
    org.post("/calendario/2026-10-25/suspender/", {"confirmado": "1"} | datos_jueves())
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    for propuesta in corrida.resultado["propuestas"]:
        for m in propuesta:
            assert datetime.fromisoformat(m["despues"][1]) >= ahora


@pytest.mark.django_db
def test_b1_en_la_propuesta_se_ve_cuantos_publicados_se_mueven(
    client: Client, torneo: Torneo
) -> None:
    org = entrar(client, ORGANIZACION)
    org.post(f"/calendario/{dia_con_partidos()}/suspender/", {"confirmado": "1"} | datos_jueves())
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    html = org.get(f"/corridas/{corrida.pk}/propuestas/").content.decode()
    assert "ya publicado" in html  # "Mueve N … ya publicados" o "No mueve ningún … ya publicado"


@pytest.mark.django_db
def test_b2_reanudar_vuelve_cada_partido_a_su_lugar(client: Client, torneo: Torneo) -> None:
    dia = dia_con_partidos()
    antes = {
        p.pk: (p.cancha_id, p.inicio)
        for p in Partido.objects.filter(inicio__isnull=False)
        if timezone.localtime(p.inicio).date().isoformat() == dia
    }
    org = entrar(client, ORGANIZACION)
    org.post(f"/calendario/{dia}/suspender/", {"confirmado": "1"} | datos_jueves())
    assert Franja.objects.filter(tipo=Franja.Tipo.ENTRE_SEMANA).count() == 1
    # Sin confirmar, no se hace nada y dice qué pasa.
    respuesta = org.get(f"/calendario/{dia}/reanudar/")
    assert "Vuelven a su lugar" in respuesta.content.decode()
    assert not torneo.franjas.filter(suspendida=False, inicio__date=dia).exists()
    org.post(f"/calendario/{dia}/reanudar/", {"confirmado": "1"})
    for pk, lugar in antes.items():
        partido = Partido.objects.get(pk=pk)
        assert (partido.cancha_id, partido.inicio) == lugar
        assert partido.estado == "programado"
    assert not torneo.franjas.filter(suspendida=True).exists()
    assert not Franja.objects.filter(tipo=Franja.Tipo.ENTRE_SEMANA).exists()  # quedó vacío


@pytest.mark.django_db
def test_b2_los_ya_reubicados_quedan_donde_estan(client: Client, torneo: Torneo) -> None:
    dia = dia_con_partidos()
    org = entrar(client, ORGANIZACION)
    org.post(f"/calendario/{dia}/suspender/", {"confirmado": "1"} | datos_jueves())
    corrida = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    org.post(f"/corridas/{corrida.pk}/aplicar/0/", {"confirmado": "1"})
    ubicados = {p.pk: (p.cancha_id, p.inicio) for p in Partido.objects.filter(inicio__isnull=False)}
    html = org.get(f"/calendario/{dia}/reanudar/").content.decode()
    assert "Quedan donde están" in html
    org.post(f"/calendario/{dia}/reanudar/", {"confirmado": "1"})
    for pk, lugar in ubicados.items():
        partido = Partido.objects.get(pk=pk)
        assert (partido.cancha_id, partido.inicio) == lugar
    assert Franja.objects.filter(tipo=Franja.Tipo.ENTRE_SEMANA).exists()  # tiene partidos


@pytest.mark.django_db
def test_b3_un_partido_en_juego_no_sale_del_calendario(client: Client, torneo: Torneo) -> None:
    dia = dia_con_partidos()
    en_juego = Partido.objects.filter(inicio__isnull=False).order_by("inicio").first()
    assert en_juego is not None
    lugar = (en_juego.cancha_id, en_juego.inicio)
    en_juego.estado = Partido.Estado.EN_JUEGO
    en_juego.save()
    org = entrar(client, ORGANIZACION)
    html = org.get(f"/calendario/{dia}/suspender/").content.decode()
    assert "En juego" in html
    org.post(f"/calendario/{dia}/suspender/", {"confirmado": "1"} | datos_jueves())
    en_juego.refresh_from_db()
    assert (en_juego.cancha_id, en_juego.inicio, en_juego.estado) == (*lugar, "en_juego")
    html = org.get(f"/calendario/{dia}/").content.decode()
    assert "En juego cuando se suspendió" in html
    assert f"/partidos/{en_juego.pk}/ficha/" in html


@pytest.mark.django_db
def test_programar_no_usa_un_dia_suspendido(torneo: Torneo) -> None:
    dia = dia_con_partidos()
    for franja in torneo.franjas.all():
        if timezone.localtime(franja.inicio).date().isoformat() == dia:
            franja.suspendida = True
            franja.save()
    programar_torneo(torneo)
    assert not any(
        timezone.localtime(p.inicio).date().isoformat() == dia
        for p in Partido.objects.filter(inicio__isnull=False)
        if p.inicio
    )


@pytest.mark.django_db
def test_agregar_un_dia_entre_semana(client: Client, torneo: Torneo) -> None:
    org = entrar(client, ORGANIZACION)
    respuesta = org.post(
        "/calendario/agregar-dia/", {"dia": "2026-10-28", "desde": "17:00", "hasta": "20:00"}
    )
    assert respuesta["Location"] == "/calendario/2026-10-28/"
    franja = Franja.objects.get(tipo=Franja.Tipo.ENTRE_SEMANA)
    assert timezone.localtime(franja.inicio).hour == 17
    html = org.get("/calendario/2026-10-28/").content.decode()
    assert "Mié" in html


@pytest.mark.django_db
def test_la_mesa_no_suspende_ni_agrega_dias(client: Client, torneo: Torneo) -> None:
    mesa = entrar(client, MESA)
    assert mesa.post(f"/calendario/{dia_con_partidos()}/suspender/").status_code == 403
    assert mesa.post("/calendario/agregar-dia/", {}).status_code == 403


@pytest.mark.django_db
def test_agregar_dia_propone_el_jueves_siguiente(client: Client, torneo: Torneo) -> None:
    # Convocatoria 2026: las fechas suspendidas se reprograman el jueves.
    org = entrar(client, ORGANIZACION)
    sabado = org.get("/calendario/2026-10-31/")
    assert sabado.context["form_dia"].initial["dia"] == date(2026, 11, 5)
    domingo = org.get("/calendario/2026-11-01/")
    assert domingo.context["form_dia"].initial["dia"] == date(2026, 11, 5)


@pytest.mark.django_db
def test_a4_el_tiempo_agregado_guarda_sus_canchas_y_llega_al_programador(
    client: Client, torneo: Torneo
) -> None:
    from torneo.servicios.programador import partidos_del_torneo, problema_del_torneo

    c3 = torneo.canchas.get(codigo="C3")
    org = entrar(client, ORGANIZACION)
    org.post(
        "/calendario/agregar-dia/",
        {"dia": "2026-10-29", "desde": "16:00", "hasta": "20:00", "canchas": [c3.pk]},
    )
    franja = Franja.objects.get(tipo=Franja.Tipo.ENTRE_SEMANA)
    assert [c.codigo for c in franja.canchas.all()] == ["C3"]
    problema = problema_del_torneo(torneo, partidos_del_torneo(torneo))
    assert [(e.canchas) for e in problema.extras] == [frozenset({"C3"})]
    # Lo agregado no es horario normal: no está entre las franjas regulares.
    assert all(desde.day != 29 for desde, _ in problema.franjas)
    # Sin canchas elegidas, vale en todas.
    org.post("/calendario/agregar-dia/", {"dia": "2026-11-05", "desde": "16:00", "hasta": "20:00"})
    assert Franja.objects.exclude(pk=franja.pk).get(tipo="entre_semana").canchas.count() == 0


@pytest.mark.django_db
def test_las_fechas_de_los_formularios_van_en_iso_para_el_campo_date(
    client: Client, torneo: Torneo
) -> None:
    # Un <input type="date"> ignora "29/10/2026": el valor tiene que ir como 2026-10-29.
    org = entrar(client, ORGANIZACION)
    dia = dia_con_partidos()
    assert 'value="2026-10-29"' in org.get(f"/calendario/{dia}/suspender/").content.decode()
    assert 'value="2026-10-29"' in org.get(f"/calendario/{dia}/").content.decode()
    partido = Partido.objects.filter(inicio__isnull=False).first()
    assert partido is not None and partido.inicio is not None
    esperado = f'value="{timezone.localtime(partido.inicio).date().isoformat()}"'
    assert esperado in org.get(f"/partidos/{partido.pk}/mover/").content.decode()


@pytest.mark.django_db
def test_b6_recalcular_aflojando_reglas_queda_anotado_en_la_corrida(
    client: Client, torneo: Torneo
) -> None:
    org = entrar(client, ORGANIZACION)
    org.post(f"/calendario/{dia_con_partidos()}/suspender/", {"confirmado": "1"} | datos_jueves())
    primera = Corrida.objects.get(tipo=Corrida.Tipo.REPROGRAMAR)
    assert primera.parametros["relajar"] == {}
    respuesta = org.post(
        f"/corridas/{primera.pk}/recalcular/",
        {"turnos_libres": "0", "max_por_dia": "3", "minutos_extra": "30", "usar_mitades": "on"},
    )
    segunda = Corrida.objects.exclude(pk=primera.pk).get(tipo=Corrida.Tipo.REPROGRAMAR)
    assert respuesta["Location"] == f"/corridas/{segunda.pk}/propuestas/"
    assert segunda.parametros["relajar"] == {
        "turnos_libres": 0,
        "max_por_dia": 3,
        "minutos_extra": 30,
        "usar_mitades": True,
    }
    assert segunda.parametros["franja_extra"] == primera.parametros["franja_extra"]
    html = org.get(f"/corridas/{segunda.pk}/propuestas/").content.decode()
    assert "Reglas aflojadas solo esta vez" in html and "Usar mitades de cancha" in html
    # Las reglas del torneo no cambian.
    torneo.refresh_from_db()
    assert torneo.reglas["max_partidos_por_dia"] == 2


@pytest.mark.django_db
def test_b9_un_partido_puesto_a_mano_en_un_dia_sin_franja_tiene_su_pestana(
    client: Client, torneo: Torneo
) -> None:
    from datetime import datetime

    from torneo.servicios.reprogramar import mover_a_mano

    partido = Partido.objects.filter(inicio__isnull=False).first()
    assert partido is not None
    miercoles = timezone.make_aware(datetime(2026, 10, 28, 17, 0))
    mover_a_mano(partido, torneo.canchas.get(codigo="C2"), miercoles, confirmar=True)
    org = entrar(client, ORGANIZACION)
    html = org.get("/calendario/2026-10-24/").content.decode()
    assert "/calendario/2026-10-28/" in html
    assert "Mié" in org.get("/calendario/2026-10-28/").content.decode()
