from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
import io

from apps.gso_requests.forms import RequestForm
from apps.gso_units.models import Unit


class RequestAttachmentValidationTests(TestCase):
    def setUp(self):
        self.unit = Unit.objects.create(
            name='Electrical Services',
            code='electrical',
            is_active=True,
        )

    def _base_data(self):
        return {
            'unit': self.unit.pk,
            'description': 'Replace busted lights in room 101',
            'location': 'IT Building - 101',
            'labor': True,
            'materials': False,
            'others': False,
            'custom_full_name': 'Test Requestor',
            'custom_email': 'requestor@example.com',
            'custom_contact_number': '09123456789',
        }

    def test_accepts_valid_png_attachment(self):
        img_buf = io.BytesIO()
        Image.new('RGB', (1, 1), color='white').save(img_buf, format='PNG')
        png_bytes = img_buf.getvalue()
        file_obj = SimpleUploadedFile(
            'valid.png',
            png_bytes,
            content_type='image/png',
        )
        form = RequestForm(data=self._base_data(), files={'attachment': file_obj})
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_rejects_fake_image_with_jpg_extension(self):
        fake_file = SimpleUploadedFile(
            'not-really-image.jpg',
            b'This is not an image',
            content_type='image/jpeg',
        )
        form = RequestForm(data=self._base_data(), files={'attachment': fake_file})
        self.assertFalse(form.is_valid())
        self.assertIn('attachment', form.errors)

