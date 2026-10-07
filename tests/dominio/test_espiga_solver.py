"""T0.6: el modelo sintético con la forma del problema real encuentra un calendario válido."""

from itertools import combinations

from dominio.programador.espiga import RECURSOS, Division, generar_instancia, resolver


def test_una_instancia_chica_queda_programada_sin_choques() -> None:
    instancia = generar_instancia(
        [Division("mitades", 4), Division("F7", 5), Division("F8", 4), Division("F11", 4)],
        findes=2,
        pares_de_profes=4,
        semilla=7,
    )

    resultado = resolver(instancia, segundos=3, workers=1)

    assert resultado.estado in {"OPTIMAL", "FEASIBLE"}
    por_partido = {p.id: p for p in instancia.partidos}
    asignado = {a.partido: a for a in resultado.asignaciones}
    assert set(asignado) == set(por_partido)

    def tramo(pid: int, factor: int = 1) -> tuple[int, int]:
        inicio = asignado[pid].inicio
        return inicio, inicio + por_partido[pid].turno * factor

    def se_pisan(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    for a, b in combinations(por_partido, 2):
        mismos_recursos = RECURSOS[asignado[a].cancha] & RECURSOS[asignado[b].cancha]
        if mismos_recursos:
            assert not se_pisan(tramo(a), tramo(b)), ("cancha", a, b)
        if set(por_partido[a].equipos) & set(por_partido[b].equipos):
            # Mismo equipo: un turno libre en medio (P17).
            assert not se_pisan(tramo(a, 2), tramo(b, 2)), ("equipo", a, b)

    for equipo_x, equipo_y in instancia.pares_de_profes:
        de_x = [p.id for p in instancia.partidos if equipo_x in p.equipos]
        de_y = [p.id for p in instancia.partidos if equipo_y in p.equipos]
        for a in de_x:
            for b in de_y:
                if a != b:
                    assert not se_pisan(tramo(a), tramo(b)), ("profe", a, b)

    for p in instancia.partidos:
        assert asignado[p.id].cancha in p.canchas
        inicio, fin = tramo(p.id)
        assert any(f_ini <= inicio and fin <= f_fin for f_ini, f_fin in instancia.franjas)
