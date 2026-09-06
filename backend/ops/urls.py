from rest_framework.routers import DefaultRouter

from .views import ShipmentBatchViewSet, ShipmentViewSet

router = DefaultRouter()
router.register("shipments", ShipmentViewSet, basename="shipment")
router.register("shipment-batches", ShipmentBatchViewSet, basename="shipment-batch")

urlpatterns = router.urls
