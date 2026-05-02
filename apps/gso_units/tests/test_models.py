from django.test import SimpleTestCase

from apps.gso_units.models import Unit


class UnitMotorpoolDetectionTests(SimpleTestCase):
    def test_slug_and_name_variants(self):
        samples = (
            ({'code': 'motorpool', 'name': 'Anything'}, True),
            ({'code': 'motorpool_transport', 'name': 'Fleet'}, True),
            ({'code': 'vehicles', 'name': 'Motorpool'}, True),
            ({'code': 'vehicles', 'name': 'Motorpool Division'}, True),
            ({'code': 'other', 'name': 'Repair & Maintenance'}, False),
            ({'code': 'fleet', 'name': 'Non-Motorpool Team'}, False),
        )
        for fields, expected in samples:
            u = Unit(**fields)
            self.assertEqual(u.is_motorpool, expected, msg=repr(fields))
