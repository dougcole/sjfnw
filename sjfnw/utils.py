from django.core.urlresolvers import reverse

def create_link(url, text, new_tab=False):
  new_tab = ' target="_blank"' if new_tab else ''
  return '<a href="{}"{}>{}</a>'.format(url, new_tab, text)

def admin_change_link(namespace, obj, new_tab=False):
  url = reverse('admin:{}_change'.format(namespace), args=(obj.pk,))
  return create_link(url, unicode(obj), new_tab=new_tab)
