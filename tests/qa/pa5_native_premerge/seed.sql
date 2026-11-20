\set ON_ERROR_STOP on
BEGIN;
DO $$ BEGIN
 IF current_database()<>'software_pa_test' OR current_setting('cluster_name') NOT LIKE 'pa5-pr8-%' THEN RAISE EXCEPTION 'not private QA cluster'; END IF;
 IF EXISTS(SELECT 1 FROM usuario) THEN RAISE EXCEPTION 'seed requires new synthetic DB'; END IF;
END $$;
SELECT set_config('app.current_user_id','1',true);
INSERT INTO usuario(id_usuario,nombre,apellido_paterno,correo,contrasena_hash,rol,observaciones)
VALUES(1,'PA5','Synthetic','pa5-qa@example.invalid','unused-no-login-fixture','admin','PA5 synthetic private cluster');
SELECT setval(pg_get_serial_sequence('usuario','id_usuario'),1,true);
INSERT INTO entidad_federativa(clave_inegi,nombre) VALUES('99','PA5 synthetic state') RETURNING id_entidad \gset
INSERT INTO municipio(id_entidad,clave_inegi,nombre) VALUES(:id_entidad,'999','PA5 synthetic town') RETURNING id_municipio \gset
SELECT id_catalogo_opcion AS tenure FROM catalogo_operativo WHERE tipo_catalogo='tipo_tenencia' AND codigo='ejido' AND activo \gset
INSERT INTO nucleo_agrario(id_municipio,nombre_nucleo,id_tipo_tenencia,creado_por) VALUES(:id_municipio,'PA5 synthetic nucleus',:tenure,1) RETURNING id_nucleo \gset
INSERT INTO proyecto(clave_proyecto,nombre_proyecto,creado_por) VALUES('PA5_SYNTHETIC','PA5 synthetic project',1) RETURNING id_proyecto \gset
INSERT INTO proyecto_nucleo(id_proyecto,id_nucleo,creado_por) VALUES(:id_proyecto,:id_nucleo,1) RETURNING id_proyecto_nucleo \gset
INSERT INTO afectacion(id_proyecto_nucleo,tipo_afectacion,observaciones,creado_por) VALUES(:id_proyecto_nucleo,'colectivo','Synthetic only',1) RETURNING id_afectacion \gset
INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,estado_antecedente,descripcion_instrumento,creado_por) VALUES(:id_proyecto_nucleo,'colectivo','convenio','cop_original','no_aplica','PA5 synthetic fixture',1) RETURNING id_convenio \gset
INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(:id_convenio,:id_afectacion,1);
SET CONSTRAINTS ALL IMMEDIATE;
COMMIT;
SELECT 'PA5_SYNTHETIC_SEED_OK';
