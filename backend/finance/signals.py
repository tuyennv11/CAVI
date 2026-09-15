from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver

from crm.models import Order

from .models import OrderFinance, next_monday_noon


@receiver(post_save, sender=Order)
def ensure_order_finance(sender, instance, created, **kwargs):
    finance, _ = OrderFinance.objects.get_or_create(order=instance)
    if instance.status == Order.Status.DONE and finance.completed_at is None:
        completed_at = instance.updated_at
        finance.completed_at = completed_at
        finance.settlement_due_at = next_monday_noon(completed_at)
        finance.payment_due_at = completed_at + timedelta(days=finance.credit_terms_days)
        finance.save(update_fields=["completed_at", "settlement_due_at", "payment_due_at", "updated_at"])
