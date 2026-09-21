from decimal import Decimal

from django.test import TestCase

from companies.models import Company

from .models import InventoryReservation, Product, StockMovement, Warehouse


class AvailableStockTests(TestCase):
    """Test 1/2 mục 31 tài liệu nghiệp vụ — tồn khả dụng phải tách khỏi tồn thực tế."""

    def setUp(self):
        self.company = Company.objects.create(code="INV-TEST", name="Synthetic inventory co", business_type="trading")
        self.warehouse = Warehouse.objects.create(company=self.company, name="Synthetic warehouse")
        self.product = Product.objects.create(company=self.company, sku="INV-SKU", name="Synthetic product")

    def test_available_stock_equals_on_hand_without_reservation(self):
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, movement_type="in", quantity=Decimal("10000")
        )
        self.assertEqual(self.product.stock_on_hand(), Decimal("10000"))
        self.assertEqual(self.product.available_stock(), Decimal("10000"))

    def test_reservation_reduces_available_but_not_on_hand(self):
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, movement_type="in", quantity=Decimal("10000")
        )
        InventoryReservation.objects.create(
            product=self.product, warehouse=self.warehouse, quantity=Decimal("2000"), status="active"
        )
        self.assertEqual(self.product.stock_on_hand(), Decimal("10000"))
        self.assertEqual(self.product.available_stock(), Decimal("8000"))

    def test_released_reservation_no_longer_counts(self):
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, movement_type="in", quantity=Decimal("10000")
        )
        InventoryReservation.objects.create(
            product=self.product, warehouse=self.warehouse, quantity=Decimal("2000"), status="released"
        )
        self.assertEqual(self.product.available_stock(), Decimal("10000"))

    def test_adjustment_up_and_down_move_stock_correctly(self):
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, movement_type="adjustment_up", quantity=Decimal("500")
        )
        self.assertEqual(self.product.stock_on_hand(), Decimal("500"))
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, movement_type="adjustment_down", quantity=Decimal("100")
        )
        self.assertEqual(self.product.stock_on_hand(), Decimal("400"))
