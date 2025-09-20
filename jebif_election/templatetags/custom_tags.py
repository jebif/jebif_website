from django import template
#File to create customs tags to use in html


register = template.Library()

@register.filter
def contains(value, arg):
    #Check if a word is present in an argument
    if not value:
        return False
    return arg.lower() in value.lower()