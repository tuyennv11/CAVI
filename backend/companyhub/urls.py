from django.urls import path
from . import views
from .fund_views import Funds

urlpatterns = [
    path("", views.Overview.as_view()),
    path("employees/", views.Employees.as_view()),
    path("employees/<int:pk>/", views.EmployeeDetail.as_view()),
    path("payroll/", views.Payroll.as_view()),
    path("payroll/<int:pk>/", views.PayrollDetail.as_view()),
    path("sources/<int:pk>/", views.SourceDetail.as_view()),
    path("fund-calculate/", views.FundCalculate.as_view()),
    path("funds/", Funds.as_view()),
]
