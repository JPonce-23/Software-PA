BEGIN;

DO $$
DECLARE
    v_usuario_admin INTEGER;
BEGIN
    SELECT id_usuario
      INTO v_usuario_admin
      FROM usuario
     WHERE activo IS TRUE
       AND rol = 'admin'
     ORDER BY id_usuario
     LIMIT 1;

    IF v_usuario_admin IS NULL THEN
        RAISE EXCEPTION 'seed.sql requiere crear primero un usuario administrador activo con scripts/create_admin.py';
    END IF;

    PERFORM set_config('app.current_user_id', v_usuario_admin::TEXT, TRUE);
END $$;

INSERT INTO entidad_federativa (id_entidad, clave_inegi, nombre)
VALUES (4, '04', 'Campeche')
ON CONFLICT DO NOTHING;

INSERT INTO municipio (id_municipio, id_entidad, clave_inegi, nombre)
VALUES (4001, 4, '001', 'Calakmul')
ON CONFLICT DO NOTHING;

INSERT INTO proyecto (id_proyecto, clave_proyecto, nombre_proyecto)
VALUES (1, 'TM', 'Tren Maya')
ON CONFLICT DO NOTHING;

INSERT INTO tramo (id_tramo, id_proyecto, clave_tramo, nombre_tramo)
VALUES (1, 1, 'TM-T7', 'Tren Maya Tramo 7')
ON CONFLICT DO NOTHING;

INSERT INTO nucleo_agrario (id_nucleo, id_municipio, nombre_nucleo, tipo_nucleo)
VALUES (1, 4001, 'Ejido Plan de San Luis', 'ejido')
ON CONFLICT DO NOTHING;

INSERT INTO tramo_nucleo (
    id_tramo_nucleo, id_tramo, id_nucleo, consecutivo, numero_tramo
)
VALUES (1, 1, 1, 1, '7.1')
ON CONFLICT DO NOTHING;

SELECT setval(pg_get_serial_sequence('proyecto', 'id_proyecto'), (SELECT MAX(id_proyecto) FROM proyecto));
SELECT setval(pg_get_serial_sequence('tramo', 'id_tramo'), (SELECT MAX(id_tramo) FROM tramo));
SELECT setval(pg_get_serial_sequence('nucleo_agrario', 'id_nucleo'), (SELECT MAX(id_nucleo) FROM nucleo_agrario));
SELECT setval(pg_get_serial_sequence('tramo_nucleo', 'id_tramo_nucleo'), (SELECT MAX(id_tramo_nucleo) FROM tramo_nucleo));

COMMIT;
