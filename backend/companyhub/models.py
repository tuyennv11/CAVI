from django.db import models


class SourceSnapshot(models.Model):
    """Immutable import version. Never a live Google credential or public media file."""
    source_id = models.CharField(max_length=120)
    digest = models.CharField(max_length=64)
    title = models.CharField(max_length=300)
    account = models.CharField(max_length=150)
    category = models.CharField(max_length=30)
    period = models.CharField(max_length=30, blank=True)
    content = models.JSONField(default=dict)
    issues = models.JSONField(default=list)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source_id", "digest"], name="hub_source_version")]


class EmployeeMaster(models.Model):
    """Source roster, independent of login accounts and unverified company mappings."""
    source = models.ForeignKey(SourceSnapshot, on_delete=models.PROTECT, related_name="employees")
    source_row = models.PositiveIntegerField()
    code = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=200)
    source_company = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=150, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    # A blank source marker is NOT automatically a resignation.
    status = models.CharField(max_length=30, default="unconfirmed")
    fields = models.JSONField(default=list)
    issues = models.JSONField(default=list)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "source_row"], name="hub_employee_source_row")]


class PayrollRecord(models.Model):
    source = models.ForeignKey(SourceSnapshot, on_delete=models.PROTECT, related_name="payroll")
    source_row = models.PositiveIntegerField()
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    department = models.CharField(max_length=150, blank=True)
    cells = models.JSONField(default=dict)
    issues = models.JSONField(default=list)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "source_row"], name="hub_payroll_source_row")]
