from pathlib import Path
from django.db import migrations
SQL=(Path(__file__).resolve().parents[2]/"schema_postgresql.sql").read_text(encoding="utf-8")
class Migration(migrations.Migration):
    initial=True
    dependencies=[]
    operations=[migrations.RunSQL(SQL)]
