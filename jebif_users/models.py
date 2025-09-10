import datetime
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.db.transaction import atomic
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail

User = get_user_model() 

#To get a default end_membership
def default_end_membership():
    return datetime.date.today() + datetime.timedelta(days=365)

def end_membership(base=None) :
		d = base
		if d is None :
			d = datetime.date.today()
		try :
			end = datetime.date(d.year+1,d.month,d.day)
		except ValueError :
			end = datetime.date(d.year+1,d.month,d.day-1)
		return end - datetime.timedelta(1)

class UserInfo( models.Model ) :
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="info")	#to access it from user: user.info
	email = models.EmailField(unique=True)
	firstname = models.CharField("Prénom", max_length=75)
	lastname = models.CharField("Nom", max_length=75)
	laboratory = models.CharField("Laboratoire", max_length=75)
	city_name = models.CharField("Ville", max_length=75)
	city_cp = models.CharField("Code Postal", max_length=7)
	country = models.CharField("Pays", max_length=75)
	position = models.CharField("Poste actuel", max_length=75)
	motivation = models.TextField("Motivation pour adhérer", blank=True)

	inscription_date = models.DateField(default=datetime.date.today)
	is_member = models.BooleanField(default=False)
	want_member = models.BooleanField("L'utilisateur souhaite devenir adhérent",default=False)
	is_deleted = models.BooleanField(default=False) 
	begin_membership = models.DateField(default=datetime.date.today)
	end_membership = models.DateField(default=default_end_membership)
	
	def __str__( self ) :
		return f"{self.firstname} {self.lastname} <{self.user.email}> {'(inactive)' if not self.is_member else ''}"

	def latter_membership( self ) :
		try :
			return User.objects.filter(info=self).order_by("-date_begin")[0]
		except IndexError :
			print(f"No membership for {self} !")
			raise

	class Meta :
		verbose_name = "UserInfo"

	def get_end_membership(self,base=None) :
		# Function to return the date of the end of the membership
		d = base
		if d is None :
			d = datetime.date.today()
		try :
			end = datetime.date(d.year+1,d.month,d.day)
		except ValueError :
			end = datetime.date(d.year+1,d.month,d.day-1)
		return end - datetime.timedelta(1)

	def init_date( self, begin_membership ) :
		# Function to create or change the dates for the beginning and end of the membership
		self.begin_membership = begin_membership
		self.end_membership = self.get_end_membership()
	
	def has_expired( self ) :
		return self.end_membership < datetime.date.today()
	
	def expire_delta( self ) :
		return self.end_membership - datetime.date.today() + datetime.timedelta(1)

	@classmethod	
	def current_objects( cls ) :	#celf replaced by cls, dunno what is celf
		today = datetime.date.today()	#added the missing ()
		return cls.objects.filter(info__active=True,
					begin_membership__lte=today, end_membership__gt=today)


	def re_new_membership(self):
		# Function to change automatically the fields related to the membership
		self.is_member = True	# change if not member, doesn't if already is
		self.init_date(datetime.date.today())	#change begin and end date of membership
		self.want_member = False
		self.save()
		if settings.DEBUG == False:
			firstname = self.firstname
			msg_subj = u"Ton adhésion à JeBiF"
			msg_txt = f"""
Bonjour {firstname},

Ton adhésion à l'association JeBiF vient d'être validée. Tu peux la modifier en te rendant sur
le site de JeBiF, dans ta page Profile.

À bientôt,
L’équipe JeBiF (RSG-France)
"""
			msg_from = "NO-REPLY@jebif.fr"
			msg_to = self.email
			send_mail(msg_subj, msg_txt, msg_from, msg_to)

	def mark_deleted(self):
		self.is_member = False
		self.is_deleted = True
		self.want_member = False
		self.end_membership = datetime.date.today()
		self.save()


	@atomic	# NOT NEEDED ANYMORE?
	def make_user( self ) :
		if self.user is not None :
			return None
		# 1. try to find a User matching email
		matching = User.objects.filter(email=self.email, is_active=True)
		if matching :
			self.user = matching[0]
			if len(matching) > 1 :
				matching2 = matching.filter(is_staff=False)
				if matching2 :
					self.user = matching2[0]
			self.save()
			return None
		else :
			passwd = User.objects.make_random_password(8)
			base_login = slugify(self.firstname)[0] + \
							slugify(self.lastname)[:7]
			login = base_login
			salt = 2
			created = False	#Useless?
			while User.objects.filter(username=login).exists() :
				login = base_login + "%d" % salt
				salt += 1
			self.user = User.objects.create_user(login, self.email, passwd)
			self.save()
			UserInfo.objects.create(
				user=self.user,
				email=self.email,
				firstname=self.firstname or "",
				lastname=self.lastname or "",
				laboratory = self.laboratory or "",
				city_name = self.city_name or "",
				city_cp = self.city_cp or "",
				country = self.country or "",
				position = self.position or "",
				begin_membership=datetime.date.today(),
				end_membership=datetime.date.today() + datetime.timedelta(days=365),
    		)

			return passwd


	def get_contact_data( self ) :
		"""def ensure_ROOT( url ) :
			if url[1:].startswith(settings.ROOT_URL) :
				return url
			else :
				return f"/{settings.ROOT_URL}{url[1:]}"
		from views import subscription_renew, subscription_update 							#NOT NEEDED ANYMORE?
		url_renew = ensure_ROOT(reverse(subscription_renew, kwargs={"info_id": self.id}))	#NOT NEEDED ANYMORE?
		url_update = ensure_ROOT(reverse(subscription_update, kwargs={"info_id": self.id}))#NOT NEEDED ANYMORE?"""
		new_passwd = self.make_user()
		return {
			"firstname" : self.firstname,
			#"url_renew" : f"{settings.HTTP_DOMAIN}{url_renew}",			#NOT NEEDED ANYMORE?
			#"url_update" : f"{settings.HTTP_DOMAIN}{url_update}",			#NOT NEEDED ANYMORE?
			"login" : self.user.username,
			"passwd_setup" : " et ton mot de passe '%s'" % new_passwd if new_passwd is not None 
								else ""
		}

"""# ---- Automatic creation of UserInfo when a User is created ---- #shouldn't be required since both forms are done at the same time
@receiver(post_save, sender=User)
def create_user_info(sender, instance, created, **kwargs):
    if created:
        UserInfo.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_info(sender, instance, **kwargs):
    instance.info.save()"""

# FROM OLD REPO, NOT MODIFIED
class DatabaseInfo( models.Model ) : 
	""" 
	Version de la structure de la base de données.
	Utilisé pour migrer les données.
	"""
	version = models.SmallIntegerField()

	@classmethod
	def instance( cls ) : 	#replaced celf with cls
		try :
			return cls.objects.all()[0]
		except IndexError :
			cls.objects.create(version=0)
			return cls.objects.all()[0]
