from django.urls import path

from website import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy-policy'),
    path('contact/', views.ContactView.as_view(), name='contact'),
]