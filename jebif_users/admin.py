from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserInfo #, MembershipInfoEmailChange

class UserInline( admin.StackedInline ) :
	model = UserInfo
	can_delete = False
	extra = 0
	fields = ('firstname', 'lastname', 'email', 'is_member', 'inscription_date', 'laboratory', 'city_cp', 'is_deleted', 'end_membership') #'is_active', 'user')

#class UserInfoAdmin( admin.ModelAdmin ) :
class UserInfoAdmin(BaseUserAdmin):
	inlines = [UserInline]
	list_display = ('username', 'firstname', 'lastname', 'email', 'is_member', 'inscription_date', 'laboratory', 'city_cp', 'is_deleted', 'end_membership',)
	list_filter = ('is_active', ) #'is_deleted') need custom user model, or create a SimpleListFilter (with lots of code)
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
	# to get correct display
	is_deleted.boolean = True 

	def is_member(self, obj):
		return obj.info.is_member
	is_member.boolean = True 

	def end_membership(self, obj):
		return obj.info.end_membership
	

# Re-register UserInfoAdmin
admin.site.unregister(User)
admin.site.register(User, UserInfoAdmin)


#class MembershipInfoEmailChangeAdmin( admin.ModelAdmin ) :
#	list_display = ('date', 'info', 'old_email')

#admin.site.register(MembershipInfoEmailChange, MembershipInfoEmailChangeAdmin)

