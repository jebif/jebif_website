import datetime
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from jebif_website.utils import send_mail_safe


User = get_user_model() 


def end_membership(base=None) :    
    '''
    Using a date, return the last day of a one-year membership starting at this date
    (today is used as default): one year later, minus one day.

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
        anniversary = d.replace(year=d.year + 1)
    except ValueError :
        # Membership starting on February 29th: the anniversary is March 1st
        anniversary = datetime.date(d.year + 1, 3, 1)
    return anniversary - datetime.timedelta(1)


def default_end_membership():
    '''
    Default date for the end of the membership: one year from today, minus one day
    (same rule as end_membership(), used when an account is renewed).
    '''
    return end_membership()


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

    know_from : str
        From what/where the user know JeBiF
    
    verified : bool
        Has the user verified is account by following the email after is inscription

        
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

    is_active_member (property)
        True if the user is a member whose membership has not expired.
    '''
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="info")    #to access it from user: user.info
    email = models.EmailField(unique=True)
    firstname = models.CharField("Prénom", max_length=75)
    lastname = models.CharField("Nom", max_length=75)
    laboratory = models.CharField("Laboratoire", max_length=75)
    city_name = models.CharField("Ville", max_length=75)
    city_cp = models.CharField("Code Postal", max_length=7)
    country = models.CharField("Pays", max_length=75)
    position = models.CharField("Poste actuel", max_length=75)
    know_from = models.TextField("Comment avez vous connu JeBiF ?", blank=True, max_length=200)
    motivation = models.TextField("Motivation pour adhérer", blank=True)

    inscription_date = models.DateField(default=datetime.date.today)
    is_member = models.BooleanField(default=False)
    want_member = models.BooleanField("L'utilisateur souhaite devenir adhérent",default=False)
    is_deleted = models.BooleanField(default=False) 
    begin_membership = models.DateField(default=datetime.date.today)
    end_membership = models.DateField(default=default_end_membership)
    
    # Check if the user has verified their account
    verified = models.BooleanField(default=False)

    # Last time a "membership about to expire" reminder was sent (see expire_memberships command)
    last_reminder = models.DateField(null=True, blank=True)

    def __str__( self ) :
        return f"{self.firstname} {self.lastname} <{self.user.email}> {'(inactive)' if not self.is_member else ''}"

    class Meta :
        verbose_name = "UserInfo"

    def get_end_membership(self,base=None) :
        '''
        Function to get the date of the end of the membership, either using the provided date or today as default for the start.
        It returns this date plus one year, minus one day.
        '''
        return end_membership(base)

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
        self.end_membership = self.get_end_membership(begin_membership)
        self.last_reminder = None
    
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

    @property
    def is_active_member(self):
        '''
        Return True if the user is a member, not deleted, and the membership has not expired
        (does not rely on the daily expire_memberships command having run).
        '''
        return self.is_member and not self.is_deleted and not self.has_expired()

    def re_new_membership(self):
        '''
        Grant membership to the User, modifying the begin_membership field (and other related fields).
        Also send an email to the User to inform him.
        Returns True if the e-mail could be sent.
        '''
        self.is_member = True    # change if not member, doesn't if already is
        self.init_date(datetime.date.today())    #change begin and end date of membership
        self.want_member = False
        self.save()
        msg_txt = f"""
Bonjour {self.firstname},

Ton adhésion à l'association JeBiF vient d'être validée. Tu peux la modifier en te rendant sur
le site de JeBiF, dans ta page Profil.

À bientôt,
L’équipe JeBiF (RSG-France)
"""
        return send_mail_safe(settings.EMAIL_SUBJECT_PREFIX + "Ton adhésion à JeBiF", msg_txt, [self.email])

    def mark_deleted(self):
        self.is_member = False
        self.is_deleted = True
        self.want_member = False
        self.end_membership = datetime.date.today()
        self.save()


@receiver(post_save, sender=User)
def sync_user_info_email(sender, instance, **kwargs):
    '''
    Keep UserInfo.email equal to User.email when the User is modified
    (for example from the admin interface), so mails are sent to the right address.
    '''
    UserInfo.objects.filter(user=instance).exclude(email=instance.email).update(email=instance.email)
