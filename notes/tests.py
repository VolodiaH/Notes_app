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

    def test_homepage_reads_database_with_categories(self):
        category = Category.objects.create(title='Робота')
        Note.objects.create(
            title='Нова нотатка з бази',
            text='Перший рядок\nДругий рядок <script>alert(1)</script>',
            reminder=datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc),
            category=category,
        )
        with self.assertNumQueries(2):
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


class NoteWorkflowTests(TestCase):
    def setUp(self):
        Note.objects.all().delete()
        self.category = Category.objects.first()
        self.other_category = Category.objects.exclude(pk=self.category.pk).first()
        self.note = Note.objects.create(
            title='Weekly plan', text='Original text', category=self.category,
            reminder=datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc),
        )
        self.payload = {
            'title': 'Updated title', 'text': 'Updated text',
            'reminder': '2026-10-06T12:30', 'category': self.other_category.pk,
        }

    def test_create_and_redirect_to_details(self):
        self.assertEqual(self.client.get(reverse('notes:create')).status_code, 200)
        response = self.client.post(reverse('notes:create'), self.payload)
        note = Note.objects.get(title='Updated title')
        self.assertRedirects(response, reverse('notes:detail', args=[note.pk]))
        self.assertEqual(note.reminder, datetime(2026, 10, 6, 9, 30, tzinfo=timezone.utc))
        self.assertEqual(note.category, self.other_category)

    def test_details_prefill_and_update_all_fields(self):
        url = reverse('notes:detail', args=[self.note.pk])
        self.assertContains(self.client.get(url), '2026-10-05T12:00')
        self.assertRedirects(self.client.post(url, self.payload), url)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, 'Updated title')
        self.assertEqual(self.note.text, 'Updated text')
        self.assertEqual(self.note.category, self.other_category)
        self.assertEqual(self.note.reminder, datetime(2026, 10, 6, 9, 30, tzinfo=timezone.utc))
        self.client.post(url, {**self.payload, 'reminder': ''})
        self.note.refresh_from_db()
        self.assertIsNone(self.note.reminder)

    def test_invalid_forms_do_not_write(self):
        for changes in ({'title': ''}, {'text': ''}, {'category': 999999}, {'reminder': 'bad date'}):
            for url in (reverse('notes:create'), reverse('notes:detail', args=[self.note.pk])):
                response = self.client.post(url, {**self.payload, **changes})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        self.assertEqual(Note.objects.count(), 1)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, 'Weekly plan')

    def test_delete_requires_post_and_csrf(self):
        from django.test import Client
        url = reverse('notes:delete', args=[self.note.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(Client(enforce_csrf_checks=True).post(url).status_code, 403)
        self.assertTrue(Note.objects.filter(pk=self.note.pk).exists())
        self.assertRedirects(self.client.post(url), reverse('notes:index'))
        self.assertFalse(Note.objects.filter(pk=self.note.pk).exists())
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_missing_note_returns_404(self):
        self.assertEqual(self.client.get(reverse('notes:detail', args=[999999])).status_code, 404)
        self.assertEqual(self.client.post(reverse('notes:delete', args=[999999])).status_code, 404)

    def test_search_and_filters_individually_and_combined(self):
        other = Note.objects.create(title='Other note', text='Weekly plan', category=self.other_category)
        cases = [
            ({'q': 'wEeKlY'}, [self.note]),
            ({'category': self.other_category.pk}, [other]),
            ({'reminder_from': '2026-10-05T12:00'}, [self.note]),
            ({'reminder_to': '2026-10-05T12:00'}, [self.note]),
            ({'reminder_from': '2026-10-05T12:01'}, []),
            ({'q': 'weekly', 'category': self.category.pk,
              'reminder_from': '2026-10-05T12:00', 'reminder_to': '2026-10-05T12:00'}, [self.note]),
            ({'q': 'weekly', 'category': self.other_category.pk}, []),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                response = self.client.get(reverse('notes:index'), params)
                self.assertEqual(list(response.context['notes']), expected)

    def test_invalid_filters_show_errors(self):
        for params in ({'category': 'invalid'}, {'reminder_from': 'invalid'},
                       {'reminder_from': '2026-10-06T12:00', 'reminder_to': '2026-10-05T12:00'}):
            response = self.client.get(reverse('notes:index'), params)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['filters'].errors)
            self.assertContains(response, 'Виправте помилки у фільтрах.')
