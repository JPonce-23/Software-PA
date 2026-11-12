"""Opt-in SCA checks on the disposable synthetic database, never A/B."""
import os
import unittest
import psycopg2


class SCACompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('SCA_DISPOSABLE_DATABASE') != 'software_pa_test':
            raise RuntimeError('Explicit synthetic database opt-in required')
        cls.owner = psycopg2.connect(host=os.environ['DB_HOST'], dbname='software_pa_test',
            user=os.environ['POSTGRES_ADMIN_USER'], password=os.environ['POSTGRES_ADMIN_PASSWORD'])
        with cls.owner.cursor() as cur:
            cur.execute("SELECT current_database(),current_setting('cluster_name')")
            if cur.fetchone() != ('software_pa_test', 'pr6-sca-synthetic-disposable'):
                cls.owner.close()
                raise RuntimeError('Wrong disposable database marker')
        cls.runtime = psycopg2.connect(host=os.environ['DB_HOST'], dbname='software_pa_test',
            user=os.environ['DB_RUNTIME_USER'], password=os.environ['DB_RUNTIME_PASSWORD'])

    @classmethod
    def tearDownClass(cls):
        cls.runtime.close()
        cls.owner.close()

    def tearDown(self):
        self.owner.rollback()
        self.runtime.rollback()

    def test_postgresql15_and_extension_versions(self):
        with self.owner.cursor() as cur:
            cur.execute("SELECT current_setting('server_version_num')::int")
            self.assertGreaterEqual(cur.fetchone()[0], 150019)
            cur.execute("SELECT current_setting('server_version_num')::int < 160000")
            self.assertTrue(cur.fetchone()[0])
            cur.execute("SELECT extname,extversion FROM pg_extension")
            versions = dict(cur.fetchall())
            for name in ['postgis', 'postgis_topology', 'postgis_tiger_geocoder']:
                self.assertEqual(versions[name], '3.6.4')
            self.assertEqual(versions['btree_gist'], '1.7')
            cur.execute('SELECT count(*), max(version) FROM schema_migrations')
            self.assertEqual(cur.fetchone(), (33, '033'))

    def test_restored_spatial_data_projection_and_index(self):
        with self.runtime.cursor() as cur:
            cur.execute("SELECT ST_AsEWKT(geom),label,ST_DWithin(geom,ST_Transform(ST_Transform(geom,3857),4326),1e-9) FROM sca_spatial_fixture WHERE id=1")
            self.assertEqual(cur.fetchone(), ('SRID=4326;POINT(-99 20)', 'ñ sintético', True))
            cur.execute("SELECT indexdef FROM pg_indexes WHERE indexname='sca_spatial_fixture_gist'")
            self.assertIn('USING gist', cur.fetchone()[0])

    def test_synthetic_constraints_still_enforced(self):
        for statement, code in [
            ("INSERT INTO sca_spatial_fixture VALUES(1,ST_SetSRID(ST_Point(0,0),4326),'synthetic')", '23505'),
            ("INSERT INTO sca_spatial_fixture VALUES(2,NULL,'synthetic')", '23502'),
            ("INSERT INTO sca_spatial_fixture VALUES(2,ST_SetSRID(ST_Point(0,0),4326),'')", '23514')]:
            with self.subTest(code=code):
                with self.owner.cursor() as cur:
                    with self.assertRaises(psycopg2.Error) as caught:
                        cur.execute(statement)
                    self.assertEqual(caught.exception.pgcode, code)
                self.owner.rollback()

    def test_flatgeobuf_decoders_denied_before_c_execution(self):
        with self.runtime.cursor() as cur:
            cur.execute("SELECT has_function_privilege(current_user,oid,'EXECUTE') FROM pg_proc WHERE proname IN ('st_fromflatgeobuf','st_fromflatgeobuftotable')")
            self.assertEqual(cur.fetchall(), [(False,), (False,)])
        for statement in [
            'SELECT ST_FromFlatGeobuf(NULL::sca_spatial_fixture,NULL::bytea)',
            "SELECT ST_FromFlatGeobufToTable('public','synthetic_never_created','synthetic'::bytea)"]:
            with self.subTest(statement=statement):
                with self.runtime.cursor() as cur:
                    with self.assertRaises(psycopg2.Error) as caught:
                        cur.execute(statement)
                    self.assertEqual(caught.exception.pgcode, '42501')
                self.runtime.rollback()
        with self.owner.cursor() as cur:
            cur.execute("SELECT count(*) FROM pg_proc WHERE prosecdef AND prosrc ILIKE '%fromflatgeobuf%'")
            self.assertEqual(cur.fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
