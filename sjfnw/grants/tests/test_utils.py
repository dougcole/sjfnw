# encoding: utf-8

from django.utils import timezone
from django.test import TestCase

from sjfnw.grants import utils

class StripPunctuation(TestCase):

  def test_str(self):
    result = utils.strip_punctuation_and_non_ascii('Hello, here\'s a list : - one! * two; + three')
    self.assertEqual(result, 'Hello heres a list   one  two  three')

    result = utils.strip_punctuation_and_non_ascii('Watch=these, / ^other $chars@get (removed) `too\r &&')
    self.assertEqual(result, 'Watchthese  other charsget removed too\r ')

  def test_unicode(self):
    result = utils.strip_punctuation_and_non_ascii(u'Hello‚ here’s å lˆst – □ oñe▶ ● two; +◇ thrée')
    self.assertEqual(result, u'Hello heres  lst   oe  two  thre')

    result = utils.strip_punctuation_and_non_ascii(u'Watch‐these, • ‘other ▹chars‒get “removed” `too\r ■')
    self.assertEqual(result, u'Watchthese  other charsget removed too\r ')

class LocalDateStr(TestCase):

  def test_timestamp(self):
    utc_time = timezone.now()
    print(utc_time)
