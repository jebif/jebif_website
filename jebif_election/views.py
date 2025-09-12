from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages

from jebif_election.models import Election, Vote
from jebif_election.forms import NewVoteForm #, MailingForm

import datetime

def vote_view(request, election_id):
    el = get_object_or_404(Election, id=election_id)
    candidates = el.candidats.all()

    if not request.user.info.is_member:
        messages.error(request, "Vous n'avez pas accès à ce formulaire.")
        return redirect("/")  

    if not el.opened:
        return render(request, "jebif_election/vote_closed.html")
    

    if request.method == 'POST':   
        form = NewVoteForm(request.POST, user=request.user, election=el)
        if form.is_valid():
            for candidat in candidates:
                choix = form.cleaned_data[f"candidat_{candidat.id}"]
                Vote.objects.update_or_create(election=el,
                                            candidat=candidat,
                                            voter=request.user.info,
                                            date=datetime.date.today(),
                                            has_voted=True,
                                            defaults={"choix": choix},)
            messages.success(request, "Vos votes ont bien été enregistrés ✅")
            #return redirect("ok/")
            return render(request,"jebif_election/vote_ok.html")
    else:
        form = NewVoteForm(user=request.user, election=el)

    return render(request, "jebif_election/vote.html", {"election": el, "form": form})


def list_elections_view(request):
    elections = Election.objects.filter(opened=True).order_by("-date")
    return render(request, "jebif_election/list_elections.html", {"elections": elections})


def is_admin() :
	def validate( u ) :
		return u.is_authenticated() and u.is_staff
	return user_passes_test(validate)



