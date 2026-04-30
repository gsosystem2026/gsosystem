from django.urls import path
from . import views

app_name = 'gso_requests'

urlpatterns = [
    path('new/', views.RequestCreateView.as_view(), name='requestor_request_new'),
    path('<int:pk>/', views.RequestDetailView.as_view(), name='requestor_request_detail'),
    path('<int:pk>/attachment/', views.RequestAttachmentView.as_view(), name='request_attachment'),
    path('<int:pk>/edit/', views.RequestEditView.as_view(), name='requestor_request_edit'),
    path('<int:pk>/cancel/', views.RequestCancelView.as_view(), name='requestor_request_cancel'),
    path('<int:pk>/feedback/', views.SubmitFeedbackView.as_view(), name='requestor_request_feedback'),
    path('export/csv/', views.RequestorRequestExportCsvView.as_view(), name='requestor_request_export_csv'),

    # Motorpool printing + saving (Unit Head / assigned personnel)
    path('<int:pk>/motorpool/update/', views.MotorpoolTripUpdateView.as_view(), name='motorpool_trip_update'),
    path('<int:pk>/motorpool/print-request/', views.MotorpoolPrintRequestView.as_view(), name='motorpool_print_request'),
    path('<int:pk>/motorpool/print-trip-ticket/', views.MotorpoolPrintTripTicketView.as_view(), name='motorpool_print_trip_ticket'),
]
