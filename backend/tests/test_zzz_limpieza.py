"""
test_zzz_limpieza.py — Limpieza de datos creados durante la sesión de tests.

Este archivo se ejecuta al final (por orden alfabético de pytest) y elimina
todos los recursos registrados en la pila de limpieza (LIFO) para respetar
las foreign keys.

Prefijo 'zzz' para garantizar que se ejecute después de todos los demás módulos.
"""


def test_limpieza_ordenada(client, admin_headers, cleanup):
    """Elimina todos los recursos creados en orden inverso (LIFO).
    Evita que queden datos basura en la BD tras la sesión de tests."""
    errores = []
    for endpoint, resource_id in cleanup.items:
        res = client.delete(
            f"{endpoint}/{resource_id}?motivo=Limpieza automatizada pytest",
            headers=admin_headers,
        )
        if res.status_code not in (200, 404):
            errores.append(f"{endpoint}/{resource_id} → {res.status_code}: {res.text}")

    assert len(errores) == 0, (
        f"Errores durante la limpieza:\n" + "\n".join(errores)
    )
