from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityViewSet,
    DashboardStatsView,
    NoticeViewSet,
    OrderViewSet,
    PartnerViewSet,
    PriceInquiryQuoteLineBidViewSet,
    PriceInquiryQuoteLineViewSet,
    PriceRequestItemViewSet,
    PriceRequestViewSet,
    PriceListItemViewSet,
    PurchaseRequestItemViewSet,
    QuotationViewSet,
    SupplierQuoteViewSet,
    TaskViewSet,
)
from .workspace_views import WorkspaceKPIView, WorkspaceRankingView, WorkspaceTodayView

router = DefaultRouter()
router.register("partners", PartnerViewSet, basename="partner")
router.register("orders", OrderViewSet, basename="order")
router.register("activities", ActivityViewSet, basename="activity")
router.register("tasks", TaskViewSet, basename="task")
router.register("price-inquiries", PriceRequestViewSet, basename="price-inquiry")
router.register("price-inquiry-items", PriceRequestItemViewSet, basename="price-inquiry-item")
router.register("purchase-request-items", PurchaseRequestItemViewSet, basename="purchase-request-item")
router.register("supplier-quotes", SupplierQuoteViewSet, basename="supplier-quote")
router.register("quote-lines", PriceInquiryQuoteLineViewSet, basename="quote-line")
router.register("quote-line-bids", PriceInquiryQuoteLineBidViewSet, basename="quote-line-bid")
router.register("quotations", QuotationViewSet, basename="quotation")
router.register("price-list-items", PriceListItemViewSet, basename="price-list-item")
router.register("notices", NoticeViewSet, basename="notice")

urlpatterns = [
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("workspace/today/", WorkspaceTodayView.as_view(), name="workspace-today"),
    path("workspace/kpi/", WorkspaceKPIView.as_view(), name="workspace-kpi"),
    path("workspace/ranking/", WorkspaceRankingView.as_view(), name="workspace-ranking"),
] + router.urls
