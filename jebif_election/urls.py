from django.urls import path
from django.views.generic import TemplateView
from jebif_election.views import *

urlpatterns = [
    path('election/<int:election_id>/vote/', vote_view, name='vote'),
    path('election/<int:election_id>/vote_ok/', TemplateView.as_view(template_name="jebif_election/vote_ok.html"), name='vote_ok'),
    path('election/<int:election_id>/vote_closed/', TemplateView.as_view(template_name="jebif_election/vote_closed.html"), name='vote_closed'),
    path('election/<int:election_id>/vote_already_done/', TemplateView.as_view(template_name="jebif_election/vote_already_done.html"), name='vote_already_done'),
    path('list_elections/', list_elections_view, name='list_elections'),
    path('election/candidate/', candidate_to_election_view, name='candidate_to_election'),
    path('election/list_results/', list_result_view, name='list_results'),
    path('election/<int:election_id>/results/', result_view, name='results'),

]