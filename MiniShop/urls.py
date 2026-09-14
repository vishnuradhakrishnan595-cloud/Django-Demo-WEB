from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    # Django built-in admin
    path(
        "django-admin/",
        admin.site.urls
    ),

    # Guest
    path(
        "",
        include("Guest.urls")
    ),

    # User
    path(
        "user/",
        include("User.urls")
    ),

    # Shop / Admin
    path(
        "shop/",
        include("Shop.urls")
    ),

    
    # Google / Allauth
    path('accounts/', include('allauth.urls')),
]


# Media files
if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )