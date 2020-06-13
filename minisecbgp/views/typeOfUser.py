from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from wtforms import Form, SubmitField, StringField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class UserDataForm(Form):
    type_of_user = StringField('Enter the Type of User name you want to create, edit or delete: ',
                               validators=[InputRequired(),
                                           Length(min=1, max=50, message='The Type of User name must be between 1 '
                                                                         'and 50 bytes long (Ex.: Application).')])
    edit_type_of_user = StringField('Enter the new Type of User name you want to edit the current value: ',
                                    validators=[InputRequired(),
                                                Length(min=1, max=50, message='The Type of User name must be between 1 '
                                                                              'and 50 bytes long (Ex.: Application).')])
    create_button = SubmitField('Create')
    edit_button = SubmitField('Save')
    delete_button = SubmitField('Delete')


@view_config(route_name='typeOfUser', renderer='minisecbgp:templates/topology/typeOfUser.jinja2')
def typeOfUser(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        form = UserDataForm(request.POST)
        dictionary['form'] = form

        if request.method == 'POST' and form.validate():

            if form.create_button.data:

                entry = request.dbsession.query(models.TypeOfUser). \
                    filter(models.TypeOfUser.id_topology == request.matchdict["id_topology"]). \
                    filter(func.lower(models.TypeOfUser.type_of_user) == func.lower(form.type_of_user.data)).first()
                if entry:
                    dictionary['message'] = 'Type of User "%s" already exist in this topology.' % form.type_of_user.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                entry = models.TypeOfUser(type_of_user=form.type_of_user.data,
                                          id_topology=request.matchdict["id_topology"])
                request.dbsession.add(entry)
                request.dbsession.flush()
                dictionary['message'] = 'Type of User "%s" successfully created in this topology.' % form.type_of_user.data
                dictionary['css_class'] = 'successMessage'
                dictionary['form'] = UserDataForm()

            elif form.edit_button.data:

                entry = request.dbsession.query(models.TypeOfUser). \
                    filter(models.TypeOfUser.id_topology == request.matchdict["id_topology"]). \
                    filter(func.lower(models.TypeOfUser.type_of_user) == func.lower(form.type_of_user.data)).first()
                if not entry:
                    dictionary['message'] = 'Type of User "%s" does not exist in this topology.' % form.type_of_user.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                edit_type_of_user = request.dbsession.query(models.TypeOfUser). \
                    filter(models.TypeOfUser.id_topology == request.matchdict["id_topology"]). \
                    filter_by(type_of_user=form.edit_type_of_user.data).first()
                if edit_type_of_user:
                    dictionary['message'] = 'Type of User "%s" already exists in this topology.' % form.edit_type_of_user.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                entry.type_of_user = form.edit_type_of_user.data
                dictionary['message'] = 'Type of User "%s" successfully changed to "%s".' % \
                                        (form.type_of_user.data, form.edit_type_of_user.data)
                dictionary['css_class'] = 'successMessage'
                dictionary['form'] = UserDataForm()

            elif form.delete_button.data:

                entry = request.dbsession.query(models.TypeOfUser.id). \
                    filter(models.TypeOfUser.id_topology == request.matchdict["id_topology"]). \
                    filter(func.lower(models.TypeOfUser.type_of_user) == func.lower(form.type_of_user.data)).first()
                if not entry:
                    dictionary['message'] = 'Type of User "%s" does not exist in this topology.' % form.type_of_user.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                try:
                    request.dbsession.query(models.TypeOfUser). \
                        filter_by(id=entry.id).delete()
                    dictionary['message'] = ('Type of User "%s" successfully deleted.' % form.type_of_user.data)
                    dictionary['css_class'] = 'successMessage'
                    dictionary['form'] = UserDataForm()
                except IntegrityError:
                    dictionary['message'] = ('The type of user "%s" cannot be deleted because it is used by some AS. You must resolve this dependency first to delete it.' % form.type_of_user.data)
                    dictionary['css_class'] = 'errorMessage'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='typeOfUserShowAll', renderer='minisecbgp:templates/topology/typeOfUserShowAll.jinja2')
def typeOfUserShowAll(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['type_of_users'] = request.dbsession.query(models.TypeOfUser).\
            filter_by(id_topology=request.matchdict["id_topology"]).\
            order_by(models.TypeOfUser.type_of_user.asc()).all()
        number_of_types_of_user = request.dbsession.query(models.TypeOfUser).\
            filter_by(id_topology=request.matchdict["id_topology"]).count()
        dictionary['tabs'] = number_of_types_of_user // 10000
        dictionary['number_of_accordions_in_last_tab'] = (number_of_types_of_user % 10000) // 1000
        form = UserDataForm(request.POST)
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
