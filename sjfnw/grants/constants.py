from sjfnw import constants as c

FORM_ERRORS = {
  'email_registered': 'That email is already registered. Log in instead.',
  'email_registered_pc': 'That email is registered with Project Central. Please register using a different email.',
  'org_registered': 'That organization is registered under a different email address. Log in instead, or contact us if you need help accessing your account.'
}

PHOTO_FILE_TYPES = ('jpeg', 'jpg', 'png', 'gif', 'bmp')

VIEWER_FILE_TYPES = ('doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf')

ALLOWED_FILE_TYPES = PHOTO_FILE_TYPES + VIEWER_FILE_TYPES + ('txt',)

STATE_CHOICES = [(state, state) for state in c.US_STATES]

STATUS_CHOICES = [
  ('Tribal government', 'Federally recognized American Indian tribal government'),
  ('501c3', '501(c)3 organization as recognized by the IRS'),
  ('501c4', '501(c)4 organization as recognized by the IRS'),
  ('Sponsored', 'Sponsored by a 501(c)3, 501(c)4, or federally recognized tribal government'),
  ('Other', 'Organized group of people without 501(c)3 or (c)4 status (you MUST call us before applying)')
]

PRE_SCREENING = (
  (10, 'Received'),
  (20, 'Incomplete'),
  (30, 'Complete'),
  (40, 'Pre-screened out'),
  (45, 'Screened out by sub-committee'),
  (50, 'Pre-screened in')
)

SCREENING = (
  (60, 'Screened out'),
  (70, 'Site visit awarded'),
  (80, 'Grant denied'),
  (90, 'Grant issued'),
  (100, 'Grant paid'),
  (110, 'Grantee report overdue'),
  (120, 'Grantee report received'),
  (130, 'Closed')
)

STANDARD_NARRATIVES = [
  {'name': 'describe_mission', 'version': 'standard' },
  {'name': 'most_impacted', 'version': 'standard' },
  {'name': 'root_causes', 'version': 'standard'},
  {'name': 'workplan', 'version': 'standard'},
  {'name': 'timeline', 'version': 'five_quarter'},
  {'name': 'racial_justice', 'version': 'standard'},
  {'name': 'racial_justice_references', 'version': 'standard'},
  {'name': 'collaboration', 'version': 'standard'},
  {'name': 'collaboration_references', 'version': 'standard'}
];

TWO_YEAR_GRANT_QUESTION = {'name': 'two_year_grant', 'version': 'standard'}

RAPID_RESPONSE_NARRATIVES = [
  {'name': 'expedited', 'version': 'rapid'},
  {'name': 'describe_mission', 'version': 'standard' },
  {'name': 'most_impacted', 'version': 'rapid' },
  {'name': 'workplan', 'version': 'rapid' },
  {'name': 'why_rapid', 'version': 'rapid' },
  {'name': 'collaboration', 'version': 'rapid' }
]

SEED_NARRATIVES = [
  {'name': 'group_beliefs', 'version': 'seed'},
  {'name': 'most_impacted', 'version': 'seed'},
  {'name': 'workplan', 'version': 'seed'},
  {'name': 'resources', 'version': 'seed'},
  {'name': 'collaboration', 'version': 'seed'}
]

NARRATIVE_WORD_LIMITS = {
  'narrative1': 300,
  'narrative2': 200,
  'narrative3': 450,
  'narrative4': 300,
  'narrative5': 300,
  'narrative6': 450,
  'cycle_question': 750,
  'two_year_question': 300
}

class QuestionTypes:
  TEXT = 'text'
  SHORT_TEXT = 'short_text'
  NUMBER = 'number'
  PHOTO = 'photo'
  FILE = 'file'

  @classmethod
  def choices(cls):
    return [
      (cls.TEXT, 'Text box'),
      (cls.SHORT_TEXT, 'Single-line text input'),
      (cls.NUMBER, 'Number'),
      (cls.PHOTO, 'Photo upload'),
      (cls.FILE, 'File upload'),
    ]

STANDARD_REPORT_QUESTIONS = [
  {'name': 'contact_info', 'version': 'standard'},
  {'name': 'summarize_last_year', 'version': 'standard'},
  {'name': 'goal_progress', 'version': 'standard'},
  {'name': 'quantitative_measures', 'version': 'standard'},
  {'name': 'evaluation', 'version': 'standard'},
  {'name': 'achievements', 'version': 'standard'},
  {'name': 'collaboration', 'version': 'standard'},
  {'name': 'new_funding', 'version': 'standard'},
  {'name': 'organizational_changes', 'version': 'standard'},
  {'name': 'total_size', 'version': 'standard'},
  {'name': 'donations_count', 'version': 'standard'},
  {'name': 'donations_count_prev', 'version': 'standard'},
  {'name': 'stay_informed', 'version': 'standard'},
  {'name': 'other_comments', 'version': 'standard'},
  {'name': 'photo1', 'version': 'standard'},
  {'name': 'photo2', 'version': 'standard'},
  {'name': 'photo3', 'version': 'standard', 'required': False},
  {'name': 'photo4', 'version': 'standard', 'required': False},
]

RAPID_REPORT_QUESTIONS = [
  {'name': 'progress', 'version': 'rapid_response'},
  {'name': 'impact', 'version': 'rapid_response'},
  {'name': 'current_direction', 'version': 'rapid_response'},
  {'name': 'relation_to_regular_work', 'version': 'rapid_response'},
  {'name': 'more_info_for_members', 'version': 'rapid_response'},
  {'name': 'photo', 'version': 'rapid_response', 'required': False},
  {'name': 'photo_release', 'version': 'general', 'required': False}
]
