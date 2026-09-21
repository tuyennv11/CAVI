from rest_framework.routers import DefaultRouter

from .views import ProductImageViewSet, ProductViewSet, StockMovementViewSet, WarehouseViewSet

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("products", ProductViewSet, basename="product")
router.register("product-images", ProductImageViewSet, basename="product-image")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")

urlpatterns = router.urls
