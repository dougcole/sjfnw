from django import template

register = template.Library()

@register.filter()
def key(dic, k):
  if hasattr(dic, 'get'):
    return dic.get(k)
  return dic[k]
