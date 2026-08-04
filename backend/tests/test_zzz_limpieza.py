"""
test_zzz_limpieza.py — Limpieza de datos creados durante la sesión de tests.

Este archivo se ejecuta al final (por orden alfabético de pytest) y elimina
todos los recursos registrados en la pila de limpieza (LIFO) para respetar
las foreign keys.

Prefijo 'zzz' para garantizar que se ejecute después de todos los demás módulos.
"""


def test_limpieza_ordenada(client, admin_headers, cleanup):
    """Elimina todos los recursos creados en orden inverso (LIFO).
    Reintenta dependencias temporalmente bloqueadas sin relajar las reglas de BD.
    Evita que queden datos basura en la BD tras la sesión de tests."""
    pendientes = list(cleanup.items)
    ultimos_errores = {}
    for _ in range(len(pendientes) + 1):
        siguientes = []
        hubo_progreso = False
        for endpoint, resource_id in pendientes:
            res = client.delete(
                f"{endpoint}/{resource_id}?motivo=Limpieza automatizada pytest",
                headers=admin_headers,
            )
            if res.status_code in (200, 404):
                hubo_progreso = True
            else:
                siguientes.append((endpoint, resource_id))
                ultimos_errores[(endpoint, resource_id)] = (
                    f"{endpoint}/{resource_id} → {res.status_code}: {res.text}"
                )
        pendientes = siguientes
        if not pendientes or not hubo_progreso:
            break

    errores = [ultimos_errores[item] for item in pendientes]

    assert len(errores) == 0, (
        f"Errores durante la limpieza:\n" + "\n".join(errores)
    )
