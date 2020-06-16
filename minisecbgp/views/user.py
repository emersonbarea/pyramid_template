from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy.exc import IntegrityError
from wtforms import (
    Form,
    StringField,
    SelectField,
    PasswordField,
)
from wtforms.validators import (
    InputRequired,
    Length,
    EqualTo
)
from .. import models


class UserDataForm(Form):
    username = StringField('Username: *',
                           validators=[InputRequired(),
                                       Length(min=5, max=30, message=('Username must be between 5 and 30 characters '
                                                                      'long.'))])
    role = SelectField('Role: *',
                       validators=[InputRequired()],
                       choices=[('', ''),
                                ('admin', 'admin'),
                                ('viewer', 'viewer')])

    password_hash = PasswordField('Password: *',
                                  validators=[InputRequired(),
                                              Length(min=5, max=10, message=('Password must be between 5 and 10 '
                                                                             'characters long.'))])
    confirmPassword = PasswordField('Repeat Password: *',
                                    validators=[InputRequired(),
                                                Length(min=5, max=10, message='Password must be between 5 and 10 '
                                                                              'characters long.'),
                                                EqualTo('password_hash', message='Passwords must match.')])


class UserDataFormSelectField(Form):
    user_list = SelectField('user_list', coerce=int,
                            validators=[InputRequired()])


class UserDataFormPassword(Form):
    password_hash = PasswordField('Password: *',
                                  validators=[InputRequired(),
                                              Length(min=5, max=10, message=('Password must be between 5 and 10 '
                                                                             'characters long.'))])
    confirmPassword = PasswordField('Repeat Password: *',
                                    validators=[InputRequired(),
                                                Length(min=5, max=10, message='Password must be between 5 and 10 '
                                                                              'characters long.'),
                                                EqualTo('password_hash', message='Passwords must match.')])


@view_config(route_name='user', renderer='minisecbgp:templates/user/user.jinja2')
def user(request):
    user = request.user
    if user is None:
        raise HTTPForbidden
    return {}


@view_config(route_name='userAction', match_param='action=create', renderer='minisecbgp:templates/user/createUser.jinja2')
def create(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    form = UserDataForm(request.POST)

    if request.method == 'POST' and form.validate():
        try:
            entry = models.User(username=form.username.data,
                                role=form.role.data)
            entry.set_password(form.password_hash.data)
            request.dbsession.add(entry)
            request.dbsession.flush()

            message = ('User account "%s" successfully created.' % form.username.data)
            css_class = 'successMessage'

        except IntegrityError as e:
            request.dbsession.rollback()

            message = ('User account "%s" already exists.' % form.username.data)
            css_class = 'errorMessage'

        request.override_renderer = 'minisecbgp:templates/user/user.jinja2'
        return {'message': message, 'css_class': css_class}

    return {'form': form}


@view_config(route_name='userAction', match_param='action=edit', renderer='minisecbgp:templates/user/editUser.jinja2')
def edit(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    form = UserDataForm(obj=user)

    form_password = UserDataFormPassword(request.POST)

    if request.method == 'POST' and form_password.validate():
        try:
            entry = request.dbsession.query(models.User).filter_by(username=form.username.data).first()
            entry.set_password(form_password.password_hash.data)
            request.dbsession.flush()

            message = ('User account "%s" password successfully updated.' % form.username.data)
            css_class = 'successMessage'

        except IntegrityError as e:
            request.dbsession.rollback()

            message = ('User account "%s" password not updated.' % form.username.data)
            css_class = 'errorMessage'

        request.override_renderer = 'minisecbgp:templates/user/user.jinja2'
        return {'message': message, 'css_class': css_class}

    return {'form': form, 'form_password': form_password}


@view_config(route_name='userAction', match_param='action=delete', renderer='minisecbgp:templates/user/deleteUser.jinja2')
def delete(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    form = UserDataFormSelectField(request.POST)
    form.user_list.choices = [(row.id, row.username)
                              for row in request.dbsession.query(models.User).filter(models.User.username != user.username)]

    if request.method == 'POST' and form.validate():
        value = dict(form.user_list.choices).get(form.user_list.data)
        try:
            request.dbsession.query(models.User).filter(models.User.id == form.user_list.data).delete()

            message = ('User account "%s" successfully deleted.' % value)
            css_class = 'successMessage'

        except IntegrityError as e:
            request.dbsession.rollback()

            message = ('User account "%s" does not exist.' % form.user_list.data)
            css_class = 'errorMessage'

        request.override_renderer = 'minisecbgp:templates/user/user.jinja2'
        return {'message': message, 'css_class': css_class}

    return {'user': user, 'form': form}
