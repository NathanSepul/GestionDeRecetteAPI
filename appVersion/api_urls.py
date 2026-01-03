
from django.urls import path

import appVersion.api_views 


urlpatterns = [
    path("<str:support>/download", appVersion.api_views.DownloadAPIView.as_view()),
    path('<str:support>/currentVersion', appVersion.api_views.AppVersionSupportAPIView.as_view()),
]