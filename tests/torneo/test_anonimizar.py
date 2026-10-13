"""T6.4: retención de datos (P49): un torneo terminado se queda sin datos personales."""

import io
from datetime import date, timedelta
from typing import Any

import pytest
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import CommandError, call_command
from PIL import Image

from dominio.config import cargar_config
from torneo.models import Club, Equipo, Jugador, Persona, Profe, Torneo
from torneo.servicios.configuracion import cargar_configuracion
from torneo.servicios.fixture import generar_fixture


@pytest.fixture
def terminado() -> Torneo:
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    cn = torneo.categorias.get(categoria="Sub 9", nivel="avanzado")
    for i in range(3):
        equipo = Equipo.objects.create(
            club=Club.objects.create(nombre=f"Club {i}"), categoria=cn, nombre=f"Equipo {i}"
        )
        for j in range(3):
            persona = Persona.objects.create(
                nombres="Nombre",
                apellidos=f"Inventado {i}{j}",
                tipo_documento="ci",
                documento=f"{7000000 + 10 * i + j}",
                clave_documento=f"{7000000 + 10 * i + j}",
                nacimiento=date(2017, 1, 1 + j),
            )
            Jugador.objects.create(persona=persona, equipo=equipo, dorsal=j + 1)
        profe = Persona.objects.create(nombres="Profe", apellidos=f"Inventado {i}")
        Profe.objects.create(persona=profe, equipo=equipo, rol="entrenador")
    generar_fixture(cn, semilla=1)
    hoy = date.today()
    Torneo.objects.filter(pk=torneo.pk).update(
        inicio=hoy - timedelta(days=60), fin=hoy - timedelta(days=30)
    )
    torneo.refresh_from_db()
    return torneo


def anonimizar(torneo: Torneo, *extra: str) -> str:
    salida = io.StringIO()
    call_command("anonimizar_torneo", str(torneo.pk), *extra, stdout=salida)
    return salida.getvalue()


@pytest.mark.django_db
def test_no_queda_ningun_dato_personal_del_torneo(terminado: Torneo) -> None:
    partidos_antes = terminado.categorias.get(categoria="Sub 9", nivel="avanzado").partidos.count()
    anonimizar(terminado, "--confirmo")
    for persona in Persona.objects.all():
        assert persona.nombres in ("Jugador", "Profe")
        assert persona.documento == persona.clave_documento == persona.tipo_documento == ""
        assert persona.nacimiento is None
        assert persona.anio_nacimiento is None
        assert "Inventado" not in persona.apellidos
    dorsales = sorted(d for d in Jugador.objects.values_list("dorsal", flat=True) if d)
    assert dorsales == [1, 1, 1, 2, 2, 2, 3, 3, 3]
    assert Equipo.objects.count() == 3
    cn = terminado.categorias.get(categoria="Sub 9", nivel="avanzado")
    assert cn.partidos.count() == partidos_antes


@pytest.mark.django_db
def test_quien_esta_en_otro_torneo_no_se_toca(terminado: Torneo) -> None:
    otro = Torneo.objects.create(
        nombre="Otro", edicion=6, anio=2027, inicio=date(2027, 10, 1), fin=date(2027, 11, 1)
    )
    cn = otro.categorias.create(
        categoria="Sub 10",
        edad=10,
        nivel="unico",
        modalidad="F7",
        min_jugadores=1,
        max_jugadores=20,
        min_por_tiempo=20,
    )
    persona = Persona.objects.get(apellidos="Inventado 00")
    equipo = Equipo.objects.create(club=Club.objects.first(), categoria=cn, nombre="Otro")  # type: ignore[misc]
    Jugador.objects.create(persona=persona, equipo=equipo)
    anonimizar(terminado, "--confirmo")
    persona.refresh_from_db()
    assert persona.apellidos == "Inventado 00"
    assert persona.documento


@pytest.mark.django_db
def test_sin_la_bandera_no_hace_nada(terminado: Torneo) -> None:
    assert "--confirmo" in anonimizar(terminado)
    assert Persona.objects.filter(apellidos__startswith="Inventado").count() == 12


@pytest.mark.django_db
def test_un_torneo_en_curso_no_se_anonimiza(terminado: Torneo) -> None:
    Torneo.objects.filter(pk=terminado.pk).update(fin=date.today() + timedelta(days=5))
    with pytest.raises(CommandError, match="todavía no terminó"):
        anonimizar(terminado, "--confirmo")
    assert Persona.objects.filter(apellidos__startswith="Inventado").count() == 12


def _foto() -> ContentFile[bytes]:
    salida = io.BytesIO()
    Image.new("RGB", (20, 20), (1, 2, 3)).save(salida, "WEBP")
    return ContentFile(salida.getvalue(), name="foto.webp")


@pytest.mark.django_db
def test_t9_1_tambien_borra_las_fotos_del_almacenamiento(
    terminado: Torneo, django_capture_on_commit_callbacks: Any
) -> None:
    # P49 y P76: las fotos son datos personales de menores; no quedan en el bucket.
    archivos = []
    for persona in Persona.objects.all():
        persona.foto.save("foto.webp", _foto())
        persona.foto_autorizada = True
        persona.save()
        archivos.append(persona.foto.name or "")
    with django_capture_on_commit_callbacks(execute=True):
        anonimizar(terminado, "--confirmo")
    for persona in Persona.objects.all():
        assert not persona.foto and not persona.foto_autorizada
    almacenamiento = Persona._meta.get_field("foto").storage
    assert not any(almacenamiento.exists(nombre) for nombre in archivos)


@pytest.mark.django_db
def test_t9_1_la_foto_de_quien_sigue_en_otro_torneo_queda(terminado: Torneo) -> None:
    otro = Torneo.objects.create(
        nombre="Otro", edicion=6, anio=2027, inicio=date.today(), fin=date.today()
    )
    persona = Jugador.objects.filter(equipo__categoria__torneo=terminado).first().persona  # type: ignore[union-attr]
    persona.foto.save("foto.webp", _foto())
    cn = otro.categorias.create(
        categoria="Sub 9",
        nivel="avanzado",
        edad=9,
        modalidad="F7",
        min_jugadores=1,
        max_jugadores=20,
        min_por_tiempo=20,
    )
    equipo = Equipo.objects.create(
        club=Club.objects.create(nombre="Otro club"), categoria=cn, nombre="Otro"
    )
    Jugador.objects.create(persona=persona, equipo=equipo, dorsal=9)
    anonimizar(terminado, "--confirmo")
    persona.refresh_from_db()
    assert persona.foto and persona.foto.storage.exists(persona.foto.name or "")
