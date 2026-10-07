"""Admin de la configuración del torneo (T1.5). Solo para el organizador (superusuario)."""

from typing import Any

from django import forms
from django.contrib import admin
from django.http import HttpRequest

from torneo.models import Cancha, CategoriaNivel, Club, Franja, Organizador, Torneo

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


class FormularioClub(forms.ModelForm):
    """Los alias se escriben uno por línea, en lugar de una lista JSON."""

    alias_texto = forms.CharField(
        label="Alias",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Otras formas de escribir el nombre del club, una por línea.",
    )

    class Meta:
        model = Club
        fields = ("nombre",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["alias_texto"].initial = "\n".join(self.instance.alias)

    def save(self, commit: bool = True) -> Club:
        lineas = self.cleaned_data["alias_texto"].splitlines()
        self.instance.alias = [linea.strip() for linea in lineas if linea.strip()]
        club: Club = super().save(commit)
        return club


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    form = FormularioClub
    list_display = ("nombre", "alias")
    search_fields = ("nombre",)
