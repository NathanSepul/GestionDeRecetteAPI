from .admin import admin
from gestionDeRecette.api_views import MyLogin, MyTokenRefreshView, MyTokenVerifyView, serve_image
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_urlpattern = [
    path("api/typeRecette/", include("typeRecette.api_urls")),
    path("api/recette/", include("recette.api_urls")),
    path("api/tag/", include("tag.api_urls")),
    path("api/user/", include("user.api_urls")),
    path("api/appVersion/", include("appVersion.api_urls")),
    
    path("api/login/", MyLogin.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", MyTokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", MyTokenVerifyView.as_view(), name="token_verify"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

urlpatterns += api_urlpattern

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_image, name='serve_image'),
    ]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)