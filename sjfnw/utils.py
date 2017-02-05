from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from sjfnw import constants as c

def create_link(url, text, new_tab=False):
  new_tab = ' target="_blank"' if new_tab else ''
  return '<a href="{}"{}>{}</a>'.format(url, new_tab, text)

def admin_change_link(namespace, obj, new_tab=False):
  url = reverse('admin:{}_change'.format(namespace), args=(obj.pk,))
  return create_link(url, unicode(obj), new_tab=new_tab)

def send_email(subject, to, sender, template, context={}):
  html_content = render_to_string(template, context)
  text_content = strip_tags(html_content)
  msg = EmailMultiAlternatives(subject, text_content, sender, to, [c.SUPPORT_EMAIL])
  msg.attach_alternative(html_content, 'text/html')
  msg.send()
