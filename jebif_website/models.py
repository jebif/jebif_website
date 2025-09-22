from django.db import models
from django.utils.text import slugify
from tinymce.models import HTMLField    #looks like an error but in fact works
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=30)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name).replace('-', '_')
            slug = base
            i = 1
            while self.__class__.objects.filter(slug=slug).exists():
                slug = f"{base}_{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    name = models.CharField(max_length=30)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, related_name="subcategory")

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name).replace('-', '_')
            slug = base
            i = 1
            while self.__class__.objects.filter(slug=slug).exists():
                slug = f"{base}_{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name



class Article(models.Model):
    title = models.CharField(max_length = 255)
    content = HTMLField()
    date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    featured = models.BooleanField(default=False)
    likes = models.ManyToManyField(User, related_name='likes', blank=True)
    subcategory = models.ForeignKey(Subcategory, null=True, blank=True, on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title).replace('-', '_')
            slug = base
            i = 1
            while self.__class__.objects.filter(slug=slug).exists():
                slug = f"{base}_{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title



class LinkedImage(models.Model):                # requires python -m pip install Pillow
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='images/linked_images/')
    url = models.URLField(blank=True)

    def __str__(self):
        return self.title
    

class WebPlatforms(models.Model):
    title = models.CharField(max_length=200)
    identification = models.CharField(max_length=200)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.title
    

class EventsDates(models.Model):
    title = models.CharField(max_length=100)
    date = models.DateTimeField()
    localisation = models.CharField(max_length=100)
    def __str__(self):
        return self.title

class PendingEvents(models.Model):
    title = models.CharField(max_length=100)
    date = models.DateTimeField()
    localisation = models.CharField(max_length=100)
    description = models.TextField("Description")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pending_events')
    pending = models.BooleanField(default=True)

    def __str__( self ) :
        return f"{self.title}/{self.localisation}/{self.date}"