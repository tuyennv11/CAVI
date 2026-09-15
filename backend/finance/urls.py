from rest_framework.routers import DefaultRouter

from .views import OrderCostViewSet, OrderDocumentViewSet, OrderFinanceViewSet, OrderPaymentViewSet


router = DefaultRouter()
router.register("orders", OrderFinanceViewSet, basename="order-finance")
router.register("costs", OrderCostViewSet, basename="order-cost")
router.register("payments", OrderPaymentViewSet, basename="order-payment")
router.register("documents", OrderDocumentViewSet, basename="order-document")

urlpatterns = router.urls
