from django.urls import path,include
from .views import HomeView,  login_view, logout_view
from dossier_medicale import views

urlpatterns =[
    path('', include('dossier_medicale.urls')),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
   
]

