from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import ContactLog, Customer, Order, OrderItem

User = get_user_model()


class AssignedToSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class ContactLogSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = ContactLog
        fields = ["id", "customer", "note", "created_by", "created_by_name", "created_at"]
        read_only_fields = ["created_by", "created_at"]


class CustomerSerializer(serializers.ModelSerializer):
    assigned_to_detail = AssignedToSerializer(source="assigned_to", read_only=True)
    contact_count = serializers.IntegerField(source="contact_logs.count", read_only=True)
    order_count = serializers.IntegerField(source="orders.count", read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "company",
            "phone",
            "email",
            "address",
            "assigned_to",
            "assigned_to_detail",
            "contact_count",
            "order_count",
            "created_at",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "description", "quantity", "unit_price", "line_total"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "customer_name",
            "status",
            "note",
            "items",
            "total",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)
        OrderItem.objects.bulk_create(OrderItem(order=order, **item) for item in items_data)
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            OrderItem.objects.bulk_create(OrderItem(order=instance, **item) for item in items_data)
        return instance
