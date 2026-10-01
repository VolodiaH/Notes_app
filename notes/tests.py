from datetime import datetime, timezone

from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .models import Category, Note


class NotesTests(TestCase):
    def test_sample_data_migration(self):
        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(Note.objects.count(), 3)
        self.assertTrue(Note.objects.filter(reminder__isnull=False).exists())

    def test_homepage_reads_database_with_categories_in_one_query(self):
        category = Category.objects.create(title='Робота')
        Note.objects.create(
            title='Нова нотатка з бази',
            text='Перший рядок\nДругий рядок <script>alert(1)</script>',
            reminder=datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc),
            category=category,
        )
        with self.assertNumQueries(1):
            response = self.client.get(reverse('notes:index'))
        self.assertContains(response, 'Нова нотатка з бази')
        self.assertContains(response, 'Робота')
        self.assertContains(response, 'Перший рядок<br>Другий рядок')
        self.assertContains(response, '&lt;script&gt;')
        self.assertContains(response, '05.10.2026 12:00')
        self.assertContains(response, 'Без нагадування')

    def test_empty_homepage(self):
        Note.objects.all().delete()
        response = self.client.get(reverse('notes:index'))
        self.assertContains(response, 'Нотаток поки немає')

    def test_category_with_notes_cannot_be_deleted(self):
        note = Note.objects.first()
        with self.assertRaises(ProtectedError):
            note.category.delete()
