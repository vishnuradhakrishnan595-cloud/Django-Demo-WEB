from django.urls import path
from . import views


urlpatterns = [

    # =====================================================
    # HOME
    # =====================================================

    path(
        "",
        views.index,
        name="index"
    ),

    # =====================================================
    # REGISTRATION
    # =====================================================

    path(
        "register/",
        views.register,
        name="register"
    ),

   
    # =====================================================
    # LOGIN / LOGOUT
    # =====================================================

    path(
        "login/",
        views.login,
        name="login"
    ),

    path(
        "logout/",
        views.logout,
        name="logout"
    ),
]