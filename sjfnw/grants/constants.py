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
  {'name': 'collaboration', 'version': 'standard'}
];

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

NARRATIVE_TEXTS = {
  'narrative1':
    'Describe your organization\'s mission, history and major accomplishments.',
  'narrative2': (
    'Social Justice Fund prioritizes groups that are led by the people most '
    'impacted by the issues the group is working on, and continually build '
    'leadership from within their own communities.<ul><li>Who are the '
    'communities most directly impacted by the issues your organization '
    'addresses?</li><li>How are those communities involved in the leadership '
    'of your organization, and how does your organization remain accountable '
    'to those communities?</li><li>What is your organization\'s <span '
    'class="has-more-info" id="nar-2">leadership body?</span></li></ul>'
  ),
  'narrative3': (
    'Social Justice Fund prioritizes groups that understand and address the '
    'underlying, or root causes of the issues, and that bring people together '
    'to build collective power.<ul><li>What problems, needs or issues does '
    'your work address?</li><li>What are the root causes of these issues?</li>'
    '<li>How does your organization build collective power?</li><li>How will '
    'your work change the root causes and underlying power dynamics of the '
    'identified problems, needs or issues?</li></ul>'
  ),
  'narrative4': (
    'Please describe your workplan, covering at least the next 12 months. '
    '(You will list the activities and objectives in the timeline form below.)'
    '<ul><li>What are your overall <span class="has-more-info" id="nar-4">'
    'goals, objectives and strategies</span> for the coming year?</li>'
    '<li>How will you assess whether you have met your goals and objectives?'
    '</li></ul>'
  ),
  'timeline': (
    'Please fill in this timeline to describe your activities over the next five '
    'quarters. This will not exactly match up with the time period funded by '
    'this grant. We are asking for this information to give us an idea of what '
    'your work looks like: what you are doing and how those activities intersect '
    'and build on each other and move you towards your goals. Because our grants '
    'are usually general operating funds, we want to get a sense of what your '
    'organizing work looks like over time. Note: We understand that this '
    'timeline is based only on what you know right now and that circumstances '
    'change. If you receive this grant, you will submit a brief report one year '
    'later, which will ask you what progress you\'ve made on the goals outlined '
    'in this application or, if you changed direction, why.'
  ),
  'narrative5': (
    'Social Justice Fund prioritizes groups that see themselves as part of a '
    'larger movement for social change, and work towards strengthening that '
    'movement.<ul><li>Describe at least two coalitions, collaborations, '
    'partnerships or networks that you participate in as an approach to '
    'social change.</li><li>What are the purposes and impacts of these '
    'collaborations?</li><li>What is your organization\'s role in these '
    'collaborations?</li><li>If your collaborations cross issue or '
    'constituency lines, how will this will help build a broad, unified, and '
    'effective progressive movement?</li></ul>'
  ),
  'narrative6': (
    '<p>Social Justice Fund prioritizes groups working on racial justice, '
    'especially those making connections between racism, economic injustice, '
    'homophobia, and other forms of oppression. Tell us how your organization '
    'is working toward racial justice and how you are drawing connections to '
    'economic injustice, homophobia, and other forms of oppression. While '
    'we believe people of color must lead the struggle for racial justice, '
    'we also realize that the demographics of our region make the work of '
    'white anti-racist allies critical to achieving racial justice. '
    'If your organization\'s <span class="has-more-info" id="nar-6">'
    'leadership body</span> is majority white, also describe how you work as '
    'an ally to communities of color. Be as specific as possible, and list at '
    'least one organization led by people of color that we can contact as a '
    'reference for your racial justice work. Include their name, organization, '
    'phone number and email.</p>'
    '<p><i>Please make sure you have asked permission to list someone as a racial '
    'justice reference before submitting their contact information. Your racial '
    'justice reference cannot be a representative from your organization. We '
    'define "led by people of color" to mean that more that 51% or more of the '
    'organizations leadership body (ie. board of directors or other leadership '
    'model) are people of color. If your organization is majority people of '
    'color led, leave the references blank.</i></p>'
  )
}

# customized question text for Displaced Tenants Fund grant cycle
NARRATIVE_TEXTS_DT = {
  'narrative1': NARRATIVE_TEXTS['narrative1'],
  'narrative2': (
    'The Displaced Tenants Fund for Housing Justice & Affordability prioritizes '
    'groups that are led by people who are directly impacted by lack of '
    'affordable housing in Seattle (in particular people of color, veterans, '
    'LGBTQ, people with disabilities, and low-income people), and continually '
    'builds leadership from within their own communities. '
    '<ol><li>Who are the communities most directly impacted by the housing '
    'issues your organization addresses?</li><li>How are impacted communities '
    'involved in the leadership of your organization? How does your organization '
    'practice accountable community engagement (we understand this as being '
    'responsive, transparent, and serving the best interest of the communities '
    'most affected by housing injustice)?</li><li>What is your organization\'s '
    'leadership body? (Your organization\'s leadership body is the group of people '
    'who together make strategic decisions about the organization\'s direction, '
    'provide oversight and guidance, and are ultimately responsible for the '
    'organization\'s mission and ability to carry out its mission. In most cases, '
    'this will be a Board of Directors, but it might also be a steering committee, '
    'collective, or other leadership structure.)</li></ol>'
  ),
  'narrative3': (
    'The Displaced Tenants Fund for Housing Justice & Affordability prioritizes '
    'groups that understand and address the underlying root causes of housing '
    'injustice, and that bring people most affected together to build collective '
    'power.<ol><li>What specific housing justice problems, needs or issues does '
    'your work address?</li><li>What are the root causes of these issues?</li>'
    '<li>How does your organization build collective power?</li><li>How will '
    'your work make structural change that will affect the root causes and '
    'underlying power dynamics of the identified housing justice problems, needs '
    'or issues?</li></ol>'
  ),
  'narrative4': (
    'Please describe your housing justice work over the next 15 months. (You will '
    'list the activities and objectives in timeline form below this question.)'
  ),
  'narrative5': (
    'The Displaced Tenants Fund for Housing Justice & Affordability prioritizes '
    'groups that see themselves and their work for housing justice as part of a '
    'larger movement for social justice.<ol><li>Describe at least two coalitions, '
    'collaborations, partnerships or networks that you participate in as an approach '
    'to social justice.<li>How do these collaborations strengthen the movement for '
    'housing justice?</li><li>What is your organization\'s role in these '
    'collaborations?</li><li>If your collaborations cross issue or constituency '
    'lines, how this will help build a broad, unified, and winning social justice '
    'movement?</li></ol>'
  ),
  'narrative6': (
    'The Displaced Tenants Fund for Housing Justice & Affordability prioritizes '
    'groups working on racial justice, especially those making connections between '
    'racism and housing justice and can demonstrate an understanding of the '
    'intersections between racial justice, economic justice, LGBTQ justice, '
    'environmental justice, disability justice and other systems of oppression. Tell '
    'us how your organization is working toward racial justice and how you are '
    'drawing connections to racism, housing justice, and other systems of '
    'oppression.'
    '<p>If your organization\'s leadership body is majority white, describe how you '
    'work as an ally and as an accountable community partner to communities of '
    'color. Be as specific as possible, and list at least one organization led by '
    'people of color that we can contact as a reference for your racial justice '
    'work. Include their name, organization, phone number and email.*</p><p><i>* '
    'Please make sure you have asked permission to list someone as a racial '
    'justice reference before submitting their contact information. Your racial '
    'justice reference cannot be a representative from your organization. We '
    'define "led by people of color" to mean that more that 51% or more of the '
    'organizations leadership body (ie. board of directors or other leadership '
    'model) are people of color. If your organization is majority people of '
    'color led, please type N/A for this question.</i></p>'
  )
}

# customized question text for Alternative to Youth Detention grant cycle
NARRATIVE_TEXTS_EPIC = {
  'narrative1': NARRATIVE_TEXTS['narrative1'],
  'narrative2': (
    'The EPIC Zero Detention Project Grant prioritizes groups'
    'that are led by people who are directly impacted by youth detention and '
    'mass incarceration, center youth and families who have been '
    'disproportionately impacted by mass incarceration or the P.I.C. (Prison '
    'Industrial Complex), and continually build leadership from within their own '
    'communities.<ol><li>Who are the communities most directly impacted by your '
    'work?</li><li>How are impacted communities involved in the leadership of '
    'your organization? How does your organization practice accountable '
    'community engagement (we understand this as being responsive, transparent, '
    'and serving the best interest of the communities most affected by youth '
    'incarceration)?</li><li>What is your organization\'s leadership body? (Your '
    'organization\'s leadership body is the group of people who together make '
    'strategic decisions about the organization\'s direction, provide oversight '
    'and guidance, and are ultimately responsible for the organization\'s '
    'mission and ability to carry out its mission. In most cases, this will be a '
    'Board of Directors, but it might also be a steering committee, collective, '
    'or other leadership structure.)</li></ol>'
  ),
  'narrative3': (
    'The EPIC Zero Detention Project Grant prioritizes groups that '
    'understand and address the underlying root causes of the prison industrial '
    'complex, mass incarceration and the school to prison pipeline, and that '
    'bring people most affected together to build collective power.<ol><li>What '
    'specific youth incarceration problems, needs or issues does your work '
    'address?</li><li>What are the root causes of these issues?</li><li>How does '
    'your organization build collective power?</li><li>How will your work make '
    'structural change that will affect the root causes and underlying power '
    'dynamics of the identified youth incarceration problems, needs or '
    'issues?</li></ol>'
  ),
  'narrative4': (
    'Please describe your alternative to youth incarceration work over the next '
    '12 months. (Please list the activities and objectives in timeline form '
    'below this question.)<ol><li>What are your overall goals and strategies '
    'for the next 12 months?</li><li>How will you assess whether you have met '
    'your objectives and goals?</li></ol>'
  ),
  'timeline': NARRATIVE_TEXTS['timeline'].replace('five quarters', 'year'),
  'narrative5': (
    'The EPIC Zero Detention Project Grant prioritizes groups that see '
    'themselves and their work to end youth incarceration as part of a larger '
    'movement for social justice.<ol><li>Describe at least two coalitions, '
    'collaborations, partnerships or networks that you participate in as an '
    'approach to social justice.</li><li>How do these collaborations strengthen '
    'the movement for Black liberation?</li><li>What is your organization\'s role '
    'in these collaborations?</li><li>If your collaborations cross issue or '
    'constituency lines, how this will help build a broad, unified, and winning '
    'social justice movement?</li></ol>'
  ),
  'narrative6': (
    'The EPIC Zero Detention Project Grant prioritizes groups working '
    'on racial justice, especially those making connections between racism and '
    'youth incarceration and can demonstrate an understanding of the '
    'intersections between racial justice, economic justice, LGBTQ justice, '
    'environmental justice, disability justice and other systems of oppression. '
    '<p>If your organization\'s leadership body is majority white, describe how '
    'you work as an ally and as an accountable community partner to communities '
    'of color. Be as specific as possible, and list at least one organization '
    'led by people of color that we can contact as a reference for your racial '
    'justice work. Include their name, organization, phone number and email.*</p>'
    '<p><i>* Please make sure you have asked permission to list someone as a racial '
    'justice reference before submitting their contact information. Your racial '
    'justice reference cannot be a representative from your organization. We '
    'define "led by people of color" to mean that more that 51% or more of the '
    'organizations leadership body (ie. board of directors or other leadership '
    'model) are people of color. If your organization is majority people of '
    'color led, leave the references blank.</i></p>'
  )
}

HELP_TEXTS = {
  'leadership': ('Your organization\'s leadership body is the group of '
      'people who together make strategic decisions about the '
      'organization\'s direction, provide oversight and guidance, and are '
      'ultimately responsible for the organization\'s mission and ability '
      'to carry out its mission. In most cases, this will be a Board of '
      'Directors, but it might also be a steering committee, collective, '
      'or other leadership structure.'),
  'goals': ('<ul><li>A goal is what your organization wants to achieve or '
      'accomplish. You may have both internal goals (how this work will '
      'impact your organization) and external goals (how this work will '
      'impact your broader community).</li><li>An objective is generally '
      'narrower and more specific than a goal, like a stepping stone along '
      'the way.</li><li>A strategy is a road map for achieving your goal. '
      'How will you get there? A strategy will generally encompass '
      'multiple activities or tactics.</li></ul>'),
}
