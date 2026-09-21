# Dữ liệu "adjustment" cũ (quantity có thể âm/dương, dấu thể hiện chiều) được tách thành
# "adjustment_up"/"adjustment_down" (quantity luôn dương, chiều suy từ loại — đúng quy ước mới, xem
# StockMovement.MovementType.decreasing_types()).

from django.db import migrations


def forwards(apps, schema_editor):
    StockMovement = apps.get_model("inventory", "StockMovement")
    for movement in StockMovement.objects.filter(movement_type="adjustment"):
        if movement.quantity < 0:
            movement.movement_type = "adjustment_down"
            movement.quantity = -movement.quantity
        else:
            movement.movement_type = "adjustment_up"
        movement.save(update_fields=["movement_type", "quantity"])


def backwards(apps, schema_editor):
    StockMovement = apps.get_model("inventory", "StockMovement")
    for movement in StockMovement.objects.filter(movement_type="adjustment_down"):
        movement.movement_type = "adjustment"
        movement.quantity = -movement.quantity
        movement.save(update_fields=["movement_type", "quantity"])
    StockMovement.objects.filter(movement_type="adjustment_up").update(movement_type="adjustment")


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_alter_stockmovement_movement_type_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
