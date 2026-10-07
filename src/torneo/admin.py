"""Admin de la configuración del torneo (T1.5). Solo para el organizador (superusuario)."""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from torneo.models import Cancha, CategoriaNivel, Franja, Organizador, Torneo

admin.site.site_header = "Rondo · configuración"
admin.site.site_title = "Rondo"
admin.site.index_title = "Configuración del torneo"


class CanchaEnLinea(admin.TabularInline):
    model = Cancha
    fields = ("codigo", "nombre", "padre")
    extra = 0


class FranjaEnLinea(admin.TabularInline):
    model = Franja
    fields = ("inicio", "fin", "tipo")
    extra = 0


@admin.register(Torneo)
class TorneoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "edicion", "anio", "inicio", "fin")
    inlines = (CanchaEnLinea, FranjaEnLinea)
    fieldsets = (
        (None, {"fields": ("nombre", "edicion", "anio", "inicio", "fin", "zona_horaria")}),
        ("Partidos", {"fields": ("descanso_min", "cambio_entre_partidos_min")}),
        (
            "Reglas",
            {
                "fields": ("cuerpo_tecnico", "reglas"),
                "description": (
                    "JSON validado: una clave mal escrita o un valor inválido se rechaza. "
                    "Cada regla corresponde a una pregunta P del reglamento (ver PROGRESO.md)."
                ),
            },
        ),
    )


@admin.register(CategoriaNivel)
class CategoriaNivelAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "modalidad",
        "min_jugadores",
        "max_jugadores",
        "min_por_tiempo",
        "minutos_turno",
    )
    list_filter = ("torneo", "nivel", "modalidad")
    filter_horizontal = ("canchas",)
    list_select_related = ("torneo",)

    @admin.display(description="turno (min)")
    def minutos_turno(self, obj: CategoriaNivel) -> int:
        return obj.minutos_turno


@admin.register(Organizador)
class OrganizadorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "color_primario")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not Organizador.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
