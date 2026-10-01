from datetime import datetime, timezone

from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from .forms import NoteForm
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


class NoteFormUnitTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(title='Unit: original')
        cls.other_category = Category.objects.create(title='Unit: updated')

    def setUp(self):
        self.payload = {
            'title': 'Нова нотатка', 'text': 'Перший рядок\nДругий рядок',
            'reminder': '2026-10-06T12:30', 'category': self.category.pk,
        }

    def make_note(self):
        return Note.objects.create(
            title='Початкова назва', text='Початковий текст',
            reminder=datetime(2026, 10, 5, 9, tzinfo=timezone.utc),
            category=self.category,
        )

    def test_save_creates_note_with_all_fields(self):
        count = Note.objects.count()
        form = NoteForm(data=self.payload)
        self.assertTrue(form.is_valid(), form.errors)
        note = form.save()
        note.refresh_from_db()
        self.assertEqual(Note.objects.count(), count + 1)
        self.assertEqual(note.title, self.payload['title'])
        self.assertEqual(note.text, self.payload['text'])
        self.assertEqual(note.category_id, self.category.pk)
        self.assertEqual(note.reminder, datetime(2026, 10, 6, 9, 30, tzinfo=timezone.utc))

    def test_save_without_optional_reminder(self):
        form = NoteForm(data={**self.payload, 'reminder': ''})
        self.assertTrue(form.is_valid(), form.errors)
        note = form.save()
        note.refresh_from_db()
        self.assertIsNone(note.reminder)

    def test_update_preserves_identity_and_changes_all_fields(self):
        note = self.make_note()
        original_pk, count = note.pk, Note.objects.count()
        form = NoteForm(data={**self.payload, 'category': self.other_category.pk}, instance=note)
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        updated.refresh_from_db()
        self.assertEqual(updated.pk, original_pk)
        self.assertEqual(Note.objects.count(), count)
        self.assertEqual(updated.title, self.payload['title'])
        self.assertEqual(updated.text, self.payload['text'])
        self.assertEqual(updated.category_id, self.other_category.pk)
        self.assertEqual(updated.reminder, datetime(2026, 10, 6, 9, 30, tzinfo=timezone.utc))

    def test_update_can_clear_reminder(self):
        note = self.make_note()
        form = NoteForm(data={**self.payload, 'reminder': ''}, instance=note)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        note.refresh_from_db()
        self.assertIsNone(note.reminder)

    def test_commit_false_does_not_write_until_explicit_save(self):
        count = Note.objects.count()
        form = NoteForm(data=self.payload)
        self.assertTrue(form.is_valid(), form.errors)
        note = form.save(commit=False)
        self.assertIsNone(note.pk)
        self.assertEqual(Note.objects.count(), count)
        note.save()
        self.assertTrue(Note.objects.filter(pk=note.pk).exists())

    def test_invalid_create_and_update_leave_database_unchanged(self):
        note = self.make_note()
        invalid_values = (
            ('title', ''), ('title', '   '), ('title', 'x' * 201),
            ('text', ''), ('category', ''), ('category', 999999),
            ('reminder', 'not-a-date'),
        )
        for field, value in invalid_values:
            for instance in (None, note):
                with self.subTest(field=field, value=value, update=instance is not None):
                    before = list(Note.objects.order_by('pk').values())
                    form = NoteForm(data={**self.payload, field: value}, instance=instance)
                    self.assertFalse(form.is_valid())
                    self.assertIn(field, form.errors)
                    with self.assertRaises(ValueError):
                        form.save()
                    self.assertEqual(list(Note.objects.order_by('pk').values()), before)
                    note.refresh_from_db()


class NoteHTTPIntegrationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(title='HTTP category')
        cls.other_category = Category.objects.create(title='HTTP updated category')

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.payload = {
            'title': 'HTTP created', 'text': 'Created through client',
            'reminder': '2026-10-06T12:30', 'category': self.category.pk,
        }

    def csrf_token(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'notes/form.html')
        return self.client.cookies['csrftoken'].value

    def test_create_read_update_delete_with_real_csrf_validation(self):
        count = Note.objects.count()
        create_url = reverse('notes:create')
        token = self.csrf_token(create_url)
        response = self.client.post(create_url, self.payload, HTTP_X_CSRFTOKEN=token)
        note = Note.objects.get(title=self.payload['title'])
        detail_url = reverse('notes:detail', args=[note.pk])
        self.assertRedirects(response, detail_url)
        self.assertEqual(Note.objects.count(), count + 1)
        self.assertEqual(note.text, self.payload['text'])
        self.assertEqual(note.category_id, self.category.pk)
        self.assertEqual(note.reminder, datetime(2026, 10, 6, 9, 30, tzinfo=timezone.utc))
        self.assertContains(self.client.get(detail_url), self.payload['text'])

        updated = {**self.payload, 'title': 'HTTP updated', 'text': 'Changed through client',
                   'reminder': '', 'category': self.other_category.pk}
        response = self.client.post(detail_url, updated, HTTP_X_CSRFTOKEN=token)
        self.assertRedirects(response, detail_url)
        note.refresh_from_db()
        self.assertEqual(Note.objects.count(), count + 1)
        self.assertEqual(note.title, updated['title'])
        self.assertEqual(note.text, updated['text'])
        self.assertEqual(note.category_id, self.other_category.pk)
        self.assertIsNone(note.reminder)
        self.assertContains(self.client.get(reverse('notes:index')), updated['title'])
        self.assertContains(self.client.get(detail_url), updated['text'])

        response = self.client.post(reverse('notes:delete', args=[note.pk]), HTTP_X_CSRFTOKEN=token)
        self.assertRedirects(response, reverse('notes:index'))
        self.assertEqual(Note.objects.count(), count)
        self.assertEqual(self.client.get(detail_url).status_code, 404)

    def test_create_and_update_without_csrf_do_not_write(self):
        note = Note.objects.create(title='Protected', text='Original', category=self.category)
        before = list(Note.objects.order_by('pk').values())
        for url in (reverse('notes:create'), reverse('notes:detail', args=[note.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, self.payload).status_code, 403)
                self.assertEqual(list(Note.objects.order_by('pk').values()), before)

    def test_invalid_post_displays_errors_and_preserves_all_data(self):
        note = Note.objects.create(title='Original', text='Unchanged', category=self.category)
        before = list(Note.objects.order_by('pk').values())
        for url in (reverse('notes:create'), reverse('notes:detail', args=[note.pk])):
            with self.subTest(url=url):
                token = self.csrf_token(url)
                response = self.client.post(url, {**self.payload, 'title': ''}, HTTP_X_CSRFTOKEN=token)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'notes/form.html')
                self.assertIn('title', response.context['form'].errors)
                self.assertContains(response, self.payload['text'])
                self.assertEqual(list(Note.objects.order_by('pk').values()), before)

    def test_unsupported_methods_and_missing_update_do_not_write(self):
        note = Note.objects.create(title='Original', text='Unchanged', category=self.category)
        before = list(Note.objects.order_by('pk').values())
        token = self.csrf_token(reverse('notes:create'))
        for url in (reverse('notes:create'), reverse('notes:detail', args=[note.pk])):
            for method in ('put', 'patch', 'delete'):
                with self.subTest(url=url, method=method):
                    response = getattr(self.client, method)(url, HTTP_X_CSRFTOKEN=token)
                    self.assertEqual(response.status_code, 405)
        missing_pk = Note.objects.order_by('-pk').first().pk + 1
        response = self.client.post(reverse('notes:detail', args=[missing_pk]),
                                    self.payload, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(list(Note.objects.order_by('pk').values()), before)
