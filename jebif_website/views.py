import os

from django.shortcuts import render, get_object_or_404, redirect, Http404
from django.views.generic import ListView, DetailView
from django.conf import settings
from django.http import JsonResponse
from django.core.mail import send_mail, EmailMessage
from django.core.files.storage import default_storage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.utils import timezone

from jebif_website.models import Article, Category, Subcategory, Events, Meetings
from jebif_website.forms import NewEventForm, ParticipantForm, ContactForm
from jebif_users.views import is_admin

import json
from datetime import datetime

def get_staff_emails():
    """Emails of "Staff" users, computed at call time (not at import time)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return [user.email for user in User.objects.filter(is_staff=True) if user.email]

class HomeView(ListView):
    model = Article
    template_name = 'jebif_website/home.html'
    paginate_by = 2
    context_object_name = 'articles'

    # get a queryset with no category
    def get_queryset(self, **kwargs):
        return Article.objects.filter(category__isnull=True, subcategory__isnull=True).order_by('-date')
    

class SubcategoryView(ListView):
    model = Article
    template_name = 'jebif_website/subcategory.html'
    paginate_by = 5
    context_object_name = 'articles'

    # necessary to get info for a specific subcategory
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        context['subcategory'] = get_object_or_404(Subcategory, slug=self.kwargs['subcategory_slug'])
        return context

    # get a queryset for a specific subcategory
    def get_queryset(self, **kwargs):
        category_slug = self.kwargs['category_slug']
        subcategory_slug = self.kwargs['subcategory_slug']

        category = get_object_or_404(Category, slug=category_slug)
        subcategory = get_object_or_404(Subcategory, slug=subcategory_slug, category=category)
        return Article.objects.filter(category=category, subcategory=subcategory).order_by('-date')

    
class CategoryView(ListView):
    model = Article
    template_name = 'jebif_website/category.html'
    paginate_by = 5
    context_object_name = 'articles'

    # necessary to get info for a specific category
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        return context

    # get a queryset for a specific category
    def get_queryset(self, **kwargs):
        category_slug = self.kwargs['category_slug']
        category = get_object_or_404(Category, slug=category_slug)
        return Article.objects.filter(category=category, subcategory__isnull=True).order_by('-date')
    

class ArticleView(DetailView):  
    model = Article
    template_name = 'jebif_website/article.html'
    context_object_name = "article"

def get_event_view(request, event_id):
    event = get_object_or_404(Events, id=event_id)
    # Pending (not yet approved) events must not be publicly visible
    if event.pending:
        raise Http404
    return render(request, 'jebif_website/event.html', {'event': event})

# To upload images in the Editor (for articles)
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024    # 10 Mo

@login_required
def upload_image(request):
    if request.method != "POST" or "file" not in request.FILES:
        return JsonResponse({"error": "Invalid request"}, status=400)

    image = request.FILES["file"]
    extension = os.path.splitext(image.name)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return JsonResponse({"error": "Type de fichier non autorisé"}, status=400)
    if image.size > MAX_UPLOAD_SIZE:
        return JsonResponse({"error": "Fichier trop volumineux"}, status=400)

    path = default_storage.save(f"images/uploaded_images/{image.name}", image)
    return JsonResponse({"location": f"{settings.MEDIA_URL}{path}"})


@login_required(login_url='login')
def propose_event_view(request):
    user_info = getattr(request.user, "info", None)
    is_member = bool(user_info and user_info.is_member)
    if not (is_member or request.user.is_superuser):
        messages.error(request, "❌ Vous n'avez pas accès à ce formulaire.")
        return redirect("/")

    if request.method == 'POST':   
        form = NewEventForm(request.POST, user=request.user)
        if form.is_valid():
            pending_event = form.save(commit=False)
            pending_event.organiser = request.user
            if request.user.is_superuser:
                pending_event.pending = False
                pending_event.active = True
            pending_event.save()
            messages.success(request, "✅ Votre proposition d'évènement a bien été enregistré. ")
            #send mail to staff
            send_mail(
                subject="Nouvel évènement proposé",
                message=(
                    f"Un nouvel évènement a été soumis.\n\n"
                    f"Titre : {pending_event.title}\n"
                    f"Date : {pending_event.date}\n"
                    f"Localisation : {pending_event.localisation}\n"
                    f"Description : {pending_event.description}\n"
                    f"Proposé par : {request.user.username}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=get_staff_emails(),
                fail_silently=False,
            )
            
            return redirect("/")
    else:
        form = NewEventForm(user=request.user)

    return render(request, "jebif_website/event_form.html", {"form": form,})

def event_register_view(request, event_id):
    event = get_object_or_404(Events, id=event_id)
    # Pending (not yet approved) events must not be publicly visible
    if event.pending:
        raise Http404

    # Server-side check of the maximum number of participants
    # (the template check can be bypassed by posting directly)
    if event.max_participants > 0 and event.participant_set.count() >= event.max_participants:
        messages.error(request, "❌ Le nombre maximum d'inscriptions pour cet événement a été atteint.")
        return redirect(f"/event/{event.id}")

    if request.method == "POST":
        form = ParticipantForm(request.POST, user=request.user, event=event)

        if form.is_valid():
            participant = form.save(commit=False)
            if not request.user.is_anonymous:
                participant.user = request.user
            participant.event = event
            participant.save()
            messages.success(request, f"✅ Votre inscription a l'évènement {event.title} a bien été prise en compte. ")
            return redirect(f"/event/{event.id}")
    else:
        if not request.user.is_anonymous:
            user_info = getattr(request.user, "info", None)
            if user_info is None:
                initial_data = {}
            else:
                initial_data = {
                "first_name": user_info.firstname,
                "last_name": user_info.lastname,
                "email": user_info.email,
            }
            form = ParticipantForm(
                user = request.user,
                initial=initial_data
            )
        else:
            form = ParticipantForm(user=request.user, event=event)

    return render(request, "jebif_website/register_form.html", {"form": form, 'event': event})

# For the contact page
def contact_view(request):
    ip = request.META.get('REMOTE_ADDR') or "unknown"

    if request.method == 'POST':
        #Limit to avoid spam
        if cache.get(ip):
            messages.error(request, "Trop de tentatives, réessayez plus tard.")
            return redirect('contact_form')

        form = ContactForm(request.POST)

        if form.is_valid():
            cache.set(ip, True, timeout=60)  # 1 request/minute

            # The sender is a fixed address of the association (never the
            # client-provided one); the contact address goes in Reply-To.
            email = EmailMessage(
                subject=f"{settings.EMAIL_SUBJECT_PREFIX}Message de {form.cleaned_data['name']} depuis le site",
                body=f"""
                Nom: {form.cleaned_data['name']},
                Email: {form.cleaned_data['email']},
                Commentaire: {form.cleaned_data['commentary']}""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.SERVER_EMAIL],
                reply_to=[form.cleaned_data['email']],
            )
            email.send(fail_silently=True)

            messages.success(request, "Votre message a bien été envoyé ✅")
            return redirect('contact_form')

    else:
        form = ContactForm()

    return render(request, 'jebif_website/contact_form.html', {'form': form})

@login_required
@is_admin()
def create_events_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)

        #date = datetime.fromisoformat(data["date"])
        date = timezone.make_aware(datetime.fromisoformat(data["date"]))

        event = Events.objects.create(
            title=data["title"],
            date=date,
            localisation=data["localisation"],
            description=data["description"],
            max_participants=data["max_participants"],
            pending=False,
            organiser=request.user,
            active=True
        )

        return JsonResponse({"status": "ok", "id": event.id})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@is_admin()
def create_meetings_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)

        #date = datetime.fromisoformat(data["date"])
        date = timezone.make_aware(datetime.fromisoformat(data["date"]))

        meeting = Meetings.objects.create(
            title=data["title"],
            date=date,
            kind=data["kind"],
            description=data["description"],
        )

        return JsonResponse({"status": "ok", "id": meeting.id})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
