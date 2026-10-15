"""T13.1: el escudo va por equipo del club (club + nombre), no por club (P68, P88 y P89).

Un club tiene cualquier cantidad de equipos, cada uno con su escudo. El mismo equipo juega en
varias categorías: el escudo se sube una vez y vale en todas. Imágenes y nombres inventados.
"""

import io

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client
from PIL import Image

from dominio.config import cargar_config
from torneo.models import CategoriaNivel, Club, Equipo, EquipoDeClub, Torneo
from torneo.permisos import ORGANIZACION
from torneo.presentacion import escudo
from torneo.servicios.clubes import NoSePuede
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.equipos import renombrar_equipo


def png(color: tuple[int, int, int] = (10, 40, 90)) -> SimpleUploadedFile:
    salida = io.BytesIO()
    Image.new("RGB", (300, 300), color).save(salida, "PNG")
    return SimpleUploadedFile("escudo.png", salida.getvalue(), content_type="image/png")


@pytest.fixture
def torneo() -> Torneo:
    return cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))


@pytest.fixture
def org(client: Client) -> Client:
    usuario = User.objects.create_user("org", password="x")
    usuario.groups.add(Group.objects.get(name=ORGANIZACION))
    client.force_login(usuario)
    return client


def _categoria(torneo: Torneo, categoria: str, nivel: str = "avanzado") -> CategoriaNivel:
    return torneo.categorias.get(categoria=categoria, nivel=nivel)


@pytest.mark.django_db
def test_crear_un_equipo_crea_o_reusa_su_equipo_del_club(torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    sub9 = Equipo.objects.create(club=club, categoria=_categoria(torneo, "Sub 9"), nombre="Norte")
    sub10 = Equipo.objects.create(club=club, categoria=_categoria(torneo, "Sub 10"), nombre="norte")
    assert sub9.equipo_de_club_id == sub10.equipo_de_club_id
    # El nombre es el del equipo del club, aunque se escriba con otras mayúsculas.
    assert sub10.nombre == "Norte"
    assert EquipoDeClub.objects.filter(club=club).count() == 1


@pytest.mark.django_db
def test_el_mismo_equipo_no_se_inscribe_dos_veces_en_una_categoria(torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    cn = _categoria(torneo, "Sub 9")
    Equipo.objects.create(club=club, categoria=cn, nombre="Norte")
    with pytest.raises(IntegrityError), transaction.atomic():
        Equipo.objects.create(club=club, categoria=cn, nombre="NORTE")


@pytest.mark.django_db
def test_dos_equipos_del_mismo_club_con_escudos_distintos(org: Client, torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    cn = _categoria(torneo, "Sub 9")
    azul = Equipo.objects.create(club=club, categoria=cn, nombre="Norte Azul")
    blanco = Equipo.objects.create(club=club, categoria=cn, nombre="Norte Blanco")
    org.post(f"/equipos-del-club/{azul.equipo_de_club_id}/escudo/", {"escudo": png()})
    org.post(f"/equipos-del-club/{blanco.equipo_de_club_id}/escudo/", {"escudo": png((200, 0, 0))})
    azul.refresh_from_db()
    blanco.refresh_from_db()
    url_azul, url_blanco = escudo(azul)["url"], escudo(blanco)["url"]
    assert url_azul and url_blanco and url_azul != url_blanco
    assert f"/imagen/escudo/{azul.equipo_de_club_id}/" in url_azul


@pytest.mark.django_db
def test_un_equipo_en_tres_categorias_tiene_un_solo_escudo(org: Client, torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    equipos = [
        Equipo.objects.create(club=club, categoria=_categoria(torneo, c), nombre="Norte")
        for c in ("Sub 8", "Sub 9", "Sub 10")
    ]
    respuesta = org.post(
        f"/equipos-del-club/{equipos[0].equipo_de_club_id}/escudo/",
        {"escudo": png(), "equipo": equipos[0].pk},
    )
    assert respuesta.status_code == 302
    urls = {escudo(e)["url"] for e in equipos}
    assert len(urls) == 1 and urls != {""}
    imagen = org.get(urls.pop())
    assert imagen.status_code == 200 and imagen["Content-Type"] == "image/webp"


@pytest.mark.django_db
def test_renombrar_cambia_el_nombre_en_todas_sus_categorias(torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    for c in ("Sub 8", "Sub 9"):
        Equipo.objects.create(club=club, categoria=_categoria(torneo, c), nombre="Norte")
    del_club = EquipoDeClub.objects.get(club=club)
    renombrar_equipo(del_club, "  Norte Azul ")
    del_club.refresh_from_db()
    assert del_club.nombre == "Norte Azul"
    # Nunca quedan distintos: el nombre de cada categoría es copia del equipo del club.
    assert set(Equipo.objects.values_list("nombre", flat=True)) == {"Norte Azul"}
    for equipo in Equipo.objects.select_related("equipo_de_club"):
        assert equipo.nombre == equipo.equipo_de_club.nombre
        assert equipo.club_id == equipo.equipo_de_club.club_id


@pytest.mark.django_db
def test_renombrar_no_deja_dos_equipos_del_club_con_el_mismo_nombre(torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    cn = _categoria(torneo, "Sub 9")
    Equipo.objects.create(club=club, categoria=cn, nombre="Norte Azul")
    blanco = Equipo.objects.create(club=club, categoria=cn, nombre="Norte Blanco")
    with pytest.raises(NoSePuede):
        renombrar_equipo(blanco.equipo_de_club, "norte azul")
    with pytest.raises(NoSePuede):
        renombrar_equipo(blanco.equipo_de_club, "   ")


@pytest.mark.django_db
def test_guardar_un_equipo_con_otro_nombre_falla(torneo: Torneo) -> None:
    """El nombre se cambia solo con renombrar_equipo: guardar una copia distinta es un error."""
    club = Club.objects.create(nombre="Norte FC")
    equipo = Equipo.objects.create(club=club, categoria=_categoria(torneo, "Sub 9"), nombre="N")
    equipo.nombre = "Otro"
    with pytest.raises(ValueError, match="renombrar_equipo"):
        equipo.save()


@pytest.mark.django_db
def test_reemplazar_un_escudo_compartido_no_borra_el_de_otro_equipo(
    org: Client, torneo: Torneo
) -> None:
    """Después de la migración, los equipos de un club comparten el archivo del escudo viejo."""
    club = Club.objects.create(nombre="Norte FC")
    cn = _categoria(torneo, "Sub 9")
    azul = Equipo.objects.create(club=club, categoria=cn, nombre="Norte Azul")
    blanco = Equipo.objects.create(club=club, categoria=cn, nombre="Norte Blanco")
    org.post(f"/equipos-del-club/{azul.equipo_de_club_id}/escudo/", {"escudo": png()})
    compartido = EquipoDeClub.objects.get(pk=azul.equipo_de_club_id).escudo.name
    EquipoDeClub.objects.filter(pk=blanco.equipo_de_club_id).update(escudo=compartido)
    org.post(f"/equipos-del-club/{azul.equipo_de_club_id}/escudo/", {"escudo": png((0, 90, 0))})
    org.post(f"/equipos-del-club/{azul.equipo_de_club_id}/escudo/", {"quitar": "1"})
    del_blanco = EquipoDeClub.objects.get(pk=blanco.equipo_de_club_id)
    assert compartido and del_blanco.escudo.name == compartido
    assert del_blanco.escudo.storage.exists(compartido)


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_la_migracion_pasa_el_escudo_del_club_a_sus_equipos() -> None:
    antes = [("torneo", "0033_planilla_flexible")]
    despues = [("torneo", "0036_quitar_escudo_del_club")]
    ejecutor = MigrationExecutor(connection)
    ejecutor.migrate(antes)
    viejas = ejecutor.loader.project_state(antes).apps
    ClubViejo = viejas.get_model("torneo", "Club")
    TorneoViejo = viejas.get_model("torneo", "Torneo")
    CategoriaVieja = viejas.get_model("torneo", "CategoriaNivel")
    EquipoViejo = viejas.get_model("torneo", "Equipo")
    torneo = TorneoViejo.objects.create(
        nombre="Prueba", edicion=1, anio=2026, inicio="2026-10-24", fin="2026-11-15"
    )
    sub8, sub9 = (
        CategoriaVieja.objects.create(
            torneo=torneo,
            categoria=f"Sub {edad}",
            edad=edad,
            nivel="inicial",
            modalidad="F7",
            min_jugadores=7,
            max_jugadores=12,
            min_por_tiempo=15,
        )
        for edad in (8, 9)
    )
    norte = ClubViejo.objects.create(nombre="Norte FC", escudo="escudos/norte.webp")
    sur = ClubViejo.objects.create(nombre="Sur FC")
    EquipoViejo.objects.create(club=norte, categoria=sub8, nombre="Norte")
    EquipoViejo.objects.create(club=norte, categoria=sub9, nombre="Norte")
    EquipoViejo.objects.create(club=norte, categoria=sub9, nombre="Norte B")
    EquipoViejo.objects.create(club=sur, categoria=sub9, nombre="Sur")

    ejecutor = MigrationExecutor(connection)
    ejecutor.loader.build_graph()
    ejecutor.migrate(despues)
    nuevas = ejecutor.loader.project_state(despues).apps
    DelClub = nuevas.get_model("torneo", "EquipoDeClub")
    EquipoNuevo = nuevas.get_model("torneo", "Equipo")
    escudos = dict(DelClub.objects.values_list("nombre", "escudo"))
    assert escudos == {"Norte": "escudos/norte.webp", "Norte B": "escudos/norte.webp", "Sur": ""}
    assert all(
        e.nombre == e.equipo_de_club.nombre and e.club_id == e.equipo_de_club.club_id
        for e in EquipoNuevo.objects.select_related("equipo_de_club")
    )
    assert (
        EquipoNuevo.objects.filter(nombre="Norte").values("equipo_de_club").distinct().count() == 1
    )
    ejecutor = MigrationExecutor(connection)
    ejecutor.loader.build_graph()
    ejecutor.migrate(ejecutor.loader.graph.leaf_nodes())


# ---------- T13.2: dónde se sube y el pendiente ----------


@pytest.mark.django_db
def test_inicio_muestra_los_equipos_sin_escudo_y_su_lista(org: Client, torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    azul = Equipo.objects.create(club=club, categoria=_categoria(torneo, "Sub 9"), nombre="Azul")
    Equipo.objects.create(club=club, categoria=_categoria(torneo, "Sub 10"), nombre="Azul")
    Equipo.objects.create(club=club, categoria=_categoria(torneo, "Sub 9"), nombre="Blanco")
    inicio = org.get("/").content.decode()
    assert "2 equipos sin escudo" in inicio
    url = f"/torneos/{torneo.pk}/sin-escudo/"
    assert url in inicio
    lista = org.get(url).content.decode()
    assert "Azul" in lista and "Blanco" in lista
    assert f"/equipos-del-club/{azul.equipo_de_club_id}/escudo/" in lista
    org.post(f"/equipos-del-club/{azul.equipo_de_club_id}/escudo/", {"escudo": png()})
    assert "1 equipo sin escudo" in org.get("/").content.decode()


@pytest.mark.django_db
def test_con_todos_los_escudos_no_hay_pendiente(org: Client, torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    azul = Equipo.objects.create(club=club, categoria=_categoria(torneo, "Sub 9"), nombre="Azul")
    EquipoDeClub.objects.filter(pk=azul.equipo_de_club_id).update(escudo="escudos/azul.webp")
    assert "sin escudo" not in org.get("/").content.decode()


@pytest.mark.django_db
def test_desde_la_lista_se_sube_y_se_vuelve_a_la_lista(org: Client, torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    azul = Equipo.objects.create(club=club, categoria=_categoria(torneo, "Sub 9"), nombre="Azul")
    respuesta = org.post(
        f"/equipos-del-club/{azul.equipo_de_club_id}/escudo/",
        {"escudo": png(), "volver": "sin-escudo", "torneo": torneo.pk},
    )
    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"/torneos/{torneo.pk}/sin-escudo/"


@pytest.mark.django_db
def test_la_pantalla_del_club_lista_sus_equipos_y_los_renombra(org: Client, torneo: Torneo) -> None:
    club = Club.objects.create(nombre="Norte FC")
    azul = Equipo.objects.create(club=club, categoria=_categoria(torneo, "Sub 9"), nombre="Azul")
    html = org.get(f"/clubes/{club.pk}/").content.decode()
    assert "Azul" in html and "Sin escudo" in html
    assert f"/equipos-del-club/{azul.equipo_de_club_id}/escudo/" in html
    org.post(f"/equipos-del-club/{azul.equipo_de_club_id}/nombre/", {"nombre": "Celeste"})
    azul.refresh_from_db()
    assert azul.nombre == "Celeste"


@pytest.mark.django_db
def test_unir_clubes_mueve_los_equipos_y_sus_escudos(torneo: Torneo) -> None:
    from torneo.servicios.clubes import unir_clubes

    bueno = Club.objects.create(nombre="Tigres FC")
    repetido = Club.objects.create(nombre="Club Tigres")
    rojo = Equipo.objects.create(
        club=repetido, categoria=_categoria(torneo, "Sub 9"), nombre="Rojo"
    )
    EquipoDeClub.objects.filter(pk=rojo.equipo_de_club_id).update(escudo="escudos/rojo.webp")
    # El mismo equipo cargado en los dos clubes, en categorías distintas: se une en uno.
    Equipo.objects.create(club=bueno, categoria=_categoria(torneo, "Sub 9"), nombre="Tigres")
    tigres = Equipo.objects.create(
        club=repetido, categoria=_categoria(torneo, "Sub 10"), nombre="tigres"
    )
    EquipoDeClub.objects.filter(pk=tigres.equipo_de_club_id).update(escudo="escudos/tigres.webp")
    unidos = unir_clubes(repetido, bueno)
    assert unidos == ["Tigres"]
    escudos = dict(EquipoDeClub.objects.values_list("nombre", "escudo"))
    assert escudos == {"Rojo": "escudos/rojo.webp", "Tigres": "escudos/tigres.webp"}
    assert set(EquipoDeClub.objects.values_list("club", flat=True)) == {bueno.pk}
    for equipo in Equipo.objects.select_related("equipo_de_club"):
        assert equipo.club_id == bueno.pk
        assert equipo.nombre == equipo.equipo_de_club.nombre
