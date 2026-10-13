"""T7.8: pegar la lista de jugadores en la ficha del equipo. Datos inventados."""

import logging
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Persona, Torneo
from torneo.permisos import MESA
from torneo.servicios.configuracion import cargar_configuracion


@pytest.fixture
def river9() -> Equipo:
    torneo: Torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")  # nacidos en 2017, 12 a 14
    club = Club.objects.create(nombre="River Plate")
    return Equipo.objects.create(club=club, categoria=cn, nombre="River Plate")


@pytest.fixture
def mesa(client: Client) -> Client:
    usuario = User.objects.create_user("mesa", password="x")
    usuario.groups.add(Group.objects.get(name=MESA))
    client.force_login(usuario)
    return client


def url(equipo: Equipo) -> str:
    return f"/equipos/{equipo.pk}/jugadores/pegar/"


def lista(filas: int, *, con_errores: tuple[int, ...] = ()) -> str:
    """Una lista inventada con encabezado; las filas de `con_errores` traen una fecha imposible."""
    lineas = ["Nº\tNOMBRES\tAPELLIDOS\tFECHA DE NACIMIENTO\tCI\tDORSAL"]
    for i in range(1, filas + 1):
        fecha = "31/02/2017" if i in con_errores else f"{i:02d}/03/2017"
        lineas.append(f"{i}\tNombre{i}\tInventado Prueba\t{fecha}\t{4000000 + i}\t{i}")
    return "\n".join(lineas)


def columnas_propuestas(respuesta: Any) -> dict[str, str]:
    analisis = respuesta.context["analisis"]
    return {f"col{i}": c for i, c in enumerate(analisis.columnas)}


def pegar_y_revisar(cliente: Client, equipo: Equipo, texto: str) -> Any:
    paso1 = cliente.post(url(equipo), {"paso": "columnas", "texto": texto})
    assert paso1.status_code == 200
    datos = {"paso": "revisar", "texto": texto} | columnas_propuestas(paso1)
    return cliente.post(url(equipo), datos)


def filas_del_formulario(respuesta: Any) -> dict[str, str]:
    """Lo que el navegador manda de vuelta desde la vista previa (todas las filas)."""
    filas = respuesta.context["filas"]
    datos = {"n": str(len(filas))}
    for i, fila in enumerate(filas):
        datos[f"f{i}-numero"] = str(fila.numero)
        for campo, valor in fila.campos.items():
            datos[f"f{i}-{campo}"] = valor
    return datos


@pytest.mark.django_db
def test_la_ficha_ofrece_pegar_la_lista(mesa: Client, river9: Equipo) -> None:
    html = mesa.get(f"/equipos/{river9.pk}/plantel/").content.decode()
    assert url(river9) in html


@pytest.mark.django_db
def test_propone_las_columnas_y_muestra_ejemplos(mesa: Client, river9: Equipo) -> None:
    respuesta = mesa.post(url(river9), {"paso": "columnas", "texto": lista(8)})
    analisis = respuesta.context["analisis"]
    assert analisis.columnas == [
        "ignorar",
        "nombres",
        "apellidos",
        "nacimiento",
        "documento",
        "dorsal",
    ]
    nombres = respuesta.context["selectores"][1]
    assert nombres[2] == "NOMBRES" and nombres[3] == ["Nombre1", "Nombre2", "Nombre3"]


@pytest.mark.django_db
def test_vista_previa_no_guarda_nada(mesa: Client, river9: Equipo) -> None:
    respuesta = pegar_y_revisar(mesa, river9, lista(3))
    assert [f.guardada for f in respuesta.context["filas"]] == [True, True, True]
    assert not Jugador.objects.exists() and not Persona.objects.exists()


@pytest.mark.django_db
def test_pegar_20_con_2_errores_guarda_18_y_deja_las_2_para_corregir(
    mesa: Client, river9: Equipo
) -> None:
    river9.categoria.max_jugadores = 22
    river9.categoria.save()
    vista = pegar_y_revisar(mesa, river9, lista(20, con_errores=(4, 9)))
    con_error = [f.numero for f in vista.context["filas"] if f.errores]
    assert con_error == [4, 9]

    guardado = mesa.post(url(river9), filas_del_formulario(vista) | {"paso": "guardar"})
    assert Jugador.objects.filter(equipo=river9).count() == 18
    quedan = guardado.context["filas"]
    assert [f.numero for f in quedan] == [4, 9]
    assert quedan[0].campos["nacimiento"] == "31/02/2017"  # como vino, para corregirla

    corregido = filas_del_formulario(guardado) | {"paso": "guardar"}
    corregido["f0-nacimiento"] = corregido["f1-nacimiento"] = "2017"
    final = mesa.post(url(river9), corregido)
    assert final.status_code == 302
    assert final["Location"] == f"/equipos/{river9.pk}/plantel/"
    assert Jugador.objects.filter(equipo=river9).count() == 20


@pytest.mark.django_db
def test_lo_que_depende_de_la_lista_entera_se_ve_en_la_vista_previa(
    mesa: Client, river9: Equipo
) -> None:
    # Sub 9: 14 como máximo. La fila 2 repite el dorsal 1 y no entra; la 16.ª sería la 15.ª.
    texto = lista(16).replace("\t2\n", "\t1\n")
    filas = pegar_y_revisar(mesa, river9, texto).context["filas"]
    assert any(h.regla == "INS-09" for h in filas[1].errores)
    assert not filas[14].errores
    assert any(h.regla == "INS-03" for h in filas[15].errores)
    # "Faltan N para el mínimo" no se repite en cada fila: lo muestra la ficha.
    assert not any(h.regla == "INS-03" for h in filas[0].avisos)


@pytest.mark.django_db
def test_lista_en_mm_dd_avisa_y_la_corrige(mesa: Client, river9: Equipo) -> None:
    texto = "Juan\tPérez Inventado\t03/14/2017\nAna\tRoca Inventada\t03/15/2017"
    respuesta = mesa.post(url(river9), {"paso": "columnas", "texto": texto})
    assert "mes/día/año" in respuesta.content.decode()
    vista = pegar_y_revisar(mesa, river9, texto)
    assert vista.context["filas"][0].campos["nacimiento"] == "14/03/2017"


@pytest.mark.django_db
def test_mas_de_60_filas_se_rechaza(mesa: Client, river9: Equipo) -> None:
    respuesta = mesa.post(url(river9), {"paso": "columnas", "texto": lista(61)})
    assert "60" in respuesta.content.decode()
    assert "analisis" not in respuesta.context or respuesta.context["analisis"] is None


@pytest.mark.django_db
def test_sin_rol_no_se_pega(client: Client, river9: Equipo) -> None:
    client.force_login(User.objects.create_user("nadie", password="x"))
    assert client.post(url(river9), {"paso": "columnas", "texto": lista(2)}).status_code == 403


@pytest.mark.django_db
def test_nada_pegado_va_al_log_ni_a_la_sesion(
    mesa: Client, river9: Equipo, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    vista = pegar_y_revisar(mesa, river9, lista(2))
    mesa.post(url(river9), filas_del_formulario(vista) | {"paso": "guardar"})
    assert "Inventado" not in caplog.text and "4000001" not in caplog.text
    assert "Inventado" not in str(dict(mesa.session))
    assert vista.wsgi_request.sensitive_post_parameters == "__ALL__"
