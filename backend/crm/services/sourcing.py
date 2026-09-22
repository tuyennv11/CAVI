"""Shared calculations for the sourcing board. Missing costs are never zero-priced offers."""
import hashlib
import json
from decimal import Decimal

from django.utils import timezone


def delivery_address(item):
    pr = item.price_request
    return ", ".join(str(value) for value in [
        pr.street_address, pr.ward.name if pr.ward else None,
        pr.district.name if pr.district else None, pr.province.name if pr.province else None,
        pr.country.name if pr.country else None,
    ] if value)


def pickup_address(quote):
    return ", ".join(str(value) for value in [quote.street_address,
        quote.ward.name if quote.ward else None, quote.district.name if quote.district else None,
        quote.province.name if quote.province else None, quote.country.name if quote.country else None] if value)


def live(offer):
    return offer.active and (offer.valid_until is None or offer.valid_until >= timezone.localdate())


def goods_total(quote):
    rows = list(quote.items.all())
    if not rows or any(row.quantity is None or row.quantity <= 0 or row.unit_cost is None or row.unit_cost < 0 for row in rows):
        return None
    return sum((row.total_cost for row in rows), Decimal("0"))


def freight_total(quote, rate, basis):
    if rate is None or rate < 0:
        return None
    if basis == "total":
        return rate
    values = [row.total_weight_kg if basis == "kg" else row.total_volume_m3 for row in quote.items.all()]
    if not values or any(value is None or value <= 0 for value in values):
        return None
    return rate * sum(values, Decimal("0"))


def comparison_key(quote):
    # Different baskets, specifications, units or terms must not share a cheapest badge.
    if goods_total(quote) is None or quote.tax_basis != "included":
        return None
    rows = []
    for row in quote.items.all():
        if not row.item_name.strip() or not row.unit.strip():
            return None
        rows.append([row.item_name.strip().casefold(), row.unit.strip().casefold(),
            *[str(value.normalize()) if value is not None else None for value in [row.quantity,
                row.unit_length_cm, row.unit_width_cm, row.unit_height_cm, row.unit_weight_kg]]])
    payload = [sorted(rows, key=lambda row: json.dumps(row)), quote.tax_basis,
               quote.delivery_terms.strip().casefold(), quote.payment_terms.strip().casefold(),
               pickup_address(quote).strip().casefold(), quote.delivery_snapshot.strip().casefold(),
               str(quote.available_at), quote.price_request_item_id]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def readiness(quote, freight=None):
    problems = []
    if not live(quote):
        problems.append("Giá hàng đã hết hiệu lực hoặc đã rút")
    if not quote.confirmed or not quote.supplier_name.strip() or not quote.valid_until:
        problems.append("Giá hàng cần NCC xác nhận, tên NCC và hạn hiệu lực")
    if goods_total(quote) is None:
        problems.append("Thiếu số lượng hoặc giá hàng")
    if quote.tax_basis != "included":
        problems.append("Giá hàng chưa xác nhận đã gồm thuế")
    if not pickup_address(quote) or not delivery_address(quote.price_request_item):
        problems.append("Thiếu điểm nhận hoặc điểm giao")
    if not quote.delivery_snapshot or quote.delivery_snapshot != delivery_address(quote.price_request_item):
        problems.append("Điểm giao đã đổi hoặc chưa xác nhận; cần báo lại giá hàng")
    if not quote.available_at or not quote.payment_terms.strip() or not quote.delivery_terms.strip():
        problems.append("Thiếu ngày có hàng hoặc điều kiện thanh toán/giao nhận")
    if freight:
        if freight.goods_quote_id != quote.id:
            problems.append("Cước không thuộc phương án hàng này")
        if not live(freight) or not freight.confirmed or not freight.valid_until:
            problems.append("Cước chưa xác nhận hoặc hết hiệu lực")
        if freight.tax_basis != "included":
            problems.append("Cước chưa xác nhận đã gồm thuế")
        if freight.delivery_snapshot != delivery_address(quote.price_request_item):
            problems.append("Điểm giao đã thay đổi; cần báo lại cước")
        if freight.delivery_days is None or not freight.terms.strip():
            problems.append("Thiếu thời gian giao hoặc phạm vi dịch vụ vận chuyển")
        shipping = freight_total(quote, freight.rate, freight.basis)
    else:
        if not quote.carrier_name.strip():
            problems.append("Chưa có đơn vị vận chuyển cho cước kèm theo")
        shipping = freight_total(quote, quote.shipping_rate, quote.shipping_rate_basis)
    if shipping is None:
        problems.append("Chưa đủ cước hoặc trọng lượng/thể tích để tính cước")
    return problems


def plan_snapshot(quote, freight=None):
    shipping = freight_total(quote, freight.rate, freight.basis) if freight else freight_total(quote, quote.shipping_rate, quote.shipping_rate_basis)
    goods = goods_total(quote)
    return {"supplier": quote.supplier_name, "carrier": freight.carrier_name if freight else quote.carrier_name,
        "pickup": pickup_address(quote), "delivery": delivery_address(quote.price_request_item),
        "goods_total": str(goods), "shipping_total": str(shipping), "landed_total": str(goods + shipping),
        "tax_basis": "included", "payment_terms": quote.payment_terms,
        "delivery_terms": quote.delivery_terms, "freight_terms": freight.terms if freight else quote.delivery_terms}
