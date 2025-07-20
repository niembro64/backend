"""
URL configuration for foreclosure API endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('test/', views.test_view, name='test_view'),
    path('test-external/', views.test_external_request, name='test_external_request'),
    path('test-browser/', views.test_browser_automation, name='test_browser_automation'),
    path('cities/', views.get_city_list, name='get_city_list'),
    path('posting-ids/', views.get_posting_ids, name='get_posting_ids'),
    path('auction-details/', views.get_auction_details, name='get_auction_details'),
    path(
        'batch-auction-details/',
        views.get_batch_auction_details,
        name='get_batch_auction_details'
    ),
]