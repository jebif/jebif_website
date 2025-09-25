from django.db import models
from django.utils.text import slugify
from tinymce.models import HTMLField    #looks like an error but in fact works
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    '''
	Object representing a Category for an Article.
	...

	Attributes
	----------
    name : str
        The name of the category

    slug : str
        A simplification of the name to use in url (or other fields).

    Methods
	-------
    '''
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
    '''
	Object representing a Sub-category for an Article.
	...

	Attributes
	----------

    name : str
        The name of the sub-category

    slug : str
        A simplification of the name to use in url (or other fields).

    category : str
        The category it is associated to.

    Methods
	-------
    '''
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
    '''
	Object representing an Article.
	...

	Attributes
	----------
    title : str
        Title of the article

    content : html object (see tinymce doc)
        The content of the article, with text, images links,...

    date : date object
        Publishing date of the article

    updated_at : date object
        Date of the update of the article

    author : str
        Author of the article

    featured : bool
        In case a new part of the site is added, to showcase special articles;
        they could be selected with this attribute.

    likes : str
        Not used, but could be used to display the number of people liking an article.

    subcategory : str
        The Subcategory the article is belonging to (can be null).

    category : str
        The Category the article is belonging to (can be null).

    slug : str
        A simplification of the name to use in url (or other fields).

    Methods
	-------
    '''
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
    '''
	Object containing an Image with its url for a website (partners).
	...

	Attributes
	----------
    title : str
        Title of the Image

    image : str
        Link to the image in the database

    url : str
        Url the image is pointing to (partner website, etc)

    Methods
	-------
    '''
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='images/linked_images/')
    url = models.URLField(blank=True)

    def __str__(self):
        return self.title
    

class WebPlatforms(models.Model):
    '''
	Social Medias or Platform, with its url and the "username" of JeBiF on it.
	...

	Attributes
	----------
    title : str
        Title of the Platform

    identification : str
        "Username" of JeBiF on this Platform

    url : str
        Url of the platform
    Methods
	-------
    '''
    title = models.CharField(max_length=200)
    identification = models.CharField(max_length=200)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.title
    

class EventsDates(models.Model):
    '''
	Events promoted by JeBiF.
	...

	Attributes
	----------
    title : str
        Name of the Event

    date : date object
        When is the opening of the event

    localisation : str
        Where is happening the event

    Methods
	-------
    '''
    title = models.CharField(max_length=100)
    date = models.DateTimeField()
    localisation = models.CharField(max_length=100)
    def __str__(self):
        return self.title

class PendingEvents(models.Model):
    '''
	Proposition of Events for JeBiF to promote.
	...

	Attributes
	----------
    title : str
        Name of the Event

    date : date object
        When is the opening of the event

    localisation : str
        Where is happening the event

    description : str
        What is the content of the event

    user : str
        Who proposed this event

    pending : bool
        Has this event been seen (and judged). Pending: not judged yet. Not Pending: Either validated or unvalidated.
    Methods
	-------
    '''
    title = models.CharField(max_length=100)
    date = models.DateTimeField()
    localisation = models.CharField(max_length=100)
    description = models.TextField("Description")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pending_events')
    pending = models.BooleanField(default=True)

    def __str__( self ) :
        return f"{self.title}/{self.localisation}/{self.date}"