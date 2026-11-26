import os
import uuid
from urllib.parse import urlsplit

from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, JsonResponse
from django.views.generic import ListView, DetailView
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from PIL import Image, UnidentifiedImageError

from jebif_website.models import Article, Category, Subcategory, Events
from jebif_website.forms import NewEventForm, ParticipantForm, ContactForm
from jebif_website.utils import get_staff_emails, send_mail_safe, client_ip, hit_rate_limit


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

    def get_queryset(self, **kwargs):
        # get a queryset for a specific subcategory (which must belong to the category)
        self.category = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        self.subcategory = get_object_or_404(Subcategory, slug=self.kwargs['subcategory_slug'], category=self.category)
        return Article.objects.filter(category=self.category, subcategory=self.subcategory).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['subcategory'] = self.subcategory
        return context


class CategoryView(ListView):
    model = Article
    template_name = 'jebif_website/category.html'
    paginate_by = 5
    context_object_name = 'articles'

    def get_queryset(self, **kwargs):
        # get a queryset for a specific category
        self.category = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        return Article.objects.filter(category=self.category, subcategory__isnull=True).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class ArticleView(DetailView):
    model = Article
    template_name = 'jebif_website/article.html'
    context_object_name = "article"


def _get_public_event(request, event_id):
    """Event visible by everyone: validated (not pending, not rejected).
    Staff can also see the other ones, to check them before validation."""
    event = get_object_or_404(Events, id=event_id)
    if not event.is_public and not request.user.is_staff:
        raise Http404
    return event


def get_event_view(request, event_id):
    event = _get_public_event(request, event_id)
    return render(request, 'jebif_website/event.html', {'event': event})


# To upload images in the Editor (for articles)
ALLOWED_IMAGE_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "GIF": ".gif", "WEBP": ".webp"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024    # 10 Mo


def _same_origin(request):
    """True if the request comes from a page of this site (Origin, or Referer, header).
    Replaces the CSRF token check, that TinyMCE cannot send."""
    source = request.headers.get("Origin") or request.headers.get("Referer")
    if not source:
        return False
    return urlsplit(source).netloc == request.get_host()


@csrf_exempt    # TinyMCE does not send the CSRF token: the origin is checked instead
@require_POST
def upload_image(request):
    # Only staff members write articles, so only they can upload images
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({"error": "Accès refusé"}, status=403)
    if not _same_origin(request):
        return JsonResponse({"error": "Origine refusée"}, status=403)
    if "file" not in request.FILES:
        return JsonResponse({"error": "Invalid request"}, status=400)

    image = request.FILES["file"]
    if image.size > MAX_UPLOAD_SIZE:
        return JsonResponse({"error": "Fichier trop volumineux"}, status=400)

    # Check the content of the file, not only its name
    try:
        with Image.open(image) as img:
            img.verify()
            image_format = img.format
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return JsonResponse({"error": "Le fichier n'est pas une image valide"}, status=400)
    if image_format not in ALLOWED_IMAGE_FORMATS:
        return JsonResponse({"error": "Type de fichier non autorisé"}, status=400)
    image.seek(0)

    # Random file name: no collision, nothing taken from the user-provided name
    name = f"{uuid.uuid4().hex}{ALLOWED_IMAGE_FORMATS[image_format]}"
    path = default_storage.save(os.path.join("images", "uploaded_images", name), image)
    return JsonResponse({"location": default_storage.url(path)})


@login_required
def propose_event_view(request):
    user_info = getattr(request.user, "info", None)
    is_member = bool(user_info and user_info.is_active_member)
    if not (is_member or request.user.is_superuser):
        messages.error(request, "❌ Vous n'avez pas accès à ce formulaire.")
        return redirect("home")

    if request.method == 'POST':
        form = NewEventForm(request.POST, user=request.user)
        if form.is_valid():
            event = form.save(commit=False)
            event.organiser = request.user
            if request.user.is_superuser:
                # Events proposed by a superuser are validated automatically
                event.pending = False
                event.active = True
            event.save()

            if event.pending:
                messages.success(request, "✅ Votre proposition d'évènement a bien été enregistrée, elle sera publiée après validation.")
                # send mail to staff (only if there is something to validate)
                send_mail_safe(
                    settings.EMAIL_SUBJECT_PREFIX + "Nouvel évènement proposé",
                    f"Un nouvel évènement a été soumis.\n\n"
                    f"Titre : {event.title}\n"
                    f"Date : {event.date}\n"
                    f"Localisation : {event.localisation}\n"
                    f"Description : {event.description}\n"
                    f"Proposé par : {request.user.username}",
                    get_staff_emails(),
                )
            else:
                messages.success(request, "✅ L'évènement a été publié.")
            return redirect("home")
    else:
        form = NewEventForm(user=request.user)

    return render(request, "jebif_website/event_form.html", {"form": form,})


EVENT_REGISTER_DELAY = 10    # seconds between two registrations from the same IP


def event_register_view(request, event_id):
    event = _get_public_event(request, event_id)

    if event.is_past:
        messages.error(request, "❌ Cet évènement est terminé, les inscriptions sont closes.")
        return redirect("event", event_id=event.id)

    # Server-side check of the maximum number of participants
    # (the template check can be bypassed by posting directly)
    if event.is_full:
        messages.error(request, "❌ Le nombre maximum d'inscriptions pour cet événement a été atteint.")
        return redirect("event", event_id=event.id)

    if request.method == "POST":
        form = ParticipantForm(request.POST, event=event)

        if form.is_valid():
            if hit_rate_limit("event_register", client_ip(request), EVENT_REGISTER_DELAY):
                messages.error(request, "Trop de tentatives, réessayez dans quelques secondes.")
                return render(request, "jebif_website/register_form.html", {"form": form, 'event': event})

            with transaction.atomic():
                # Check the capacity again inside the transaction, with the event row locked
                # (two people registering at the same time for the last place)
                event = Events.objects.select_for_update().get(pk=event.pk)
                if event.is_full:
                    messages.error(request, "❌ Le nombre maximum d'inscriptions pour cet événement a été atteint.")
                    return redirect("event", event_id=event.id)
                participant = form.save(commit=False)
                if request.user.is_authenticated:
                    participant.user = request.user
                participant.event = event
                participant.save()
            messages.success(request, f"✅ Votre inscription a l'évènement {event.title} a bien été prise en compte. ")
            return redirect("event", event_id=event.id)
    else:
        initial_data = {}
        user_info = getattr(request.user, "info", None) if request.user.is_authenticated else None
        if user_info is not None:
            initial_data = {
                "first_name": user_info.firstname,
                "last_name": user_info.lastname,
                "email": user_info.email,
            }
        form = ParticipantForm(event=event, initial=initial_data)

    return render(request, "jebif_website/register_form.html", {"form": form, 'event': event})


CONTACT_DELAY = 60    # seconds between two messages from the same IP


# For the contact page
def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)

        if form.is_valid():
            # Limit to avoid spam (only counted for valid messages)
            if hit_rate_limit("contact", client_ip(request), CONTACT_DELAY):
                messages.error(request, "Trop de tentatives, réessayez dans une minute.")
                return render(request, 'jebif_website/contact_form.html', {'form': form})

            # The sender is a fixed address of the association (never the
            # client-provided one); the contact address goes in Reply-To.
            sent = send_mail_safe(
                f"{settings.EMAIL_SUBJECT_PREFIX}Message de {form.cleaned_data['name']} depuis le site",
                f"Nom : {form.cleaned_data['name']}\n"
                f"Email : {form.cleaned_data['email']}\n\n"
                f"Commentaire :\n{form.cleaned_data['commentary']}",
                [settings.CONTACT_EMAIL],
                reply_to=[form.cleaned_data['email']],
            )
            if sent:
                messages.success(request, "Votre message a bien été envoyé ✅")
                return redirect('contact_form')
            messages.error(request, "❌ Votre message n'a pas pu être envoyé, réessayez plus tard.")
    else:
        form = ContactForm()

    return render(request, 'jebif_website/contact_form.html', {'form': form})
