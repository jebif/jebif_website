import datetime
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.defaultfilters import slugify
from django.db.transaction import atomic
#from django.db.models.signals import post_save		# Unused, but could be used 
from django.core.mail import send_mail

User = get_user_model() 


def default_end_membership():
	'''
	Obtain a default date for the membership, one year later from today.

	Parameters
	----------

	Returns
	-------
		A default date, one year from now/today.

	'''
	return datetime.date.today() + datetime.timedelta(days=365)


def end_membership(base=None) :	
	'''
	Using a date, return this date plus one year (today is used as default).
	Can't remove it (issue with initial migration if done), but should be useless.

	Parameters
	----------
	base : date
		The starting date of the membership.

	Returns
	-------
		The ending date of the membership.


	'''
	d = base
	if d is None :
		d = datetime.date.today()
	try :
		end = datetime.date(d.year+1,d.month,d.day)
	except ValueError :
		end = datetime.date(d.year+1,d.month,d.day-1)
	return end - datetime.timedelta(1)


class UserInfo( models.Model ) :
	'''
	Object created to add more info for an User, accessed with: "user.info".
	It should not be independent from an User.
	...

	Attributes
	----------

	user : str
		The User it is referring to.

	email : str
		The email address of the User.

	firstname : str
		The firstname of the User.

	lastname : str
		The lastname of the User.

	laboratory : str
		The working place of the User.

	city_name : str
		In previous versions of the site, it was the city of the laboratory;
		but for students it should be their place of living.

	city_cp : str
		Same as city name, its the postal code of either the laboratory or the living place.

	country : str
		Idem, name of the country of the User or of its Laboratory.

	position : str
		Current position of the User (can be unemployed or student)

	motivation : str
		"Short" optional description of the reasons for the User to register.

	inscription_date : str (date)
		User's regitration date.

	is_member : bool
		If the User is a member or not (a registered user can not be a member) default = False

	want_member : bool
		If the User wants to become a member or not. If already a member, should be False. default = False

	is_deleted : bool
		If the User decide to not use the website anymore, but doesn't mind we keep its data.

	begin_membership : str (date)
		Start of the User's membership.

	end_membership : str (date)
		End of the User's membership.

		
	Methods
	-------

	__str__()
		What should be returned when used in a string.

	latter_membership()
		From old repos, not deleted yet because used in expire_adhesion.py that still need to be reworked.

	get_end_membership( base=None )
		Function to get the date of the end of the membership, either using the provided date or today as default for the start.
		It returns this date plus one year.
	
	init_date( begin_membership )
		Using begin_membership as a starting date, modify both fields begin_membership and end_membership of the User.

	has_expired()
		Return if end_membership has passed and the membership has expired.

	expire_delta()
		Return the difference between today and the end_membership.

	re_new_membership()
		Grant membership to the User, modifying the begin_membership field (and other related fields).
		Also send an email to the User to inform him.

	mark_deleted()
		Modify the relevant field to mark the User as deleted.
		Important: the User won't really be deleted. 
		To do so, use the Admin action that "delete", and not "mark as deleted".

	make_user() 
		Check if there is not already a User, thant create a new one. 
		Method from the old repo, should not be used (but is used in some other functions/methods from old repo)

	get_contact_data()
		Method from old repo to get informations from the user,
		creating a new one (with new password) if not existant.
		Returning a dictionnary of those informations.
	'''
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
		'''
		From old repos, not deleted yet because used in expire_adhesion.py that still need to be reworked.
		'''
		try :
			return User.objects.filter(info=self).order_by("-date_begin")[0]
		except IndexError :
			print(f"No membership for {self} !")
			raise

	class Meta :
		verbose_name = "UserInfo"

	def get_end_membership(self,base=None) :
		'''
		Function to get the date of the end of the membership, either using the provided date or today as default for the start.
		It returns this date plus one year.

		Parameters
		----------
		base : date
			The starting date of the membership.

		Returns
		-------
			The ending date of the membership.
		'''
		d = base
		if d is None :
			d = datetime.date.today()
		try :
			end = datetime.date(d.year+1,d.month,d.day)
		except ValueError :
			end = datetime.date(d.year+1,d.month,d.day-1)
		return end - datetime.timedelta(1)

	def init_date( self, begin_membership ) :
		'''
		Using begin_membership as a starting date, modify both fields begin_membership and end_membership of the User.

		Parameters
		----------
		begin_membership : date
			The starting date of the membership.

		Returns
		-------
			None
		'''
		self.begin_membership = begin_membership
		self.end_membership = self.get_end_membership()
	
	def has_expired( self ) :
		'''
		Return if end_membership has passed and the membership has expired.
		'''
		return self.end_membership < datetime.date.today()
	
	def expire_delta( self ) :
		'''
		Return the difference between today and the end_membership.
		'''
		return self.end_membership - datetime.date.today() + datetime.timedelta(1)

	def re_new_membership(self):
		'''
		Grant membership to the User, modifying the begin_membership field (and other related fields).
		Also send an email to the User to inform him.
		'''
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


	@atomic
	def make_user( self ) :
		'''
		Check if there is not already a User, thant create a new one. 
		Method from the old repo, should not be used (but is used in some other functions/methods from old repo)

		Return
		------
		None or passwd
			If a User is created, return its password
		'''
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
		'''
		Method from old repo to get informations from the user,
		creating a new one (with new password) if not existant.

		Return 
		------
			A dictionnary of those informations.
		'''
		new_passwd = self.make_user()
		return {
			"firstname" : self.firstname,
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
	''' 
	Version de la structure de la base de données.
	Utilisé pour migrer les données.
	'''
	version = models.SmallIntegerField()

	@classmethod
	def instance( cls ) : 	#replaced celf with cls
		try :
			return cls.objects.all()[0]
		except IndexError :
			cls.objects.create(version=0)
			return cls.objects.all()[0]
