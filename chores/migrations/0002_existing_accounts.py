from django.db import migrations


def import_existing_emails(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Account = apps.get_model("chores", "Account")
    alias = schema_editor.connection.alias
    seen = set()
    accounts = []
    for user in User.objects.using(alias).exclude(email="").iterator():
        email = user.email.strip().lower()
        if not email:
            continue
        if email in seen:
            raise RuntimeError(
                "Existing users have duplicate email addresses. Resolve duplicates before migrating; no users have been changed."
            )
        seen.add(email)
        accounts.append(Account(user_id=user.pk, email=email, role="member"))
    Account.objects.using(alias).bulk_create(accounts)


class Migration(migrations.Migration):
    dependencies = [("chores", "0001_initial")]
    operations = [migrations.RunPython(import_existing_emails, migrations.RunPython.noop)]
