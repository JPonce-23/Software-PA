BEGIN;
SET LOCAL "app.current_user_id" = 1;

INSERT INTO entidad_federativa (id_entidad, clave_inegi, nombre) VALUES (4, '04', 'Campeche') ON CONFLICT DO NOTHING;
INSERT INTO municipio (id_municipio, id_entidad, clave_inegi, nombre) VALUES (4001, 4, '001', 'Calakmul') ON CONFLICT DO NOTHING;

INSERT INTO tramo (id_tramo, clave_tramo, nombre_tramo) VALUES (1, 'TM-T7', 'Tren Maya Tramo 7') ON CONFLICT DO NOTHING;
INSERT INTO frente (id_frente, id_tramo, clave_frente, nombre_frente) VALUES (1, 1, 'F7-A', 'Frente 7A') ON CONFLICT DO NOTHING;
INSERT INTO nucleo_agrario (id_nucleo, id_municipio, nombre_nucleo, tipo_nucleo) VALUES (1, 4001, 'Ejido Plan de San Luis', 'ejido') ON CONFLICT DO NOTHING;
INSERT INTO tramo_nucleo (id_tramo_nucleo, id_tramo, id_frente, id_nucleo, consecutivo, numero_tramo) VALUES (1, 1, 1, 1, 1, '7.1') ON CONFLICT DO NOTHING;

INSERT INTO usuario (id_usuario, nombre, apellido_paterno, correo, contrasena_hash, rol)
VALUES (1, 'Admin', 'Sistema', 'admin@sistema.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'admin') ON CONFLICT DO NOTHING;

COMMIT;
