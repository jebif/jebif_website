from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserInfo #, MembershipInfoEmailChange

class UserInline( admin.StackedInline ) :
	model = UserInfo
	can_delete = False
	extra = 0
	fields = ('firstname', 'lastname', 'email', 'is_member', 'want_member', 'inscription_date', 'laboratory', 'city_cp', 'is_deleted', 'end_membership') #'is_active', 'user')


class WantMemberFilter(admin.SimpleListFilter):
	title = "(Re)Demande d'adhésion"
	parameter_name = 'want_member'

	def lookups(self, request, model_admin):
		return (
			('yes', 'Oui'),
			('no', 'Non'),
		)

	def queryset(self, request, queryset):
		if self.value() == 'yes':
			return queryset.filter(userinfo__want_member=True)
		if self.value() == 'no':
			return queryset.filter(userinfo__want_member=False)
		return queryset
	
class IsDeletedFilter(admin.SimpleListFilter):
	title = "Supprimé"
	parameter_name = 'is_deleted'

	def lookups(self, request, model_admin):
		return (
			('yes', 'Oui'),
			('no', 'Non'),
		)

	def queryset(self, request, queryset):
		if self.value() == 'yes':
			return queryset.filter(userinfo__is_deleted=True)
		if self.value() == 'no':
			return queryset.filter(userinfo__is_deleted=False)
		return queryset


class UserInfoAdmin(BaseUserAdmin):
	inlines = [UserInline]
	list_display = ('username', 'firstname', 'lastname', 'email', 'is_member', 'want_member', 'inscription_date', 'laboratory', 'city_cp', 'is_deleted', 'end_membership',)
	list_filter = BaseUserAdmin.list_filter + (WantMemberFilter,IsDeletedFilter,)
	search_fields = ('firstname', 'lastname', 'email', 'user__username')

	#Get each field of the UserInfo to display
	def firstname(self, obj):
		return obj.info.firstname
	
	def lastname(self, obj):
		return obj.info.lastname
	
	def inscription_date(self, obj):
		return obj.info.inscription_date

	def laboratory(self, obj):
		return obj.info.laboratory
	
	def city_cp(self, obj):
		return obj.info.city_cp

	def is_deleted(self, obj):
		return obj.info.is_deleted
	# to be able to order with this column
	is_deleted.admin_order_field = 'info__is_deleted'
	# to get correct display for booleans
	is_deleted.boolean = True 

	def is_member(self, obj):
		return obj.info.is_member
	is_member.boolean = True 

	def want_member(self, obj):
		return obj.info.want_member
	want_member.admin_order_field = 'info__want_member'
	want_member.boolean = True

	def end_membership(self, obj):
		return obj.info.end_membership
	


# Re-register UserInfoAdmin
admin.site.unregister(User)
admin.site.register(User, UserInfoAdmin)


#class MembershipInfoEmailChangeAdmin( admin.ModelAdmin ) :
#	list_display = ('date', 'info', 'old_email')

#admin.site.register(MembershipInfoEmailChange, MembershipInfoEmailChangeAdmin)

