from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_existing_notes(apps, schema_editor):
    Note = apps.get_model('notes', 'Note')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    database = schema_editor.connection.alias
    if Note.objects.using(database).filter(owner__isnull=True).exists():
        user = User.objects.using(database).create(
            username='legacy_notes_owner', is_active=False, password='!',
        )
        Note.objects.using(database).filter(owner__isnull=True).update(owner=user)


class Migration(migrations.Migration):
    dependencies = [
        ('notes', '0002_sample_notes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [
        migrations.AddField(
            model_name='note', name='owner',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True,
                                    related_name='notes', on_delete=django.db.models.deletion.CASCADE),
        ),
        migrations.AddField(
            model_name='note', name='group',
            field=models.ForeignKey(to='auth.group', null=True, blank=True,
                                    related_name='notes', on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.RunPython(assign_existing_notes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='note', name='owner',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL,
                                    related_name='notes', on_delete=django.db.models.deletion.CASCADE),
        ),
    ]
