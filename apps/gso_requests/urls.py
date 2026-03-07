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
]
