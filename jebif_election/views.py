from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.utils.timezone import now


from jebif_election.models import Election, Vote, get_election_results
from jebif_election.forms import NewVoteForm, NewCandidateForm #, MailingForm

import datetime



@login_required(login_url='login')
def vote_view(request, election_id):
    el = get_object_or_404(Election, id=election_id)

    if not request.user.info.is_member:
        messages.error(request, "Vous n'avez pas accès à ce formulaire.")
        return redirect("/")  

    if not el.opened:
        return render(request, "jebif_election/vote_closed.html")
    
    #Remove candidates already voted for
    voted_candidates = Vote.objects.filter(election=el,
                                           voter=request.user.info,
                                           has_voted=True
                                           ).values_list("candidat_id", flat=True)

    candidates = el.candidats.exclude(id__in=voted_candidates)

    if len(candidates)==0:
         return render(request, "jebif_election/vote_already_done.html")

    if request.method == 'POST':   
        form = NewVoteForm(request.POST, user=request.user, election=el, candidates=candidates)
        if form.is_valid():
            for candidat in candidates:
                choix = form.cleaned_data[f"candidat_{candidat.id}"]
                Vote.objects.update_or_create(election=el,
                                            candidat=candidat,
                                            voter=request.user.info,
                                            defaults={"choix": choix, "date": now, "has_voted": True},)
            messages.success(request, "✅ Vos votes ont bien été enregistrés.")
            #return redirect("ok/")
            return render(request,"jebif_election/vote_ok.html")
    else:
        form = NewVoteForm(user=request.user, election=el, candidates=candidates)

    return render(request, "jebif_election/vote.html", {"election": el, "candidates": candidates, "form": form})


@login_required(login_url='login')
def list_elections_view(request):
    if not request.user.info.is_member:
        messages.error(request, "Vous n'avez pas accès à cette page.")
        return redirect("/")

    elections = Election.objects.filter(opened=True).order_by("-date")
    waiting_el = Election.objects.filter(waiting=True).order_by("-date")
    ended_el = Election.objects.filter(ended=True).order_by("-date")
    if len(elections) == 0:
         return render(request, "jebif_election/list_elections.html", {"waiting_el": waiting_el, "ended_el": ended_el})
    else:
        return render(request, "jebif_election/list_elections.html", {"elections": elections, "waiting_el": waiting_el, "ended_el": ended_el})

@login_required(login_url='login')
def candidate_to_election_view(request):
    if not request.user.info.is_member:
        messages.error(request, "Vous n'avez pas accès à ce formulaire.")
        return redirect("/")

    elections = Election.objects.filter(waiting=True).order_by("-date")
    if request.method == 'POST':   
        form = NewCandidateForm(request.POST, user=request.user, elections=elections)
        if form.is_valid():
            candidat = form.save(commit=False)
            candidat.user = request.user
            candidat.save()
            messages.success(request, "✅ Votre candidature a bien été enregistré. ")
            return redirect("list_elections")
    else:
        form = NewCandidateForm(user=request.user, elections=elections)

    return render(request, "jebif_election/candidate_form.html", {"form": form, "elections": elections})


@login_required(login_url='login')
def result_view(request, election_id):
    el = get_object_or_404(Election, id=election_id)
    #results = get_election_results(election_id)
    results = el.get_results()

    if not request.user.info.is_member:
        messages.error(request, "Vous n'avez pas accès à cette page.")
        return redirect("/")  

    if el.opened:
        messages.error(request, "Cette élection n'est pas terminée.")
        return render(request, "jebif_election/vote.html", {"election": el,})
    else:
        return render(request, "jebif_election/results.html", {"election": el, "results": results,})
    

@login_required(login_url='login')
def list_result_view(request):
    if not request.user.info.is_member:
        messages.error(request, "Vous n'avez pas accès à cette page.")
        return redirect("/")

    ended_el = Election.objects.filter(ended=True).order_by("-date")
    return render(request, "jebif_election/list_results.html", {"ended_el": ended_el,})



"""def is_admin() :
	def validate( u ) :
		return u.is_authenticated() and u.is_staff
	return user_passes_test(validate)"""