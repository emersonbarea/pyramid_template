from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from wtforms import Form, SelectField, TextField, StringField, SubmitField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class AffectedAreaDataForm(Form):
    attacker = SelectField('Define the <i>attacker</i>: *', choices=[('', '--'),
                                                             ('any', 'Any AS'),
                                                             ('region', 'All ASs from a specific region'),
                                                             ('AS', 'Choose the ASN')])
    regionAttacker = StringField('<i>Attacker</i> region name: *',
                                 validators=[InputRequired(),
                                             Length(min=1, max=100, message='Region name string must be between 1 and 100 characters long.')])
    ASAttacker = StringField('<i>Attacker</i> ASN: *',
                             validators=[InputRequired(),
                                         Length(min=1, max=100,
                                                message='ASN string must be between 1 and 100 characters long.')])
    target = SelectField('Define the <i>target</i>: *', choices=[('', '--'),
                                                                ('any', 'Any AS'),
                                                                ('region', 'All ASs from a specific topology region'),
                                                                ('AS', 'Specify the ASN')])
    regionTarget = StringField('<i>Target</i> region name: *',
                               validators=[InputRequired(),
                                           Length(min=1, max=100, message='Region name string must be between 1 and 100 characters long.')])
    ASTarget = StringField('<i>Target</i> ASN: *',
                           validators=[InputRequired(),
                                       Length(min=1, max=100,
                                              message='ASN string must be between 1 and 100 characters long.')])
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
