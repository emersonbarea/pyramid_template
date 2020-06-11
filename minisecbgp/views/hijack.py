from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from wtforms import Form, SelectField, TextField, StringField, SubmitField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class AffectedAreaDataForm(Form):

    attacker = SelectField('Choose the <b><i>attacker</i></b> '
                           '(Which AS will announce the hijacked prefix): *',
                           choices=[('', '--'),
                                    ('all', 'All ASs'),
                                    ('region', 'All ASs from a region'),
                                    ('AS', 'Specify the ASN')])
    regionAttacker = StringField('<i>Attacker\'s</i> region name: *',
                                 validators=[InputRequired(),
                                             Length(min=1, max=100, message='Region name string must be between 1 and 100 characters long.')])
    ASAttacker = StringField('<i>Attacker\'s</i> ASN: *',
                             validators=[InputRequired(),
                                         Length(min=1, max=100,
                                                message='ASN string must be between 1 and 100 characters long.')])

    target = SelectField('Choose the <b><i>target</i></b> '
                         '(Check if this AS receives and accepts the hijacked route): *',
                         choices=[('', '--'),
                                  ('all', 'All ASs'),
                                  ('region', 'All ASs from a region'),
                                  ('AS', 'Specify the ASN')])
    regionTarget = StringField('<i>Target\'s</i> region name: *',
                               validators=[InputRequired(),
                                           Length(min=1, max=100, message='Region name string must be between 1 and 100 characters long.')])
    ASTarget = StringField('<i>Target\'s</i> ASN: *',
                           validators=[InputRequired(),
                                       Length(min=1, max=100,
                                              message='ASN string must be between 1 and 100 characters long.')])

    prefix = SelectField('Choose the <b><i>prefix</i></b> '
                         '(Which prefix will be hijacked): *',
                         choices=[('', '--'),
                                  ('all', 'All AS\'s prefixes'),
                                  ('region', 'All AS\'s prefixes from a region'),
                                  ('AS', 'Specific AS\'s prefix'),
                                  ('prefix', 'Choose a prefix')])
    regionPrefix = StringField('Name of the region where all AS\'s prefixes will be hijacked: *',
                               validators=[InputRequired(),
                                           Length(min=1, max=100, message='Region name string must be between 1 and 100 characters long.')])
    ASPrefix = StringField('ASN from which its prefix will be hijacked: *',
                           validators=[InputRequired(),
                                       Length(min=1, max=100,
                                              message='ASN string must be between 1 and 100 characters long.')])
    prefixPrefix = StringField('Specific prefix that will be hijacked: *',
                               validators=[InputRequired(),
                                           Length(min=1, max=100,
                                                  message='Prefix string must be between 1 and 100 characters long.')])
    submit_button = SubmitField('Submit')


@view_config(route_name='hijack', renderer='minisecbgp:templates/hijack/hijackHistory.jinja2')
def hijack(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()

    return dictionary


@view_config(route_name='hijackAffectedArea', renderer='minisecbgp:templates/hijack/hijackAffectedArea.jinja2')
def hijackAffectedArea(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()

    try:
        form = AffectedAreaDataForm(request.POST)

        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='hijackRealisticAnalysis', renderer='minisecbgp:templates/hijack/hijackRealisticAnalysis.jinja2')
def hijackRealisticAnalysis(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()

    return dictionary
