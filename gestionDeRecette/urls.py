from .admin import admin

from django.conf import settings
from django.conf.urls.static import static

from django.urls import path, include



api_urlpattern = [
    path("api/typeRecette/", include("typeRecette.api_urls")),
    path("api/recette/", include("recette.api_urls")),
    path("api/tag/", include("tag.api_urls")),
    
    # path("api/login/", MyLogin.as_view(), name="token_obtain_pair"),
    # path("api/token/refresh/", MyTokenRefreshView.as_view(), name="token_refresh"),
    # path("api/token/verify/", MyTokenVerifyView.as_view(), name="token_verify"),
]




urlpatterns = (
    api_urlpattern
    + [
        path("admin/", admin.site.urls),
        # path("swagger/",schema_view.with_ui("swagger", cache_timeout=0),name="schema-swagger-ui",),
        # path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
        # path("", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    ]
    
)+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)