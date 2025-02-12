from django.conf.urls import url

from activity.views.training import *

urlpatterns = [
    url(r'thamatic/list/$', ThematicAreaListView.as_view(), name='thematic_list'),
    url(r'thamatic/create/$',  ThematicAreaCreateView.as_view(), name='thamatic_create'),
    url(r'thamatic/(?P<pk>[\w]+)/$', ThematicAreaUpdateView.as_view(), name='thamatic_edit'),
    url(r'training/session/(?P<pk>[\w]+)/$', TrainingSessionDetailView.as_view(), name='detail_list'),
    url(r'training/session/$', TrainingSessionListView.as_view(), name='training_list'),
    url(r'training/create/$', TrainingCreateView.as_view(), name='training_create'),
    url(r'external/create/$', ExternalTrainerCreateView.as_view(), name='external_create'),

    url(r'training/topic/list/(?P<thematic>[\w]+)/$', TrainingContentListView.as_view(), name='training_content_list'),
    url(r'training/topic/create/(?P<thematic>[\w]+)/$', TrainingContentCreateView.as_view(), name='training_coontent_create'),
    url(r'training/topic/create/(?P<thematic>[\w]+)/update/(?P<pk>[\w]+)/$', TrainingContentUpdateView.as_view(), name='training_coontent_update'),
]