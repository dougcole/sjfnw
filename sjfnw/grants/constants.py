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
  ('Sponsored', 'Sponsored by a 501(c)3, 501(c)4, or federally recognized tribal government')
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
  (110, 'Year-end report overdue'),
  (120, 'Year-end report received'),
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
