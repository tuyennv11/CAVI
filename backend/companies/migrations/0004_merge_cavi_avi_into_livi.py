# Chỉnh tay: công ty giờ chỉ còn LIVI hoạt động thật — dữ liệu còn gắn với CAVI/AVI (đơn hàng, đối
# tác, hồ sơ nhân viên...) được chuyển hẳn sang LIVI để không "treo" dưới 1 công ty đã ngừng hoạt
# động, sau đó xoá bản ghi Công ty CAVI/AVI luôn (0003_deactivate_cavi_avi trước đây chỉ tắt
# is_active, chưa xoá). Riêng Bảng giá dịch vụ (crm.PriceListItem) là bảng giá cho nghiệp vụ VẬN
# CHUYỂN của CAVI — LIVI làm THƯƠNG MẠI, không dùng loại bảng giá này trong quy trình hỏi giá
# (crm/serializers.py: company.business_type quyết định dùng "product" hay "item") — nên xoá hẳn
# thay vì chuyển sang LIVI để khỏi để lại dữ liệu không bao giờ dùng tới.
#
# Không thể hoàn tác: đã xoá dữ liệu (bảng giá) và xoá hẳn bản ghi Công ty CAVI/AVI.

from django.db import migrations

# (app_label, model_name, field_name) — mọi model có ForeignKey thẳng tới Company, TRỪ
# PriceListItem (xử lý riêng ở trên).
COMPANY_FK_MODELS = [
    ("crm", "TierUpgradeRequest", "company"),
    ("crm", "Order", "company"),
    ("crm", "Activity", "company"),
    ("crm", "PriceInquiry", "company"),
    ("crm", "Task", "company"),
    ("crm", "KPITarget", "company"),
    ("crm", "Notice", "company"),
    ("approvals", "ApprovalRequest", "company"),
    ("ops", "ShipmentBatch", "company"),
    ("ops", "Shipment", "company"),
    ("inventory", "Warehouse", "company"),
    ("inventory", "Product", "company"),
]

# (app_label, model_name, field_name) — mọi model có ManyToManyField tới Company.
COMPANY_M2M_MODELS = [
    ("crm", "Partner", "companies"),
    ("hr", "Profile", "companies"),
]


def merge_cavi_avi_into_livi(apps, schema_editor):
    Company = apps.get_model("companies", "Company")
    PriceListItem = apps.get_model("crm", "PriceListItem")

    try:
        livi = Company.objects.get(code="LIVI")
    except Company.DoesNotExist:
        return  # môi trường chưa seed công ty (vd test riêng) — không có gì để gộp

    retired = list(Company.objects.filter(code__in=["CAVI", "AVI"]))
    if not retired:
        return

    PriceListItem.objects.filter(company__in=retired).delete()

    for app_label, model_name, field_name in COMPANY_FK_MODELS:
        Model = apps.get_model(app_label, model_name)
        Model.objects.filter(**{f"{field_name}__in": retired}).update(**{field_name: livi})

    for app_label, model_name, field_name in COMPANY_M2M_MODELS:
        Model = apps.get_model(app_label, model_name)
        for obj in Model.objects.filter(**{f"{field_name}__in": retired}).distinct():
            rel = getattr(obj, field_name)
            rel.add(livi)
            rel.remove(*retired)

    Company.objects.filter(pk__in=[c.pk for c in retired]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0003_deactivate_cavi_avi"),
        ("crm", "0036_partner_companies"),
        ("hr", "0012_add_companies_m2m"),
        ("approvals", "0005_alter_approvalrequest_company"),
        ("ops", "0004_alter_shipment_company_alter_shipmentbatch_company"),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(merge_cavi_avi_into_livi, migrations.RunPython.noop),
    ]
