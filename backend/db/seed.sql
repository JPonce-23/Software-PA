BEGIN;
SET LOCAL "app.current_user_id" = '1';

-- El usuario técnico se crea primero porque todos los registros operativos
-- disparan la auditoría forense.
INSERT INTO usuario (
    id_usuario, nombre, apellido_paterno, correo, contrasena_hash, rol
)
VALUES (
    1,
    'Admin',
    'Sistema',
    'admin@sistema.com',
    '$2b$12$o3hWnUn7TaaDouwlExb6z.wtr3bQafHhxk9dr0L2TG4AfKP.7ymum',
    'admin'
)
ON CONFLICT DO NOTHING;

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

SELECT setval(pg_get_serial_sequence('usuario', 'id_usuario'), (SELECT MAX(id_usuario) FROM usuario));
SELECT setval(pg_get_serial_sequence('proyecto', 'id_proyecto'), (SELECT MAX(id_proyecto) FROM proyecto));
SELECT setval(pg_get_serial_sequence('tramo', 'id_tramo'), (SELECT MAX(id_tramo) FROM tramo));
SELECT setval(pg_get_serial_sequence('nucleo_agrario', 'id_nucleo'), (SELECT MAX(id_nucleo) FROM nucleo_agrario));
SELECT setval(pg_get_serial_sequence('tramo_nucleo', 'id_tramo_nucleo'), (SELECT MAX(id_tramo_nucleo) FROM tramo_nucleo));

COMMIT;
