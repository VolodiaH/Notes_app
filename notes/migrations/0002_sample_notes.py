from datetime import datetime, timezone

from django.db import migrations


def seed_notes(apps, schema_editor):
    Category = apps.get_model('notes', 'Category')
    Note = apps.get_model('notes', 'Note')
    database = schema_editor.connection.alias
    samples = [
        ('Навчання', 'Плани на тиждень',
         'Завершити головну сторінку застосунку.\nПовторити моделі та міграції Django.',
         datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc)),
        ('Ідеї', 'Ідеї для проєкту',
         'Додати пошук за назвою та категорії нотаток.\nПродумати форму для нових записів.',
         None),
        ('Особисте', 'Список покупок',
         'Кава, молоко, яблука та хліб.\nНовий блокнот для записів.',
         None),
    ]
    for category_title, title, text, reminder in samples:
        category = Category.objects.using(database).create(title=category_title)
        Note.objects.using(database).create(
            title=title, text=text, reminder=reminder, category=category
        )


class Migration(migrations.Migration):
    dependencies = [('notes', '0001_initial')]
    operations = [migrations.RunPython(seed_notes, migrations.RunPython.noop)]
