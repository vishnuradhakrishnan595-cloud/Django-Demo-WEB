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
    # OTP VERIFICATION
    # =====================================================

    path(
        "verify-otp/",
        views.verify_otp,
        name="verify_otp"
    ),

    path(
        "resend-otp/",
        views.resend_otp,
        name="resend_otp"
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