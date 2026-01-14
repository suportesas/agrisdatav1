from django.test import SimpleTestCase
from django.urls import reverse, NoReverseMatch


class VehicleAssignmentRemovedTests(SimpleTestCase):
    def test_assignment_url_removed(self):
        with self.assertRaises(NoReverseMatch):
            reverse('cadastros:vehicle_assignment_create', args=[1])
