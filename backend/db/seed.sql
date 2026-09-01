-- Dominio demo objetivo para 031-033.
-- Ejecutar mediante scripts/seed_objective_demo.py; no contiene usuarios ni secretos.
BEGIN;

SELECT pg_advisory_xact_lock(20260825, 100);

DO $seed$
DECLARE
    v_admin INTEGER;
    v_seed_time TIMESTAMPTZ := TIMESTAMPTZ '2025-08-25 12:00:00-06';
    v_mun_colon INTEGER;
    v_mun_pedro INTEGER;
    v_mun_marques INTEGER;
    v_mun_tula INTEGER;
    v_project_main INTEGER;
    v_project_empty INTEGER;
    v_n1 INTEGER; v_n2 INTEGER; v_n3 INTEGER; v_n4 INTEGER; v_n5 INTEGER;
    v_pn1 INTEGER; v_pn2 INTEGER; v_pn3 INTEGER; v_pn4 INTEGER; v_pn5 INTEGER;
    v_person_rep1 INTEGER; v_person_rep2 INTEGER;
    v_person_172 INTEGER; v_person_170 INTEGER; v_person_173 INTEGER; v_person_169 INTEGER;
    v_orv1 INTEGER; v_orv2 INTEGER; v_orv4 INTEGER;
    v_padron1 INTEGER; v_padron2 INTEGER; v_padron4 INTEGER;
    v_parcel172 INTEGER; v_parcel170 INTEGER; v_parcel173 INTEGER; v_parcel169 INTEGER;
    v_ca1 INTEGER; v_ca2 INTEGER; v_ca3 INTEGER; v_ca4 INTEGER; v_ca5 INTEGER; v_ca6 INTEGER;
    v_ia172 INTEGER; v_ia170 INTEGER; v_ia173 INTEGER; v_ia169 INTEGER;
    v_assembly1 INTEGER; v_assembly4 INTEGER; v_retiro4 INTEGER;
    v_cop_collective INTEGER; v_modified INTEGER; v_additional INTEGER; v_works INTEGER;
    v_permute INTEGER; v_cop_172 INTEGER; v_cop_170 INTEGER; v_expand INTEGER; v_remnant INTEGER;
    v_fifo_collective INTEGER; v_fifo_individual INTEGER;
    v_indemnity INTEGER; v_payment1 INTEGER; v_payment2 INTEGER;
    v_document1 INTEGER; v_document2 INTEGER; v_document3 INTEGER;
BEGIN
    IF current_setting('app.environment', TRUE) IS NULL
       OR lower(current_setting('app.environment', TRUE)) NOT IN ('development', 'test')
       OR current_database() !~* '(test|prueba|dev|local)' THEN
        RAISE EXCEPTION 'seed objetivo bloqueado: sólo development/test en una base identificada como local';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '033') THEN
        RAISE EXCEPTION 'seed objetivo requiere schema_migrations 033';
    END IF;
    IF (SELECT COUNT(*) FROM entidad_federativa WHERE activo) <> 32
       OR (SELECT COUNT(*) FROM municipio WHERE activo) <> 2478 THEN
        RAISE EXCEPTION 'seed objetivo requiere catálogo territorial 32/2478';
    END IF;
    IF EXISTS (SELECT 1 FROM proyecto)
       OR EXISTS (SELECT 1 FROM nucleo_agrario)
       OR EXISTS (SELECT 1 FROM persona)
       OR EXISTS (SELECT 1 FROM proyecto_nucleo)
       OR EXISTS (SELECT 1 FROM afectacion)
       OR EXISTS (SELECT 1 FROM convenio) THEN
        RAISE EXCEPTION 'seed objetivo exige dominio funcional vacío; no se mezcla con un estado parcial';
    END IF;

    SELECT id_usuario INTO v_admin FROM usuario WHERE activo AND rol = 'admin' ORDER BY id_usuario LIMIT 1;
    IF v_admin IS NULL THEN
        RAISE EXCEPTION 'seed objetivo requiere un administrador creado por scripts/create_admin.py';
    END IF;
    PERFORM set_config('app.current_user_id', v_admin::TEXT, TRUE);

    SELECT m.id_municipio INTO v_mun_colon FROM municipio m JOIN entidad_federativa e USING (id_entidad) WHERE e.clave_inegi = '22' AND m.clave_inegi = '22005' AND e.activo AND m.activo;
    SELECT m.id_municipio INTO v_mun_pedro FROM municipio m JOIN entidad_federativa e USING (id_entidad) WHERE e.clave_inegi = '22' AND m.clave_inegi = '22012' AND e.activo AND m.activo;
    SELECT m.id_municipio INTO v_mun_marques FROM municipio m JOIN entidad_federativa e USING (id_entidad) WHERE e.clave_inegi = '22' AND m.clave_inegi = '22011' AND e.activo AND m.activo;
    SELECT m.id_municipio INTO v_mun_tula FROM municipio m JOIN entidad_federativa e USING (id_entidad) WHERE e.clave_inegi = '13' AND m.clave_inegi = '13076' AND e.activo AND m.activo;
    IF v_mun_colon IS NULL OR v_mun_pedro IS NULL OR v_mun_marques IS NULL OR v_mun_tula IS NULL THEN
        RAISE EXCEPTION 'No se resolvieron por clave INEGI los municipios del dominio demo';
    END IF;

    INSERT INTO proyecto (clave_proyecto, nombre_proyecto, descripcion, fecha_inicio, creado_en, creado_por, observaciones)
    VALUES ('MEX-QRO', 'MÉXICO-QUERÉTARO', 'Dominio demo basado en fuentes locales, con casos QA explícitos.', DATE '2025-01-01', v_seed_time, v_admin, 'SEED OBJETIVO 2026-08-25') RETURNING id_proyecto INTO v_project_main;
    INSERT INTO proyecto (clave_proyecto, nombre_proyecto, descripcion, fecha_inicio, creado_en, creado_por, observaciones)
    VALUES ('QRO-IRA', 'QUERÉTARO-IRAPUATO', 'Proyecto demo para validar estados vacíos sin totales inventados.', DATE '2025-01-01', v_seed_time, v_admin, 'SEED OBJETIVO; sin ProyectoNucleo deliberadamente') RETURNING id_proyecto INTO v_project_empty;
    INSERT INTO trazo_proyecto (id_proyecto, version, geometria_linea, fuente, fecha_fuente, fecha_vigencia_inicio, creado_en, creado_por, observaciones)
    VALUES (v_project_main, 1, ST_GeomFromText('MULTILINESTRING((-100.3000 20.3000,-99.9000 20.7000))', 4326), 'SINTETICO_QA_NO_OFICIAL', DATE '2025-08-25', DATE '2025-08-25', v_seed_time, v_admin, 'Trazo sintético QA para validar el mapa por proyecto');

    INSERT INTO nucleo_agrario (id_municipio, nombre_nucleo, tipo_nucleo, fuente_datos, id_nucleo_fuente, alcance_identidad_fuente, creado_en, creado_por, observaciones)
    VALUES (v_mun_colon, 'SAN ILDEFONSO', 'ejido', 'Excel local M-Q', '220095', 'local', v_seed_time, v_admin, 'Caso fuente; municipio Colón, Querétaro') RETURNING id_nucleo INTO v_n1;
    INSERT INTO nucleo_agrario (id_municipio, nombre_nucleo, tipo_nucleo, fuente_datos, id_nucleo_fuente, alcance_identidad_fuente, creado_en, creado_por, observaciones)
    VALUES (v_mun_pedro, 'AHORCADO', 'ejido', 'Excel local M-Q', '220228', 'local', v_seed_time, v_admin, 'Caso fuente de parcelas P-172/P-170/P-173/P-169') RETURNING id_nucleo INTO v_n2;
    INSERT INTO nucleo_agrario (id_municipio, nombre_nucleo, tipo_nucleo, fuente_datos, id_nucleo_fuente, alcance_identidad_fuente, creado_en, creado_por, observaciones)
    VALUES (v_mun_marques, 'AGUA AZUL', 'ejido', 'Excel local M-Q', '220193', 'local', v_seed_time, v_admin, 'Caso fuente') RETURNING id_nucleo INTO v_n3;
    INSERT INTO nucleo_agrario (id_municipio, nombre_nucleo, tipo_nucleo, fuente_datos, id_nucleo_fuente, alcance_identidad_fuente, creado_en, creado_por, observaciones)
    VALUES (v_mun_tula, 'PUEBLO NUEVO DE JASSO', 'ejido', 'Excel local M-Q', '130992', 'local', v_seed_time, v_admin, 'Caso fuente de permuta') RETURNING id_nucleo INTO v_n4;
    INSERT INTO nucleo_agrario (id_municipio, nombre_nucleo, tipo_nucleo, comunidad_indigena, geometria_poligono, fuente_geometria, fecha_fuente_geometria, fuente_datos, alcance_identidad_fuente, creado_en, creado_por, observaciones)
    VALUES (v_mun_marques, 'COMUNIDAD QA MODELO OBJETIVO', 'comunidad', TRUE, ST_GeomFromText('MULTIPOLYGON(((-100.2200 20.5200,-100.2000 20.5200,-100.2000 20.5400,-100.2200 20.5400,-100.2200 20.5200)))', 4326), 'SINTETICA_QA_NO_RAN', DATE '2025-08-25', 'SINTETICO_QA', 'qa', v_seed_time, v_admin, 'CASO SINTÉTICO QA; no representa un núcleo oficial') RETURNING id_nucleo INTO v_n5;

    INSERT INTO proyecto_nucleo (id_proyecto, id_nucleo, residencia, responsable_nombre, contacto, creado_en, creado_por, observaciones)
    VALUES (v_project_main, v_n1, 'QUERÉTARO', 'Ing. José Luis Rico Mosqueda', '4423711439', v_seed_time, v_admin, 'Fuente INFORME M-Q fila 8') RETURNING id_proyecto_nucleo INTO v_pn1;
    INSERT INTO proyecto_nucleo (id_proyecto, id_nucleo, residencia, responsable_nombre, contacto, creado_en, creado_por, observaciones)
    VALUES (v_project_main, v_n2, 'QUERÉTARO', 'Lic. Lizzeth Aylin Velazquez Laparra', '9616039686', v_seed_time, v_admin, 'Fuente INFORME M-Q fila 10') RETURNING id_proyecto_nucleo INTO v_pn2;
    INSERT INTO proyecto_nucleo (id_proyecto, id_nucleo, residencia, responsable_nombre, contacto, creado_en, creado_por, observaciones)
    VALUES (v_project_main, v_n3, 'QUERÉTARO', 'Lic. Gloria Alegria Espinoza', '7121922842', v_seed_time, v_admin, 'Fuente INFORME M-Q fila 14') RETURNING id_proyecto_nucleo INTO v_pn3;
    INSERT INTO proyecto_nucleo (id_proyecto, id_nucleo, residencia, responsable_nombre, contacto, creado_en, creado_por, observaciones)
    VALUES (v_project_main, v_n4, 'TULA', 'Julieta Pérez Vargas', '7732230671', v_seed_time, v_admin, 'Fuente INFORME M-Q fila 70') RETURNING id_proyecto_nucleo INTO v_pn4;
    INSERT INTO proyecto_nucleo (id_proyecto, id_nucleo, residencia, responsable_nombre, contacto, creado_en, creado_por, observaciones)
    VALUES (v_project_main, v_n5, 'QA', 'Responsable sintético QA', NULL, v_seed_time, v_admin, 'CASO SINTÉTICO QA') RETURNING id_proyecto_nucleo INTO v_pn5;

    INSERT INTO proyecto_nucleo_referencia (id_proyecto_nucleo, tipo_referencia, valor, es_principal, creado_en, creado_por) VALUES
      (v_pn1, 'consecutivo', '2', TRUE, v_seed_time, v_admin),
      (v_pn1, 'consecutivo', '2-A', FALSE, v_seed_time, v_admin),
      (v_pn1, 'clave_tramo', '1', TRUE, v_seed_time, v_admin),
      (v_pn2, 'consecutivo', '3', TRUE, v_seed_time, v_admin),
      (v_pn3, 'consecutivo', '8', TRUE, v_seed_time, v_admin),
      (v_pn4, 'consecutivo', '47', TRUE, v_seed_time, v_admin),
      (v_pn5, 'otro', 'QA-COMUNIDAD-001', TRUE, v_seed_time, v_admin);

    INSERT INTO persona (nombre, datos_identidad_incompletos, origen_registro, creado_en, creado_por, observaciones)
    VALUES ('Representante QA San Ildefonso', TRUE, 'qa', v_seed_time, v_admin, 'Persona sintética para probar integrante ORV') RETURNING id_persona INTO v_person_rep1;
    INSERT INTO persona (nombre, datos_identidad_incompletos, origen_registro, creado_en, creado_por, observaciones)
    VALUES ('Representante QA Pueblo Nuevo de Jasso', TRUE, 'qa', v_seed_time, v_admin, 'Persona sintética para probar integrante ORV') RETURNING id_persona INTO v_person_rep2;
    INSERT INTO persona (nombre, datos_identidad_incompletos, origen_registro, creado_en, creado_por) VALUES ('BENJAMIN PACHECO CRUZ', TRUE, 'excel', v_seed_time, v_admin) RETURNING id_persona INTO v_person_172;
    INSERT INTO persona (nombre, datos_identidad_incompletos, origen_registro, creado_en, creado_por) VALUES ('MARCELO RESENDIZ PÉREZ', TRUE, 'excel', v_seed_time, v_admin) RETURNING id_persona INTO v_person_170;
    INSERT INTO persona (nombre, datos_identidad_incompletos, origen_registro, creado_en, creado_por) VALUES ('IGNACIO ALVAREZ GONZALEZ', TRUE, 'excel', v_seed_time, v_admin) RETURNING id_persona INTO v_person_173;
    INSERT INTO persona (nombre, datos_identidad_incompletos, origen_registro, creado_en, creado_por) VALUES ('J. CLEOTILDE BENITO CALLEJAS', TRUE, 'excel', v_seed_time, v_admin) RETURNING id_persona INTO v_person_169;

    INSERT INTO orv (id_nucleo, numero_orv, inicio_vigencia, fin_vigencia, estatus_fuente, acta_eleccion_inscrita_ran, fecha_inscripcion_acta_ran, creado_en, creado_por, observaciones)
    VALUES (v_n1, 'ORV-SI-2025', DATE '2025-11-10', DATE '2027-07-05', 'SI', TRUE, DATE '2025-11-10', v_seed_time, v_admin, 'Fechas verificadas en hoja ORV') RETURNING id_orv INTO v_orv1;
    INSERT INTO orv (id_nucleo, numero_orv, inicio_vigencia, fin_vigencia, estatus_fuente, acta_eleccion_inscrita_ran, creado_en, creado_por, observaciones)
    VALUES (v_n2, 'ORV-AH-2025', DATE '2025-11-10', NULL, 'NO', FALSE, v_seed_time, v_admin, 'Caso fuente sin inscripción RAN') RETURNING id_orv INTO v_orv2;
    INSERT INTO orv (id_nucleo, numero_orv, inicio_vigencia, fin_vigencia, estatus_fuente, acta_eleccion_inscrita_ran, fecha_inscripcion_acta_ran, creado_en, creado_por, observaciones)
    VALUES (v_n4, 'ORV-PNJ-2025', DATE '2025-11-05', DATE '2028-08-10', 'SI', TRUE, DATE '2025-11-05', v_seed_time, v_admin, 'Fechas verificadas en hoja ORV') RETURNING id_orv INTO v_orv4;
    INSERT INTO orv_integrante (id_orv, id_persona, cargo, fecha_inicio, creado_en, creado_por, observaciones) VALUES
      (v_orv1, v_person_rep1, 'Presidencia QA', DATE '2025-11-10', v_seed_time, v_admin, 'Cargo sintético QA'),
      (v_orv4, v_person_rep2, 'Secretaría QA', DATE '2025-11-05', v_seed_time, v_admin, 'Cargo sintético QA');

    INSERT INTO padron_historial (id_nucleo, fecha_padron, numero_ejidatarios_comuneros, creado_en, creado_por, observaciones) VALUES (v_n1, DATE '2025-11-10', 59, v_seed_time, v_admin, 'Hoja ORV fila 7') RETURNING id_padron INTO v_padron1;
    INSERT INTO padron_historial (id_nucleo, fecha_padron, numero_ejidatarios_comuneros, creado_en, creado_por, observaciones) VALUES (v_n2, DATE '2025-11-10', 201, v_seed_time, v_admin, 'Hoja ORV fila 8') RETURNING id_padron INTO v_padron2;
    INSERT INTO padron_historial (id_nucleo, fecha_padron, numero_ejidatarios_comuneros, creado_en, creado_por, observaciones) VALUES (v_n4, DATE '2025-11-05', 117, v_seed_time, v_admin, 'Hoja ORV fila 42') RETURNING id_padron INTO v_padron4;

    INSERT INTO actividad_campo (id_proyecto_nucleo, tipo_actividad, contexto_actividad, fecha_programada, fecha_realizada, responsable, resultado, creado_en, creado_por, observaciones) VALUES
      (v_pn1, 'sensibilizacion', 'general', DATE '2025-03-28', DATE '2025-04-04', 'Equipo PA', 'Realizada', v_seed_time, v_admin, 'Caso demo con programación y realización'),
      (v_pn1, 'caminamiento', 'general', DATE '2025-04-10', DATE '2025-04-12', 'Equipo técnico', 'Realizado', v_seed_time, v_admin, 'Caso demo'),
      (v_pn2, 'sensibilizacion', 'general', DATE '2025-03-28', NULL, 'Equipo PA', NULL, v_seed_time, v_admin, 'Programada sin realización'),
      (v_pn3, 'caminamiento', 'superficie_adicional', DATE '2025-05-02', DATE '2025-05-03', 'Equipo técnico', 'Superficie revisada', v_seed_time, v_admin, 'Contexto adicional sin ciclo'),
      (v_pn4, 'sensibilizacion', 'general', NULL, DATE '2025-06-02', 'Equipo PA', 'Realizada', v_seed_time, v_admin, 'Fecha fuente');

    INSERT INTO parcela (id_nucleo, tipo_parcela, no_parcela, certificado_parcelario, folio_derechos, constancia_vigencia_fecha, geometria_poligono, fuente_geometria, fecha_fuente_geometria, creado_en, creado_por, observaciones)
    VALUES (v_n2, 'individual', 'P-172', '79616', '22FD00059363', DATE '2025-08-25', ST_GeomFromText('MULTIPOLYGON(((-100.1500 20.4500,-100.1490 20.4500,-100.1490 20.4510,-100.1500 20.4510,-100.1500 20.4500)))', 4326), 'SINTETICA_QA_NO_RAN', DATE '2025-08-25', v_seed_time, v_admin, 'Geometría sintética QA; no cartografía oficial RAN') RETURNING id_parcela INTO v_parcel172;
    INSERT INTO parcela (id_nucleo, tipo_parcela, no_parcela, certificado_parcelario, folio_derechos, constancia_vigencia_fecha, creado_en, creado_por, observaciones) VALUES (v_n2, 'individual', 'P-170', '79953', '22FD00074310', DATE '2025-08-25', v_seed_time, v_admin, 'Sin geometría por diseño') RETURNING id_parcela INTO v_parcel170;
    INSERT INTO parcela (id_nucleo, tipo_parcela, no_parcela, certificado_parcelario, folio_derechos, constancia_vigencia_fecha, creado_en, creado_por, observaciones) VALUES (v_n2, 'individual', 'P-173', '55831', '22FD00055387', DATE '2025-08-25', v_seed_time, v_admin, 'Sin geometría por diseño') RETURNING id_parcela INTO v_parcel173;
    INSERT INTO parcela (id_nucleo, tipo_parcela, no_parcela, certificado_parcelario, folio_derechos, constancia_vigencia_fecha, creado_en, creado_por, observaciones) VALUES (v_n2, 'individual', 'P-169', '55836', '22FD00055392', DATE '2025-08-25', v_seed_time, v_admin, 'Sin geometría por diseño') RETURNING id_parcela INTO v_parcel169;
    INSERT INTO parcela_titular (id_parcela, id_persona, tipo_derecho, porcentaje_participacion, fecha_inicio, creado_en, creado_por) VALUES
      (v_parcel172, v_person_172, 'titular', 100, DATE '2025-08-25', v_seed_time, v_admin),
      (v_parcel170, v_person_170, 'titular', 100, DATE '2025-08-25', v_seed_time, v_admin),
      (v_parcel173, v_person_173, 'titular', 100, DATE '2025-08-25', v_seed_time, v_admin),
      (v_parcel169, v_person_169, 'titular', 100, DATE '2025-08-25', v_seed_time, v_admin);

    INSERT INTO afectacion (id_proyecto_nucleo, tipo_afectacion, destino_superficie, superficie_preliminar_ha, superficie_afectada_ha, situacion, avaluo_monto, avaluo_fecha, avaluo_referencia, avaluo_institucion, creado_en, creado_por, observaciones)
    VALUES (v_pn1, 'colectivo', 'tierras_uso_comun', 10.500000, 10.000000, 'en_convenio', 1000000, DATE '2025-05-15', 'AV-QA-COL-001', 'Institución valuadora QA', v_seed_time, v_admin, 'Superficies/monto sintéticos QA') RETURNING id_afectacion INTO v_ca1;
    INSERT INTO afectacion (id_proyecto_nucleo, tipo_afectacion, destino_superficie, no_parcela_solar, superficie_preliminar_ha, superficie_afectada_ha, situacion, creado_en, creado_por, observaciones)
    VALUES (v_pn1, 'colectivo', 'parcela_escolar', 'P-60', 2.250000, 2.000000, 'en_convenio', v_seed_time, v_admin, 'Destino y referencia de fuente; superficies QA') RETURNING id_afectacion INTO v_ca2;
    INSERT INTO afectacion (id_proyecto_nucleo, tipo_afectacion, destino_superficie, superficie_preliminar_ha, superficie_afectada_ha, situacion, creado_en, creado_por, observaciones)
    VALUES (v_pn3, 'colectivo', 'tierras_uso_comun', 8.000000, 7.500000, 'seguimiento', v_seed_time, v_admin, 'Caso fuente; superficies QA') RETURNING id_afectacion INTO v_ca3;
    INSERT INTO afectacion (id_proyecto_nucleo, tipo_afectacion, destino_superficie, no_parcela_solar, superficie_preliminar_ha, superficie_afectada_ha, situacion, creado_en, creado_por, observaciones)
    VALUES (v_pn4, 'colectivo', 'solar', 'P-360', 0.400000, 0.350000, 'permuta', v_seed_time, v_admin, 'Caso fuente de superficie; valores QA') RETURNING id_afectacion INTO v_ca4;
    INSERT INTO afectacion (id_proyecto_nucleo, tipo_afectacion, destino_superficie, no_parcela_solar, superficie_preliminar_ha, superficie_afectada_ha, situacion, creado_en, creado_por, observaciones)
    VALUES (v_pn4, 'colectivo', 'solar', 'P-409', 0.450000, 0.400000, 'permuta', v_seed_time, v_admin, 'Segunda superficie del escenario N:M QA') RETURNING id_afectacion INTO v_ca5;
    INSERT INTO afectacion (id_proyecto_nucleo, tipo_afectacion, destino_superficie, superficie_preliminar_ha, superficie_afectada_ha, situacion, condicion_especial, descripcion_condicion, avaluo_monto, avaluo_fecha, creado_en, creado_por, observaciones)
    VALUES (v_pn2, 'colectivo', 'tierras_uso_comun', 3.000000, 2.800000, 'expropiacion', 'expropiacion_directa', 'Caso de expropiación directa sin cierre global', 2800000, DATE '2025-07-01', v_seed_time, v_admin, 'Condición reportada en fuente general; importes QA') RETURNING id_afectacion INTO v_ca6;

    INSERT INTO afectacion (id_proyecto_nucleo, id_parcela, tipo_afectacion, destino_superficie, superficie_preliminar_ha, superficie_afectada_ha, situacion, avaluo_monto, avaluo_fecha, avaluo_referencia, avaluo_institucion, creado_en, creado_por, observaciones) VALUES
      (v_pn2, v_parcel172, 'individual', 'parcela_individual', 4.291030, 4.291030, 'convenio_firmado', 14160399.33, DATE '2025-08-25', 'Excel PROPUESTA fila 7', 'Fuente Excel', v_seed_time, v_admin, 'Superficie administrativa convertida de 04-29-10.301; no derivada de geometría') RETURNING id_afectacion INTO v_ia172;
    INSERT INTO afectacion (id_proyecto_nucleo, id_parcela, tipo_afectacion, destino_superficie, superficie_preliminar_ha, superficie_afectada_ha, situacion, avaluo_monto, avaluo_fecha, avaluo_referencia, avaluo_institucion, creado_en, creado_por, observaciones) VALUES
      (v_pn2, v_parcel170, 'individual', 'parcela_individual', 0.324632, 0.324632, 'convenio_firmado', 1071285.93, DATE '2025-08-25', 'Excel PROPUESTA fila 8', 'Fuente Excel', v_seed_time, v_admin, 'Superficie administrativa convertida de 00-32-46.321') RETURNING id_afectacion INTO v_ia170;
    INSERT INTO afectacion (id_proyecto_nucleo, id_parcela, tipo_afectacion, destino_superficie, superficie_preliminar_ha, superficie_afectada_ha, situacion, avaluo_monto, avaluo_fecha, avaluo_referencia, avaluo_institucion, creado_en, creado_por, observaciones) VALUES
      (v_pn2, v_parcel173, 'individual', 'parcela_individual', 0.202846, 0.202846, 'convenio_firmado', 669391.47, DATE '2025-08-25', 'Excel PROPUESTA fila 9', 'Fuente Excel', v_seed_time, v_admin, 'Superficie administrativa convertida de 00-20-28.459') RETURNING id_afectacion INTO v_ia173;
    INSERT INTO afectacion (id_proyecto_nucleo, id_parcela, tipo_afectacion, destino_superficie, superficie_preliminar_ha, superficie_afectada_ha, situacion, avaluo_monto, avaluo_fecha, avaluo_referencia, avaluo_institucion, creado_en, creado_por, observaciones) VALUES
      (v_pn2, v_parcel169, 'individual', 'parcela_individual', 2.175041, 2.175041, 'convenio_firmado', 7177636.62, DATE '2025-08-25', 'Excel PROPUESTA fila 10', 'Fuente Excel', v_seed_time, v_admin, 'Superficie administrativa convertida de 02-17-50.414') RETURNING id_afectacion INTO v_ia169;

    INSERT INTO asamblea (id_proyecto_nucleo, id_padron, tipo_asamblea, proposito, fecha_expedicion_primera, fecha_programada_primera, fecha_expedicion_segunda, fecha_programada_segunda, fecha_realizada, resultado, fecha_programada_ingreso_ran, fecha_ingreso_ran, numero_solicitud_ran, calificacion_registral_ran, fecha_inscripcion_ran, creado_en, creado_por, observaciones)
    VALUES (v_pn1, v_padron1, 'anuencia', 'Autorizar convenios colectivos del expediente', DATE '2025-05-01', DATE '2025-05-10', DATE '2025-05-11', DATE '2025-05-20', DATE '2025-05-20', 'celebrada', DATE '2025-05-25', DATE '2025-05-26', 'RAN-ACTA-QA-001', 'positiva', DATE '2025-06-15', v_seed_time, v_admin, 'Una asamblea compartida por varios convenios') RETURNING id_asamblea INTO v_assembly1;
    INSERT INTO asamblea (id_proyecto_nucleo, id_padron, tipo_asamblea, proposito, fecha_programada_primera, fecha_realizada, resultado, fecha_ingreso_ran, numero_solicitud_ran, fecha_inscripcion_ran, creado_en, creado_por, observaciones)
    VALUES (v_pn4, v_padron4, 'anuencia', 'Autorizar permuta', DATE '2025-07-10', DATE '2025-07-20', 'celebrada', DATE '2025-08-01', 'RAN-PERM-QA', DATE '2025-08-20', v_seed_time, v_admin, 'Caso fuente permuta; fechas QA') RETURNING id_asamblea INTO v_assembly4;
    INSERT INTO asamblea (id_proyecto_nucleo, id_padron, tipo_asamblea, proposito, fecha_programada_primera, fecha_realizada, resultado, creado_en, creado_por, observaciones)
    VALUES (v_pn4, v_padron4, 'retiro_fondos', 'Retiro de fondos QA', DATE '2025-09-01', DATE '2025-09-05', 'celebrada', v_seed_time, v_admin, 'CASO SINTÉTICO QA') RETURNING id_asamblea INTO v_retiro4;

    INSERT INTO convenio (id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, consecutivo, id_asamblea_autorizacion, fecha_programada_firma, fecha_firma, monto_90, monto_100, superficie_ha, fecha_programada_ingreso_ran, ingreso_ran_fecha, numero_solicitud_ingreso, calificacion_registral, fecha_inscripcion_ran, creado_en, creado_por, observaciones)
    VALUES (v_pn1, 'colectivo', 'convenio', 'cop_original', 1, v_assembly1, DATE '2025-06-01', DATE '2025-06-05', 900000, 1000000, 12.000000, DATE '2025-06-10', DATE '2025-06-11', 'RAN-COL-QA-001', 'positiva', DATE '2025-07-01', v_seed_time, v_admin, 'Convenio colectivo N:M del seed') RETURNING id_convenio INTO v_cop_collective;
    INSERT INTO convenio_afectacion (id_convenio, id_afectacion, rol, creado_en, creado_por) VALUES (v_cop_collective, v_ca1, 'principal', v_seed_time, v_admin), (v_cop_collective, v_ca2, 'adicional', v_seed_time, v_admin);
    INSERT INTO convenio (id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, consecutivo, id_convenio_padre, id_asamblea_autorizacion, fecha_programada_firma, fecha_firma, monto_90, monto_100, superficie_ha, creado_en, creado_por, observaciones)
    VALUES (v_pn1, 'colectivo', 'convenio', 'modificatorio', 2, v_cop_collective, v_assembly1, DATE '2025-07-10', DATE '2025-07-12', 945000, 1050000, 12.100000, v_seed_time, v_admin, 'Misma asamblea del COP original') RETURNING id_convenio INTO v_modified;
    INSERT INTO convenio_afectacion (id_convenio, id_afectacion, rol, creado_en, creado_por) VALUES (v_modified, v_ca1, 'principal', v_seed_time, v_admin);
    INSERT INTO convenio (id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, consecutivo, id_asamblea_autorizacion, fecha_programada_firma, fecha_firma, monto_100, superficie_ha, creado_en, creado_por, observaciones)
    VALUES (v_pn1, 'colectivo', 'convenio', 'superficie_adicional', 1, v_assembly1, DATE '2025-07-15', DATE '2025-07-16', 200000, 2.000000, v_seed_time, v_admin, 'Actividad contextual asociada sólo por expediente/documentación') RETURNING id_convenio INTO v_additional;
    INSERT INTO convenio_afectacion (id_convenio, id_afectacion, rol, creado_en, creado_por) VALUES (v_additional, v_ca2, 'principal', v_seed_time, v_admin);
    INSERT INTO convenio (id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, consecutivo, id_asamblea_autorizacion, fecha_programada_firma, fecha_firma, monto_100, superficie_ha, creado_en, creado_por, observaciones)
    VALUES (v_pn1, 'colectivo', 'convenio', 'obras_complementarias', 1, v_assembly1, DATE '2025-08-01', DATE '2025-08-03', 150000, 0.500000, v_seed_time, v_admin, 'CASO SINTÉTICO QA') RETURNING id_convenio INTO v_works;
    INSERT INTO convenio_afectacion (id_convenio, id_afectacion, rol, creado_en, creado_por) VALUES (v_works, v_ca1, 'principal', v_seed_time, v_admin);

    INSERT INTO convenio (id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, modalidad_especial, consecutivo, id_asamblea_autorizacion, fecha_programada_firma, fecha_firma, monto_100, superficie_ha, creado_en, creado_por, observaciones)
    VALUES (v_pn4, 'colectivo', 'convenio', 'cop_original', 'permuta', 1, v_assembly4, DATE '2025-08-21', DATE '2025-08-21', 922460.39, 0.750000, v_seed_time, v_admin, '1 COP FIRMADO (PERMUTA); escenario N:M de dos superficies marcado QA') RETURNING id_convenio INTO v_permute;
    INSERT INTO convenio_afectacion (id_convenio, id_afectacion, rol, creado_en, creado_por, observaciones) VALUES (v_permute, v_ca4, 'principal', v_seed_time, v_admin, 'Principal'), (v_permute, v_ca5, 'adicional', v_seed_time, v_admin, 'Asociación adicional QA inspirada en caso dos solares');

    INSERT INTO convenio (id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, consecutivo, fecha_programada_firma, fecha_firma, monto_90, monto_100, superficie_ha, fecha_programada_ingreso_ran, ingreso_ran_fecha, numero_solicitud_ingreso, calificacion_registral, fecha_inscripcion_ran, creado_en, creado_por, observaciones)
    VALUES (v_pn2, 'individual', 'convenio', 'cop_original', 1, DATE '2025-08-25', DATE '2025-08-25', 12744359.40, 14160399.33, 4.291030, DATE '2025-09-03', DATE '2025-09-03', '22250008955', 'PARA ENTREGA', DATE '2025-12-01', v_seed_time, v_admin, 'Valores de Excel PROPUESTA fila 7') RETURNING id_convenio INTO v_cop_172;
    INSERT INTO convenio_afectacion (id_convenio, id_afectacion, rol, creado_en, creado_por) VALUES (v_cop_172, v_ia172, 'principal', v_seed_time, v_admin);
    INSERT INTO convenio (id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, consecutivo, fecha_programada_firma, fecha_firma, monto_90, monto_100, superficie_ha, fecha_programada_ingreso_ran, ingreso_ran_fecha, numero_solicitud_ingreso, calificacion_registral, fecha_inscripcion_ran, creado_en, creado_por, observaciones)
    VALUES (v_pn2, 'individual', 'convenio', 'cop_original', 1, DATE '2025-08-25', DATE '2025-08-25', 964157.34, 1071285.93, 0.324632, DATE '2025-09-03', DATE '2025-09-03', '22250008948', 'PARA ENTREGA', DATE '2025-12-01', v_seed_time, v_admin, 'Valores de Excel PROPUESTA fila 8') RETURNING id_convenio INTO v_cop_170;
    INSERT INTO convenio_afectacion (id_convenio, id_afectacion, rol, creado_en, creado_por) VALUES (v_cop_170, v_ia170, 'principal', v_seed_time, v_admin);
    INSERT INTO convenio (id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, consecutivo, id_convenio_padre, fecha_programada_firma, fecha_firma, monto_100, superficie_ha, creado_en, creado_por, observaciones)
    VALUES (v_pn2, 'individual', 'convenio', 'ampliacion', 2, v_cop_172, DATE '2025-10-01', DATE '2025-10-02', 100000, 0.050000, v_seed_time, v_admin, 'CASO SINTÉTICO QA') RETURNING id_convenio INTO v_expand;
    INSERT INTO convenio_afectacion (id_convenio, id_afectacion, rol, creado_en, creado_por) VALUES (v_expand, v_ia173, 'principal', v_seed_time, v_admin);
    INSERT INTO convenio (id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, consecutivo, id_convenio_padre, fecha_programada_firma, fecha_firma, monto_100, superficie_ha, creado_en, creado_por, observaciones)
    VALUES (v_pn2, 'individual', 'convenio', 'ampliacion_remanente', 3, v_cop_172, DATE '2025-10-10', DATE '2025-10-11', 125000, 0.060000, v_seed_time, v_admin, 'CASO SINTÉTICO QA') RETURNING id_convenio INTO v_remnant;
    INSERT INTO convenio_afectacion (id_convenio, id_afectacion, rol, creado_en, creado_por) VALUES (v_remnant, v_ia169, 'principal', v_seed_time, v_admin);

    INSERT INTO tramite_fifonafe (id_proyecto_nucleo, ambito, estatus, no_oficio_fifonafe_a_dgaopr, fecha_oficio_fifonafe_a_dgaopr, no_oficio_dgaopr_a_representacion, fecha_oficio_dgaopr_a_representacion, no_oficio_respuesta_representacion_a_dgaopr, fecha_oficio_respuesta_representacion_a_dgaopr, no_oficio_respuesta_dgaopr_a_fifonafe, fecha_oficio_respuesta_dgaopr_a_fifonafe, hay_conflictos, resultado_no_conflictos, creado_en, creado_por, observaciones)
    VALUES (v_pn1, 'colectivo', 'completo', 'FIF-QA-C-01', DATE '2025-06-01', 'DGA-QA-C-02', DATE '2025-06-05', 'REP-QA-C-03', DATE '2025-06-10', 'DGA-FIF-QA-C-04', DATE '2025-06-15', FALSE, 'Sin conflictos reportados', v_seed_time, v_admin, 'Cuatro oficios, un trámite, dos afectaciones') RETURNING id_tramite_fifonafe INTO v_fifo_collective;
    INSERT INTO tramite_fifonafe_afectacion (id_tramite_fifonafe, id_afectacion, creado_en, creado_por) VALUES (v_fifo_collective, v_ca1, v_seed_time, v_admin), (v_fifo_collective, v_ca2, v_seed_time, v_admin);
    INSERT INTO tramite_fifonafe (id_proyecto_nucleo, ambito, estatus, no_oficio_fifonafe_a_dgaopr, fecha_oficio_fifonafe_a_dgaopr, no_oficio_dgaopr_a_representacion, fecha_oficio_dgaopr_a_representacion, no_oficio_respuesta_representacion_a_dgaopr, fecha_oficio_respuesta_representacion_a_dgaopr, no_oficio_respuesta_dgaopr_a_fifonafe, fecha_oficio_respuesta_dgaopr_a_fifonafe, hay_conflictos, resultado_no_conflictos, creado_en, creado_por, observaciones)
    VALUES (v_pn2, 'individual', 'completo', 'FIF-QA-I-01', DATE '2025-09-01', 'DGA-QA-I-02', DATE '2025-09-05', 'REP-QA-I-03', DATE '2025-09-10', 'DGA-FIF-QA-I-04', DATE '2025-09-15', FALSE, 'Sin conflictos reportados', v_seed_time, v_admin, 'Cuatro oficios compartidos por cuatro parcelas') RETURNING id_tramite_fifonafe INTO v_fifo_individual;
    INSERT INTO tramite_fifonafe_afectacion (id_tramite_fifonafe, id_afectacion, creado_en, creado_por) VALUES (v_fifo_individual, v_ia172, v_seed_time, v_admin), (v_fifo_individual, v_ia170, v_seed_time, v_admin), (v_fifo_individual, v_ia173, v_seed_time, v_admin), (v_fifo_individual, v_ia169, v_seed_time, v_admin);

    INSERT INTO indemnizacion (id_afectacion, estatus, descripcion_estatus, fecha_programada, fecha_resolucion, creado_en, creado_por, observaciones)
    VALUES (v_ca6, 'completo', NULL, DATE '2025-07-10', DATE '2025-07-20', v_seed_time, v_admin, 'No depende de FIFONAFE; caso QA de expropiación directa') RETURNING id_indemnizacion INTO v_indemnity;
    INSERT INTO pago (id_indemnizacion, fecha_pago, monto, beneficiario_nombre, referencia, medio_pago, creado_en, creado_por, observaciones)
    VALUES (v_indemnity, DATE '2025-07-25', 2000000.00, 'Núcleo Ahorcado · beneficiario QA', 'PAGO-QA-001', 'transferencia', v_seed_time, v_admin, 'Primer pago') RETURNING id_pago INTO v_payment1;
    INSERT INTO pago (id_indemnizacion, fecha_pago, monto, beneficiario_nombre, referencia, medio_pago, creado_en, creado_por, observaciones)
    VALUES (v_indemnity, DATE '2025-08-05', 800000.00, 'Núcleo Ahorcado · beneficiario QA', 'PAGO-QA-002', 'cheque', v_seed_time, v_admin, 'Segundo pago') RETURNING id_pago INTO v_payment2;

    INSERT INTO documento (tipo_documento, estado, titulo, descripcion, creado_en, creado_por, observaciones)
    VALUES ('soporte_convenio', 'disponible', 'Soporte sintético de QA', 'Archivo pequeño versionado para pruebas de inmutabilidad.', v_seed_time, v_admin, 'No es documento oficial') RETURNING id_documento INTO v_document1;
    INSERT INTO documento_vinculo (id_documento, entidad_tipo, entidad_id, creado_en, creado_por) VALUES (v_document1, 'convenio', v_permute, v_seed_time, v_admin);
    INSERT INTO documento_version (id_documento, numero_version, hash_sha256, tamano_bytes, nombre_original, ruta_almacenamiento, tipo_mime, fecha_carga, id_usuario_carga)
    VALUES (v_document1, 1, 'dee42d98c899eb2dc8dba9f95326ded525de0b4ce752a82208880da79e679717', 161, 'qa_soporte_demo.txt', 'seed/qa_soporte_demo.txt', 'text/plain', v_seed_time, v_admin);
    INSERT INTO documento (tipo_documento, estado, titulo, descripcion, creado_en, creado_por, observaciones)
    VALUES ('acta_asamblea', 'faltante', 'Acta pendiente de soporte', 'Permite validar el estado faltante sin archivo.', v_seed_time, v_admin, 'Caso demo') RETURNING id_documento INTO v_document2;
    INSERT INTO documento_vinculo (id_documento, entidad_tipo, entidad_id, creado_en, creado_por) VALUES (v_document2, 'asamblea', v_assembly1, v_seed_time, v_admin);
    INSERT INTO documento (tipo_documento, estado, titulo, descripcion, creado_en, creado_por, observaciones)
    VALUES ('comprobante_pago', 'referenciado', 'Comprobante bancario referenciado', 'La referencia existe; el binario no forma parte del seed.', v_seed_time, v_admin, 'Caso demo') RETURNING id_documento INTO v_document3;
    INSERT INTO documento_vinculo (id_documento, entidad_tipo, entidad_id, creado_en, creado_por) VALUES (v_document3, 'pago', v_payment1, v_seed_time, v_admin);

    INSERT INTO trazabilidad_fuente (entidad_tipo, entidad_id, archivo, hoja, fila, columna, valor_original, tratamiento, registrado_en, id_usuario_registro) VALUES
      ('nucleo_agrario', v_n1, 'Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx', 'INFORME M-Q', 8, 'F', 'SAN ILDEFONSO', 'PERSISTIR', v_seed_time, v_admin),
      ('nucleo_agrario', v_n5, 'SEED_QA_INTERNO', 'QA', 1, 'caso', 'COMUNIDAD QA MODELO OBJETIVO', 'DOCUMENTAR', v_seed_time, v_admin),
      ('proyecto_nucleo_referencia', (SELECT id_referencia FROM proyecto_nucleo_referencia WHERE id_proyecto_nucleo = v_pn1 AND tipo_referencia = 'consecutivo' AND es_principal), 'Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx', 'INFORME M-Q', 8, 'A', '2', 'REFERENCIA', v_seed_time, v_admin),
      ('parcela', v_parcel172, 'SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx', 'PROPUESTA', 7, 'L', 'P-172', 'PERSISTIR', v_seed_time, v_admin),
      ('parcela', v_parcel170, 'SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx', 'PROPUESTA', 8, 'L', 'P-170', 'PERSISTIR', v_seed_time, v_admin),
      ('parcela', v_parcel173, 'SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx', 'PROPUESTA', 9, 'L', 'P-173', 'PERSISTIR', v_seed_time, v_admin),
      ('parcela', v_parcel169, 'SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx', 'PROPUESTA', 10, 'L', 'P-169', 'PERSISTIR', v_seed_time, v_admin),
      ('afectacion', v_ia172, 'SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx', 'PROPUESTA', 7, 'AD', '04-29-10.301', 'PERSISTIR', v_seed_time, v_admin),
      ('convenio', v_cop_172, 'SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx', 'PROPUESTA', 7, 'S:AB', 'Firma, montos y RAN', 'PERSISTIR', v_seed_time, v_admin),
      ('convenio', v_permute, 'Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx', 'PCOLECTIVAS', 3, 'K', '1 COP FIRMADO (PERMUTA)', 'PERSISTIR', v_seed_time, v_admin),
      ('convenio', v_permute, 'Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx', 'PCOLECTIVAS', 3, 'K', 'Asociación adicional a segunda superficie para probar N:M', 'DOCUMENTAR', v_seed_time, v_admin),
      ('tramite_fifonafe', v_fifo_collective, 'SEED_QA_INTERNO', 'QA', 2, 'oficios', 'Cuatro oficios sintéticos QA', 'DOCUMENTAR', v_seed_time, v_admin),
      ('indemnizacion', v_indemnity, 'SEED_QA_INTERNO', 'QA', 3, 'cadena_financiera', 'Indemnización directa sin FK a FIFONAFE', 'DOCUMENTAR', v_seed_time, v_admin),
      ('documento', v_document1, 'SEED_QA_INTERNO', 'QA', 4, 'version', 'qa_soporte_demo.txt', 'DOCUMENTAR', v_seed_time, v_admin);

    RAISE NOTICE 'Seed objetivo creado: proyectos %, ProyectoNucleo %, parcelas %, afectaciones %, convenios %, FIFONAFE %, pagos %',
      (SELECT COUNT(*) FROM proyecto), (SELECT COUNT(*) FROM proyecto_nucleo), (SELECT COUNT(*) FROM parcela),
      (SELECT COUNT(*) FROM afectacion), (SELECT COUNT(*) FROM convenio), (SELECT COUNT(*) FROM tramite_fifonafe), (SELECT COUNT(*) FROM pago);
END;
$seed$;

COMMIT;
