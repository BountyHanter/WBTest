from django.urls import path, include

from stats.views.image import TestImageListCreateView, TestImageDetailView, TestImageReorderView
from stats.views.test import TestListCreateView, TestDetailView, TestCreateWithImagesView
from stats.views.test_action import TestStartView, TestPauseView, TestResumeView
from stats.views.wb_token import WBTokenListCreateView, WBTokenDetailView

urlpatterns = [
    path("wb-tokens/", WBTokenListCreateView.as_view(), name="wb-token-list"),
    path("wb-tokens/<int:pk>/", WBTokenDetailView.as_view(), name="wb-token-detail"),
    path("tests/", include([
        path("", TestListCreateView.as_view(), name="test-list"),
        path("full", TestCreateWithImagesView.as_view(), name="test-full-create"),
        path("<int:pk>/", TestDetailView.as_view(), name="test-detail"),

        path("<int:pk>/start/", TestStartView.as_view(), name="test-start"),
        path("<int:pk>/pause/", TestPauseView.as_view(), name="test-pause"),
        path("<int:pk>/resume/", TestResumeView.as_view(), name="test-resume"),

        path("<int:test_id>/images/", TestImageListCreateView.as_view(), name="image-list"),
        path("<int:test_id>/images/<int:image_id>/", TestImageDetailView.as_view(), name="image-detail"),
        path("<int:test_id>/images/reorder/", TestImageReorderView.as_view(), name="image-reorder"),

    ])),
]