"""B7 (fase 12): un solo "¿Estás seguro?" que dice qué va a pasar."""

import pytest
from django.test import RequestFactory

from torneo.views.confirmar import confirmado, pedir_confirmacion


@pytest.mark.django_db
def test_la_pantalla_dice_que_va_a_pasar_y_guarda_los_datos() -> None:
    pedido = RequestFactory().post("/algo/", {"dia": "2026-10-31", "canchas": ["1", "2"]})
    pedido.htmx = False  # type: ignore[attr-defined]
    respuesta = pedir_confirmacion(
        pedido,
        mensaje="Se suspenden los 26 partidos del sábado 31/10.",
        detalle=["3 en juego"],
        boton="Suspender",
    )
    html = respuesta.content.decode()
    assert "Se suspenden los 26 partidos" in html and "Suspender" in html
    assert 'name="dia" value="2026-10-31"' in html
    assert html.count('name="canchas"') == 2
    assert 'name="confirmado" value="1"' in html
    assert not confirmado(pedido)
    assert confirmado(RequestFactory().post("/algo/", {"confirmado": "1"}))
