from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.urls import re_path
from django.views.static import serve

urlpatterns = [
    path("api/", include("voice.urls")),
]
# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# MEDIA_ROOTを公開する(アクセス可能にする)　
urlpatterns += static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)

# DEBUG=FalseでもMEDIA_ROOTを見える様にする
urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT, }), ]
