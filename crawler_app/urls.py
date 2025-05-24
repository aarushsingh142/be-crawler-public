from django.urls import path
from . import views

urlpatterns = [
    path('', views.crawl_dashboard, name='crawl_dashboard'),
    path('request-crawl/', views.request_crawl, name='request_crawl'),
    path('view-data/<int:request_id>/', views.view_crawled_data, name='view_crawled_data'),
]
