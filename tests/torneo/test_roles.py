"""TU.2: roles Organización y Mesa de control, y el aviso donde no hay permiso."""

from io import StringIO

import pytest
from django.contrib.auth.models import AnonymousUser, Group, User
from django.core.management import CommandError, call_command
from django.http import HttpRequest, HttpResponse
from django.test import Client, RequestFactory

from torneo.permisos import MESA, ORGANIZACION, PERMISOS_POR_ROL, nombre_del_rol, requiere

CLAVE = "Cancha-Sintetica-2026!"


def usuario_con_rol(nombre: str, grupo: str) -> User:
    usuario = User.objects.create_user(nombre, password="x")
    usuario.groups.add(Group.objects.get(name=grupo))
    return usuario


@requiere("torneo.programar_partidos", "programar")
def vista_de_programar(request: HttpRequest) -> HttpResponse:
    return HttpResponse("programando")


@requiere("torneo.inscribir_equipos", "cargar equipos")
def vista_de_equipos(request: HttpRequest) -> HttpResponse:
    return HttpResponse("equipos")


def pedir(vista: object, usuario: User) -> HttpResponse:
    request = RequestFactory().get("/")
    request.user = usuario
    return vista(request)  # type: ignore[operator, no-any-return]


@pytest.mark.django_db
def test_los_grupos_existen_despues_de_migrar() -> None:
    assert Group.objects.filter(name=ORGANIZACION).exists()
    assert Group.objects.filter(name=MESA).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("permiso", PERMISOS_POR_ROL[ORGANIZACION])
def test_la_organizacion_puede_todo(permiso: str) -> None:
    assert usuario_con_rol("org", ORGANIZACION).has_perm(f"torneo.{permiso}")


@pytest.mark.django_db
def test_la_mesa_carga_equipos_y_verifica_pero_no_configura_ni_programa() -> None:
    mesa = usuario_con_rol("mesa", MESA)
    assert mesa.has_perm("torneo.inscribir_equipos")
    assert mesa.has_perm("torneo.verificar_jugadores")
    assert not mesa.has_perm("torneo.configurar_torneo")
    assert not mesa.has_perm("torneo.programar_partidos")


@pytest.mark.django_db
def test_la_mesa_ve_el_aviso_del_rol_con_un_403() -> None:
    respuesta = pedir(vista_de_programar, usuario_con_rol("mesa", MESA))
    assert respuesta.status_code == 403
    html = respuesta.content.decode()
    assert "Solo la organización puede programar" in html


@pytest.mark.django_db
def test_la_organizacion_entra_y_la_mesa_tambien_donde_tiene_permiso() -> None:
    assert pedir(vista_de_programar, usuario_con_rol("org", ORGANIZACION)).status_code == 200
    assert pedir(vista_de_equipos, usuario_con_rol("mesa", MESA)).status_code == 200


@pytest.mark.django_db
def test_el_superusuario_es_de_la_organizacion() -> None:
    sebastian = User.objects.create_superuser("sebastian", password="x")
    assert nombre_del_rol(sebastian) == ORGANIZACION
    assert pedir(vista_de_programar, sebastian).status_code == 200


@pytest.mark.django_db
def test_sin_grupo_no_hay_rol() -> None:
    assert nombre_del_rol(User.objects.create_user("nadie", password="x")) == ""
    assert nombre_del_rol(AnonymousUser()) == ""


@pytest.mark.django_db
def test_crear_usuario_de_mesa_sin_staff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RONDO_CLAVE_USUARIO", CLAVE)
    call_command("crear_usuario", "mesa1", "--rol", "mesa", stdout=StringIO())
    usuario = User.objects.get(username="mesa1")
    assert not usuario.is_staff
    assert nombre_del_rol(usuario) == MESA


@pytest.mark.django_db
def test_crear_usuario_de_la_organizacion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RONDO_CLAVE_USUARIO", CLAVE)
    call_command("crear_usuario", "org1", "--rol", "organizacion", stdout=StringIO())
    assert nombre_del_rol(User.objects.get(username="org1")) == ORGANIZACION


@pytest.mark.django_db
def test_crear_usuario_rechaza_un_rol_desconocido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RONDO_CLAVE_USUARIO", CLAVE)
    with pytest.raises(CommandError):
        call_command("crear_usuario", "x", "--rol", "arbitro", stdout=StringIO())


@pytest.mark.django_db
def test_la_pantalla_mas_muestra_las_personas_y_su_rol(client: Client) -> None:
    usuario_con_rol("ana", ORGANIZACION)
    client.force_login(usuario_con_rol("mesa1", MESA))
    respuesta = client.get("/mas/")
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "ana" in html
    assert "mesa1" in html
    assert ORGANIZACION in html
    assert "Mesa" in html


@pytest.mark.django_db
def test_la_barra_muestra_el_rol_actual(client: Client) -> None:
    client.force_login(usuario_con_rol("mesa1", MESA))
    assert 'class="rol-actual"' in client.get("/").content.decode()


@pytest.mark.django_db
def test_el_403_generico_tambien_explica_y_ofrece_volver(client: Client) -> None:
    client.force_login(usuario_con_rol("mesa1", MESA))
    respuesta = client.get("/diagnostico/componentes/")
    assert respuesta.status_code == 403
    html = respuesta.content.decode()
    assert "No tienes permiso para ver esta página" in html
    assert 'aria-label="Principal"' in html
