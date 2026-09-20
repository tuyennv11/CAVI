# Bước 2/3 — chuyển dữ liệu: mỗi Đối tác đang có assigned_to (User) trỏ sang đúng Hồ sơ nhân sự
# (Profile) của chính tài khoản đó (Profile.user OneToOne User, mỗi User luôn có đúng 1 Profile do
# signal hr.signals.create_profile_for_new_user tạo sẵn). Đối tác nào chưa gán ai (assigned_to rỗng)
# thì giữ nguyên rỗng.

from django.db import migrations


def forwards(apps, schema_editor):
    Partner = apps.get_model("crm", "Partner")
    Profile = apps.get_model("hr", "Profile")
    for partner in Partner.objects.exclude(assigned_to__isnull=True).only("id", "assigned_to_id"):
        profile = Profile.objects.filter(user_id=partner.assigned_to_id).first()
        if profile is not None:
            partner.assigned_to_profile_id = profile.id
            partner.save(update_fields=["assigned_to_profile"])


def backwards(apps, schema_editor):
    Partner = apps.get_model("crm", "Partner")
    for partner in Partner.objects.exclude(assigned_to_profile__isnull=True).only("id", "assigned_to_profile_id"):
        partner.assigned_to_id = partner.assigned_to_profile.user_id
        partner.save(update_fields=["assigned_to"])


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0040_partner_assigned_to_profile_step1'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
