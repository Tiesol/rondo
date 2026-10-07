"""Alta de un equipo: club del catálogo, categoría-nivel, nombre visible y colores (T2.5)."""

from typing import TYPE_CHECKING, Any

from django import forms

from torneo.models import Club, Equipo, Torneo

if TYPE_CHECKING:
    _Base = forms.ModelForm[Equipo]
else:
    _Base = forms.ModelForm


class FormularioEquipo(_Base):
    class Meta:
        model = Equipo
        fields = ["club", "categoria", "nombre", "color_1", "color_2"]
        labels = {
            "categoria": "Categoría",
            "color_1": "Camiseta",
            "color_2": "Detalle",
        }
        help_texts = {"nombre": "Vacío: el nombre del club. Sirve para un segundo equipo."}
        widgets = {
            "color_1": forms.TextInput(attrs={"type": "color"}),
            "color_2": forms.TextInput(attrs={"type": "color"}),
        }

    def __init__(self, *args: Any, torneo: Torneo, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        club = self.fields["club"]
        categoria = self.fields["categoria"]
        assert isinstance(club, forms.ModelChoiceField)
        assert isinstance(categoria, forms.ModelChoiceField)
        club.queryset = Club.objects.all()
        club.empty_label = "Elige el club"
        categoria.queryset = torneo.categorias.all()
        categoria.empty_label = None
        self.fields["nombre"].required = False

    def clean_nombre(self) -> str:
        nombre: str = self.cleaned_data.get("nombre", "").strip()
        club = self.cleaned_data.get("club")
        return nombre or (club.nombre if club else "")
