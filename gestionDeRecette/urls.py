from .admin import admin
from gestionDeRecette.api_views import MyLogin, MyTokenRefreshView, MyTokenVerifyView
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.contrib.auth.decorators import login_required

api_urlpattern = [
    path("api/typeRecette/", include("typeRecette.api_urls")),
    path("api/recette/", include("recette.api_urls")),
    path("api/tag/", include("tag.api_urls")),
    path("api/user/", include("user.api_urls")),
    
    path("api/login/", MyLogin.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", MyTokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", MyTokenVerifyView.as_view(), name="token_verify"),
]




urlpatterns = (
    api_urlpattern
    + [
       path("admin/", admin.site.urls),
        
        # path('schema/', SpectacularAPIView.as_view(), name='schema'),
        # path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    ]
)+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)