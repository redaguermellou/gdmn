# dossier_medicale/migrations/0009_fix_employee_id_removal.py
from django.db import migrations

def mark_employee_id_removed(apps, schema_editor):
    """This function does nothing since column was already removed manually"""
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('dossier_medicale', '0008_remove_dossiermedical_employee_id_and_more'),
    ]

    operations = [
        migrations.RunPython(
            code=mark_employee_id_removed,
            reverse_code=migrations.RunPython.noop,
        ),
    ]