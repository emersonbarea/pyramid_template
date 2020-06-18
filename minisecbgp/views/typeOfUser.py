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


@view_config(route_name='typeOfUserShowAllTxt', renderer='minisecbgp:templates/topology/typeOfUserShowAllTxt.jinja2')
def typeOfUserShowAllTxt(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        query = 'select tou.id as id_type_of_user, ' \
                'tou.type_of_user as type_of_user, ' \
                'coalesce ((select sum(touas.number) ' \
                'from type_of_user_autonomous_system touas ' \
                'where touas.id_type_of_user = tou.id), 0) as total_number_of_user_by_type ' \
                'from type_of_user tou ' \
                'where tou.id_topology = %s ' \
                'order by tou.type_of_user;' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        type_of_users = list()
        for type_of_user in result_proxy:
            type_of_users.append({'id_type_of_user': type_of_user.id_type_of_user,
                                  'type_of_user': type_of_user.type_of_user,
                                  'total_number_of_user_by_type': type_of_user.total_number_of_user_by_type})
        dictionary['type_of_users'] = type_of_users
        dictionary['type_of_user_autonomous_systems'] = request.dbsession.query(models.AutonomousSystem, models.TypeOfUserAutonomousSystem).\
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]).\
            filter(models.AutonomousSystem.id == models.TypeOfUserAutonomousSystem.id_autonomous_system).\
            order_by(models.AutonomousSystem.autonomous_system.asc()).all()
    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='typeOfUserShowAllHtml', renderer='minisecbgp:templates/topology/typeOfUserShowAllHtml.jinja2')
def typeOfUserShowAllHtml(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        query = 'select row_number () over (order by tou.type_of_user) as id_tab, ' \
                'tou.id as id_type_of_user, ' \
                'tou.type_of_user as type_of_user, ' \
                'coalesce ((select sum(touas.number) from type_of_user_autonomous_system touas where touas.id_type_of_user = tou.id), 0) as total_number_of_user_by_type, ' \
                'coalesce ((select count(touas.id_autonomous_system) from type_of_user_autonomous_system touas where touas.id_type_of_user = tou.id), 0) as number_of_autonomous_system_per_type_of_user ' \
                'from type_of_user tou ' \
                'where tou.id_topology = %s;' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        type_of_users = list()
        for type_of_user in result_proxy:
            type_of_users.append({'id_tab': type_of_user.id_tab,
                                  'id_type_of_user': type_of_user.id_type_of_user,
                                  'type_of_user': type_of_user.type_of_user,
                                  'total_number_of_user_by_type': type_of_user.total_number_of_user_by_type,
                                  'number_of_accordions_per_type_of_user': int(
                                      (str(type_of_user.number_of_autonomous_system_per_type_of_user)[:-3]) if (
                                          str(type_of_user.number_of_autonomous_system_per_type_of_user)[:-3]) else 0),
                                  'number_of_autonomous_system_last_accordion_per_type_of_user': int(
                                      str(type_of_user.number_of_autonomous_system_per_type_of_user)[-3:]),
                                  'number_of_autonomous_system_per_type_of_user': type_of_user.number_of_autonomous_system_per_type_of_user})
        dictionary['type_of_users'] = type_of_users

        query = 'select touas.id_type_of_user as id_type_of_user, ' \
                'asys.autonomous_system as autonomous_system, ' \
                'tou.type_of_user as type_of_user, ' \
                'touas.number as number ' \
                'from autonomous_system asys, ' \
                'type_of_user_autonomous_system touas, ' \
                'type_of_user tou ' \
                'where asys.id_topology = %s ' \
                'and asys.id = touas.id_autonomous_system ' \
                'and touas.id_type_of_user = tou.id ' \
                'order by tou.type_of_user, asys.autonomous_system' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        autonomous_systems_per_type_of_user = list()
        for autonomous_system_per_type_of_user in result_proxy:
            autonomous_systems_per_type_of_user.append({'id_type_of_user': autonomous_system_per_type_of_user.id_type_of_user,
                                                        'autonomous_system': autonomous_system_per_type_of_user.autonomous_system,
                                                        'type_of_user': autonomous_system_per_type_of_user.type_of_user,
                                                        'number': autonomous_system_per_type_of_user.number})
        dictionary['autonomous_systems_per_type_of_user'] = autonomous_systems_per_type_of_user

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
