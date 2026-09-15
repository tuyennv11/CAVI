from django.urls import path

from .views import InboxView, MarkReadView, NotificationDetailView

urlpatterns = [
    path("", InboxView.as_view()),
    path("read/", MarkReadView.as_view()),
    path("<int:pk>/", NotificationDetailView.as_view()),
]
