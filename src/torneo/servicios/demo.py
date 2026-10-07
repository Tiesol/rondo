"""Datos de demo inventados (T2.7), con la forma de 2023 (CONTEXTO 6.2 y 6.4).

Nunca datos reales: los nombres, CI y fechas los inventa faker con una semilla fija, así la
demo es siempre la misma. Los planteles se cargan en bloque (bulk_create), cumpliendo las
reglas por construcción, para que también ande rápido contra Neon. Para mostrar los avisos,
algunos jugadores son menores, otros no tienen CI y algunos equipos no tienen dorsales.
"""

import json
import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from faker import Faker

from dominio.config import CuerpoTecnico, cargar_config
from dominio.documentos import normalizar_documento
from torneo.models import CategoriaNivel, Club, Equipo, Jugador, Persona, Profe, Torneo
from torneo.servicios.clubes import cargar_clubes
from torneo.servicios.configuracion import cargar_configuracion

SEMILLA = 2026
DATOS = settings.RAIZ / "datos" / "demo" / "equipos.json"
COLORES = ["#c8102e", "#0d2440", "#1f5e9c", "#1b7a43", "#f2cf3a", "#6d2077", "#e87722", "#111111"]


class NoEsLaDemo(Exception):
    """La base tiene datos que no son de demo: no se toca nada."""


@dataclass
class _Plantel:
    equipo: Equipo
    tamanio: int
    con_dorsales: bool
    jugadores: list[tuple[Persona, bool]] = field(default_factory=list)  # (persona, compartida)
    profes: list[Persona] = field(default_factory=list)


def verificar_que_es_demo() -> None:
    if Equipo.objects.filter(categoria__torneo__es_demo=False).exists() or (
        Persona.objects.filter(
            Q(jugadores__equipo__categoria__torneo__es_demo=False)
            | Q(profes__equipo__categoria__torneo__es_demo=False)
        ).exists()
    ):
        raise NoEsLaDemo("La base tiene equipos o personas que no son de demo.")


class _Generador:
    def __init__(self, torneo: Torneo) -> None:
        self.torneo = torneo
        self.azar = random.Random(SEMILLA)
        self.faker = Faker("es_ES")
        self.faker.seed_instance(SEMILLA)
        self.numeros = iter(self.azar.sample(range(3_000_000, 9_999_999), 3000))
        self.cuerpo = CuerpoTecnico.model_validate(torneo.cuerpo_tecnico)

    def documento(self, adulto: bool) -> dict[str, str]:
        if not adulto and self.azar.random() < 0.03:
            return {"tipo_documento": "", "documento": "", "clave_documento": ""}
        numero = next(self.numeros)
        forma = self.azar.choice(["{}", "{} SC", "{}SC", "{} LP", "{}-1E", "E-{}"])
        documento = normalizar_documento(forma.format(numero))
        assert documento is not None
        return {
            "tipo_documento": documento.tipo,
            "documento": documento.texto,
            "clave_documento": documento.clave,
        }

    def persona(self, nacimiento: date | None, adulto: bool = False) -> Persona:
        return Persona(
            nombres=self.faker.first_name(),
            apellidos=f"{self.faker.last_name()} {self.faker.last_name()}",
            nacimiento=nacimiento,
            **self.documento(adulto),
        )

    def nacimiento(self, categoria: CategoriaNivel, menor_por: int = 0) -> date:
        anio = self.torneo.anio - categoria.edad
        anio += self.azar.randrange(categoria.anios_nacimiento) + menor_por
        return date(anio, self.azar.randint(1, 12), self.azar.randint(1, 28))

    def menor_por(self) -> int:
        """Casi todos de su año; algunos menores, y unos pocos con aviso (más de 2 años)."""
        sorteo = self.azar.random()
        return 3 if sorteo < 0.015 else 1 if sorteo < 0.07 else 0


def _equipos(torneo: Torneo, datos: dict[str, Any], azar: random.Random) -> dict[str, Equipo]:
    categorias = {f"{c.categoria}|{c.nivel}": c for c in torneo.categorias.all()}
    equipos: dict[str, Equipo] = {}
    for clave, nombres in datos["equipos"].items():
        for nombre in nombres:
            club = Club.buscar(nombre)
            assert club is not None, f"{nombre} no está en el catálogo de clubes"
            equipo = Equipo(
                club=club,
                categoria=categorias[clave],
                nombre=nombre,
                color_1=azar.choice(COLORES),
                color_2="#ffffff",
                pagado=azar.random() < 0.7,
            )
            equipos[f"{nombre}|{clave}"] = equipo
    Equipo.objects.bulk_create(equipos.values())
    return equipos


def _rehacer_borrando(torneo: Torneo) -> None:
    """Saca los equipos de demo, y las personas que solo estaban en ellos."""
    equipos = Equipo.objects.filter(categoria__torneo=torneo)
    personas = set(
        Persona.objects.filter(
            Q(jugadores__equipo__in=equipos) | Q(profes__equipo__in=equipos)
        ).values_list("pk", flat=True)
    )
    equipos.delete()
    Persona.objects.filter(pk__in=personas, jugadores__isnull=True, profes__isnull=True).delete()


@transaction.atomic
def generar_demo(datos: Path = DATOS) -> Torneo:
    verificar_que_es_demo()
    cargar_clubes(settings.CATALOGO_CLUBES)
    torneo = cargar_configuracion(cargar_config(settings.PLANTILLA_TORNEO))
    torneo.es_demo = True
    torneo.publico = True
    torneo.save(update_fields=["es_demo", "publico"])
    _rehacer_borrando(torneo)

    contenido = json.loads(datos.read_text())
    generador = _Generador(torneo)
    azar = generador.azar
    equipos = _equipos(torneo, contenido, azar)

    planteles: dict[str, _Plantel] = {}
    cortos = set(azar.sample(sorted(equipos), 3))
    for clave, equipo in equipos.items():
        categoria = equipo.categoria
        tamanio = azar.randint(categoria.min_jugadores, categoria.max_jugadores)
        if clave in cortos:
            tamanio = categoria.min_jugadores - azar.randint(1, 3)
        planteles[clave] = _Plantel(equipo, tamanio, con_dorsales=azar.random() > 0.25)

    # 6.4: jugadores en dos categorías de su club. Tienen la edad de la categoría menor.
    for grupo in contenido["jugadores_compartidos"]:
        claves = grupo["equipos"]
        menor = min((planteles[c].equipo.categoria for c in claves), key=lambda c: c.edad)
        for _ in range(grupo["veces"]):
            persona = generador.persona(generador.nacimiento(menor))
            for clave in claves:
                planteles[clave].jugadores.append((persona, True))

    # 6.4: profes que dirigen varios equipos.
    for grupo in contenido["profes_compartidos"]:
        for _ in range(grupo["veces"]):
            persona = generador.persona(None, adulto=True)
            for clave in grupo["equipos"]:
                planteles[clave].profes.append(persona)

    for plantel in planteles.values():
        categoria = plantel.equipo.categoria
        while len(plantel.jugadores) < plantel.tamanio:
            nacimiento = generador.nacimiento(categoria, generador.menor_por())
            plantel.jugadores.append((generador.persona(nacimiento), False))
        objetivo = max(len(plantel.profes), azar.randint(1, generador.cuerpo.max_por_equipo))
        while len(plantel.profes) < objetivo:
            plantel.profes.append(generador.persona(None, adulto=True))

    nuevas = {id(p): p for pl in planteles.values() for p, _ in pl.jugadores}
    nuevas |= {id(p): p for pl in planteles.values() for p in pl.profes}
    Persona.objects.bulk_create(nuevas.values())

    jugadores, profes = [], []
    for plantel in planteles.values():
        dorsales = azar.sample(range(1, 31), len(plantel.jugadores))
        for (persona, _), dorsal in zip(plantel.jugadores, dorsales, strict=True):
            jugadores.append(
                Jugador(
                    persona=persona,
                    equipo=plantel.equipo,
                    dorsal=dorsal if plantel.con_dorsales else None,
                    verificado=azar.random() < 0.5,
                )
            )
        for persona, rol in zip(plantel.profes, generador.cuerpo.roles, strict=False):
            profes.append(Profe(persona=persona, equipo=plantel.equipo, rol=rol))
    Jugador.objects.bulk_create(jugadores)
    Profe.objects.bulk_create(profes)
    return torneo
