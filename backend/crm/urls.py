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
    PriceInquiryViewSet,
    PriceListItemViewSet,
    QuotationViewSet,
    TaskViewSet,
    TierUpgradeRequestViewSet,
)
from .workspace_views import WorkspaceKPIView, WorkspaceRankingView, WorkspaceTodayView

router = DefaultRouter()
router.register("partners", PartnerViewSet, basename="partner")
router.register("orders", OrderViewSet, basename="order")
router.register("activities", ActivityViewSet, basename="activity")
router.register("tasks", TaskViewSet, basename="task")
router.register("price-inquiries", PriceInquiryViewSet, basename="price-inquiry")
router.register("quote-lines", PriceInquiryQuoteLineViewSet, basename="quote-line")
router.register("quote-line-bids", PriceInquiryQuoteLineBidViewSet, basename="quote-line-bid")
router.register("quotations", QuotationViewSet, basename="quotation")
router.register("price-list-items", PriceListItemViewSet, basename="price-list-item")
router.register("tier-requests", TierUpgradeRequestViewSet, basename="tier-request")
router.register("notices", NoticeViewSet, basename="notice")

urlpatterns = [
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("workspace/today/", WorkspaceTodayView.as_view(), name="workspace-today"),
    path("workspace/kpi/", WorkspaceKPIView.as_view(), name="workspace-kpi"),
    path("workspace/ranking/", WorkspaceRankingView.as_view(), name="workspace-ranking"),
] + router.urls
