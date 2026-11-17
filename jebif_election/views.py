from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings

from jebif_election.models import Election, Vote
from jebif_election.forms import NewVoteForm, NewCandidateForm


def get_staff_emails():
    """Emails of "Staff" users."""
    User = get_user_model()
    return [user.email for user in User.objects.filter(is_staff=True) if user.email]


def _get_user_info(request):
    """UserInfo of the logged-in user, or None (a user may not have one)."""
    return getattr(request.user, "info", None)


@login_required(login_url='login')
def vote_view(request, election_id):
    el = get_object_or_404(Election, id=election_id)

    user_info = _get_user_info(request)
    if not (user_info and user_info.is_member):
        messages.error(request, "❌ Vous n'avez pas accès à ce formulaire.")
        return redirect("/")  

    if not el.opened:
        return render(request, "jebif_election/vote_closed.html")
    
    #Remove candidates already voted for
    voted_candidates = Vote.objects.filter(election=el,
                                           voter=user_info,
                                           has_voted=True
                                           ).values_list("candidat_id", flat=True)

    candidates = el.candidats.exclude(id__in=voted_candidates)

    if len(candidates)==0:
         return render(request, "jebif_election/vote_already_done.html")

    if request.method == 'POST':   
        form = NewVoteForm(request.POST, user=request.user, election=el, candidates=candidates)
        if form.is_valid():
            try:
                with transaction.atomic():
                    for candidat in candidates:
                        choix = form.cleaned_data[f"candidat_{candidat.id}"]
                        Vote.objects.update_or_create(election=el,
                                                    candidat=candidat,
                                                    voter=user_info,
                                                    defaults={"choix": choix, "date": now, "has_voted": True},)
            except IntegrityError:
                # Duplicate vote (race condition): the unique constraint caught it
                messages.error(request, "❌ Tu as déjà voté pour cette élection.")
                return redirect("list_elections")
            messages.success(request, "✅ Tes votes ont bien été enregistrés.")
            return render(request,"jebif_election/vote_ok.html")
    else:
        form = NewVoteForm(user=request.user, election=el, candidates=candidates)

    return render(request, "jebif_election/vote.html", {"election": el, "candidates": candidates, "form": form})


@login_required(login_url='login')
def list_elections_view(request):
    user_info = _get_user_info(request)
    if not (user_info and user_info.is_member):
        messages.error(request, "❌ Vous n'avez pas accès à cette page.")
        return redirect("/")

    elections = Election.objects.filter(opened=True).order_by("-start_date")    #May change that to check end_date instead
    waiting_el = Election.objects.filter(waiting=True).order_by("-start_date")
    ended_el = Election.objects.filter(ended=True).order_by("-start_date")
    if len(elections) == 0:
         return render(request, "jebif_election/list_elections.html", {"waiting_el": waiting_el, "ended_el": ended_el})
    else:
        return render(request, "jebif_election/list_elections.html", {"elections": elections, "waiting_el": waiting_el, "ended_el": ended_el})


@login_required(login_url='login')
def candidate_to_election_view(request):
    user_info = _get_user_info(request)
    if not (user_info and user_info.is_member):
        messages.error(request, "❌ Vous n'avez pas accès à ce formulaire.")
        return redirect("/")

    elections = Election.objects.filter(waiting=True).order_by("-start_date")   #May need to check with the date too, in case of an error from the admin
    if request.method == 'POST':   
        form = NewCandidateForm(request.POST, user=request.user, elections=elections)
        if form.is_valid():
            candidat = form.save(commit=False)
            candidat.user = request.user
            candidat.save()
            messages.success(request, "✅ Votre candidature a bien été enregistré. ")
            send_mail(
                subject="Nouvel Candidature proposée",
                message=(
                    f"Une nouvel candidature a été soumise.\n\n"
                    f"Nom : {candidat.label}\n"
                    f"Election : {candidat.election}\n"
                    f"Description : {candidat.description}\n"
                    f"Proposé par : {request.user.username}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=get_staff_emails(),
                fail_silently=False,
            )
            return redirect("list_elections")
    else:
        form = NewCandidateForm(user=request.user, elections=elections)

    return render(request, "jebif_election/candidate_form.html", {"form": form, "elections": elections})


@login_required(login_url='login')
def result_view(request, election_id):
    el = get_object_or_404(Election, id=election_id)

    user_info = _get_user_info(request)
    if not (user_info and user_info.is_member):
        messages.error(request, "❌ Vous n'avez pas accès à cette page.")
        return redirect("/")  

    if el.opened:
        messages.error(request, "❌ Cette élection n'est pas terminée.")
        return redirect(f"/election/{el.id}/vote/")

    results = el.get_results()
    return render(request, "jebif_election/results.html", {"election": el, "results": results,})
    

@login_required(login_url='login')
def list_result_view(request):
    user_info = _get_user_info(request)
    if not (user_info and user_info.is_member):
        messages.error(request, "❌ Vous n'avez pas accès à cette page.")
        return redirect("/")

    ended_el = Election.objects.filter(ended=True).order_by("-start_date")
    return render(request, "jebif_election/list_results.html", {"ended_el": ended_el,})


#May be used later to create admin pages in the website to create elections
"""def is_admin() :
	def validate( u ) :
		return u.is_authenticated() and u.is_staff
	return user_passes_test(validate)"""