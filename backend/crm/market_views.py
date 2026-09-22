from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.roles import is_manager, is_supply
from companies.mixins import CompanyScopedMixin
from .models import CostQuote, FreightOffer, PriceRequestItem, SourcingPlan
from .serializers import CostQuoteSerializer
from .market_serializers import FreightOfferSerializer, SourcingPlanSerializer
from .services.sourcing import delivery_address, live, plan_snapshot, readiness


class MarketScope(CompanyScopedMixin):
    permission_classes = [IsAuthenticated]

    def visible_items(self):
        qs = PriceRequestItem.objects.filter(price_request__company=self.get_active_company())
        if not (is_manager(self.request.user) or is_supply(self.request.user)):
            qs = qs.filter(price_request__assigned_to=self.request.user.profile)
        return qs

    def require_supply(self):
        if not (is_manager(self.request.user) or is_supply(self.request.user)):
            raise PermissionDenied("Chỉ Cung ứng/Quản lý được báo giá.")

    def require_owner(self, obj):
        self.require_supply()
        if not is_manager(self.request.user) and obj.created_by_id != self.request.user.id:
            raise PermissionDenied("Chỉ cập nhật/rút giá của chính mình.")


class CostQuoteViewSet(MarketScope, mixins.CreateModelMixin, mixins.ListModelMixin,
                       mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = CostQuoteSerializer
    filterset_fields = ["price_request_item"]

    def get_queryset(self):
        return CostQuote.objects.filter(price_request_item__in=self.visible_items()).select_related(
            "price_request_item__price_request", "created_by", "country", "province", "district", "ward"
        ).prefetch_related("items", "freight_offers__created_by")

    @transaction.atomic
    def perform_create(self, serializer):
        self.require_supply()
        item = self.visible_items().select_for_update().filter(pk=serializer.validated_data["price_request_item"].id).first()
        if item is None:
            raise PermissionDenied("Yêu cầu giá không thuộc công ty đang chọn.")
        old = serializer.validated_data.get("supersedes")
        if old:
            old = CostQuote.objects.select_for_update().filter(pk=old.pk, price_request_item=item).first()
            if old is None or old.price_request_item_id != item.id:
                raise ValidationError("Phiên bản gốc không thuộc yêu cầu này.")
            self.require_owner(old)
            if not old.active or hasattr(old, "next_version"):
                raise ValidationError("Giá gốc đã được thay thế hoặc rút.")
            if old.sourcing_plans.filter(status="approved").exists():
                raise ValidationError("Giá đã chốt được giữ nguyên. Hãy thêm phương án độc lập.")
            old.active = False
            old.save(update_fields=["active"])
        serializer.save(created_by=self.request.user, delivery_snapshot=delivery_address(item))

    @action(detail=True, methods=["post"], url_path="bid-goods")
    @transaction.atomic
    def bid_goods(self, request, pk=None):
        self.require_supply()
        source = self.get_object()
        PriceRequestItem.objects.select_for_update().get(pk=source.price_request_item_id)
        source.refresh_from_db()
        if not live(source):
            raise ValidationError("Phương án đã hết hiệu lực hoặc đã rút.")
        if source.delivery_snapshot != delivery_address(source.price_request_item):
            raise ValidationError("Điểm giao đã thay đổi. Hãy tạo phương án mới.")
        prices = request.data.get("prices")
        rows = list(source.items.all())
        if not isinstance(prices, list) or len(prices) != len(rows):
            raise ValidationError("Cần đơn giá cho từng mặt hàng trong phương án.")
        data = {name: getattr(source, name) for name in [
            "street_address", "available_at", "tax_basis", "payment_terms", "delivery_terms"]}
        data.update({name: getattr(source, name + "_id") for name in ["country", "province", "district", "ward"]})
        data.update(price_request_item=source.price_request_item_id,
                    supplier_name=request.data.get("supplier_name", ""),
                    confirmed=request.data.get("confirmed", False),
                    valid_until=request.data.get("valid_until"),
                    shipping_rate=None, carrier_name="",
                    note="Báo giá hàng cùng phương án #" + str(source.id),
                    items=[{**{name: getattr(row, name) for name in [
                        "item_name", "quantity", "unit", "unit_length_cm", "unit_width_cm", "unit_height_cm", "unit_weight_kg"]},
                        "unit_cost": price} for row, price in zip(rows, prices)])
        if any(price is None or price == "" for price in prices):
            raise ValidationError("Nhập đủ đơn giá hàng.")
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user, delivery_snapshot=source.delivery_snapshot, based_on_id=source.based_on_id or source.id)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def withdraw(self, request, pk=None):
        quote = self.get_object()
        PriceRequestItem.objects.select_for_update().get(pk=quote.price_request_item_id)
        quote.refresh_from_db()
        self.require_owner(quote)
        if quote.sourcing_plans.filter(status="approved").exists():
            raise ValidationError("Không thể rút giá đã chốt.")
        quote.active = False
        quote.save(update_fields=["active"])
        return Response(self.get_serializer(quote).data)


class FreightOfferViewSet(MarketScope, mixins.CreateModelMixin, mixins.ListModelMixin,
                         mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = FreightOfferSerializer
    filterset_fields = ["goods_quote"]

    def get_queryset(self):
        return FreightOffer.objects.filter(goods_quote__price_request_item__in=self.visible_items()).select_related("goods_quote", "created_by")

    @transaction.atomic
    def perform_create(self, serializer):
        self.require_supply()
        quote = serializer.validated_data["goods_quote"]
        item = self.visible_items().select_for_update().filter(pk=quote.price_request_item_id).first()
        if item is None:
            raise PermissionDenied("Nguồn hàng không thuộc công ty đang chọn.")
        quote.refresh_from_db()
        if not live(quote):
            raise ValidationError("Nguồn hàng đã hết hiệu lực hoặc đã rút.")
        old = serializer.validated_data.get("supersedes")
        if old:
            old = FreightOffer.objects.select_for_update().filter(pk=old.pk, goods_quote=quote).first()
            if old is None or old.goods_quote_id != quote.id:
                raise ValidationError("Cước gốc không thuộc nguồn hàng này.")
            self.require_owner(old)
            if not old.active or hasattr(old, "next_version") or old.sourcing_plans.filter(status="approved").exists():
                raise ValidationError("Cước đã thay thế, đã rút hoặc đã chốt.")
            old.active = False
            old.save(update_fields=["active"])
        serializer.save(created_by=self.request.user, delivery_snapshot=delivery_address(item))

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def withdraw(self, request, pk=None):
        offer = self.get_object()
        PriceRequestItem.objects.select_for_update().get(pk=offer.goods_quote.price_request_item_id)
        self.require_owner(offer)
        if offer.sourcing_plans.filter(status="approved").exists():
            raise ValidationError("Không thể rút cước đã chốt.")
        offer.active = False
        offer.save(update_fields=["active"])
        return Response(self.get_serializer(offer).data)


class SourcingPlanViewSet(MarketScope, mixins.CreateModelMixin, mixins.ListModelMixin,
                         mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = SourcingPlanSerializer
    filterset_fields = ["price_request_item"]

    def get_queryset(self):
        return SourcingPlan.objects.filter(price_request_item__in=self.visible_items()).select_related("created_by", "reviewed_by")

    @transaction.atomic
    def perform_create(self, serializer):
        data = serializer.validated_data
        item = self.visible_items().select_for_update().filter(pk=data["price_request_item"].id).first()
        if item is None:
            raise PermissionDenied("Không có quyền với yêu cầu này.")
        quote = data["goods_quote"]
        freight = data.get("freight_offer")
        quote.refresh_from_db()
        if freight:
            freight.refresh_from_db()
        if quote.price_request_item_id != item.id or (freight and freight.goods_quote_id != quote.id):
            raise ValidationError("Không thể ghép nguồn hàng/cước khác yêu cầu hoặc khác điểm lấy hàng.")
        if item.sourcing_plans.filter(status="approved").exists():
            raise ValidationError("Yêu cầu đã chốt; báo giá mới không thay phương án đã duyệt.")
        if not data.get("reason", "").strip():
            raise ValidationError("Cần lý do đề xuất phương án.")
        issues = readiness(quote, freight)
        if issues:
            raise ValidationError({"detail": "; ".join(issues)})
        serializer.save(created_by=self.request.user, snapshot=plan_snapshot(quote, freight))

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý được duyệt chốt.")
        plan = self.get_object()
        item = self.visible_items().select_for_update().get(pk=plan.price_request_item_id)
        plan.refresh_from_db()
        if plan.status != "proposed" or item.sourcing_plans.filter(status="approved").exists():
            raise ValidationError("Phương án không còn chờ duyệt hoặc yêu cầu đã chốt.")
        issues = readiness(plan.goods_quote, plan.freight_offer)
        if issues:
            raise ValidationError({"detail": "; ".join(issues)})
        plan.snapshot = plan_snapshot(plan.goods_quote, plan.freight_offer)
        plan.status, plan.reviewed_by, plan.reviewed_at = "approved", request.user, timezone.now()
        plan.save()
        item.sourcing_plans.filter(status="proposed").exclude(pk=plan.pk).update(status="rejected", reviewed_by=request.user, reviewed_at=timezone.now())
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Chỉ Quản lý được từ chối đề xuất.")
        plan = self.get_object()
        PriceRequestItem.objects.select_for_update().get(pk=plan.price_request_item_id)
        plan.refresh_from_db()
        if plan.status != "proposed":
            raise ValidationError("Phương án không còn chờ duyệt.")
        plan.status, plan.reviewed_by, plan.reviewed_at = "rejected", request.user, timezone.now()
        plan.save()
        return Response(self.get_serializer(plan).data)
