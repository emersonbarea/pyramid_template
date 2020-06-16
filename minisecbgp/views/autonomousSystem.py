from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from wtforms import Form, SubmitField, IntegerField, SelectField, SelectMultipleField, widgets, StringField
from wtforms.validators import InputRequired
from wtforms.widgets.html5 import NumberInput

from minisecbgp import models


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class AutonomousSystemDataForm(Form):
    autonomous_system = IntegerField('Autonomous System Number: ',
                                     widget=NumberInput(min=0, max=4294967295, step=1),
                                     validators=[InputRequired()])
    id_region = SelectField('Region where the AS is located: *', coerce=int,
                            validators=[InputRequired()])
    internet_exchange_point = MultiCheckboxField('Internet eXchange Point(s) to which the AS is connected: ',
                                                 coerce=int)
    type_of_service = MultiCheckboxField('Autonomous System\'s Type of Service: ',
                                         coerce=int)
    create_button = SubmitField('Create')
    edit_button = SubmitField('Save')
    delete_button = SubmitField('Delete')


def type_of_user(type_of_users):
    form_fields = {}
    for tou in type_of_users:
        field_id = 'type_of_user_{}'.format(tou.id)
        form_fields[field_id] = IntegerField(label=tou.type_of_user + ':',
                                             default=0,
                                             widget=NumberInput(min=0, max=9999999999, step=1),
                                             validators=[InputRequired()])
    return type('TypeOfUser', (Form,), form_fields)


@view_config(route_name='autonomousSystem', renderer='minisecbgp:templates/topology/autonomousSystem.jinja2')
def autonomousSystem(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        form = AutonomousSystemDataForm()
        dictionary['form'] = form

        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='autonomousSystemAddEdit', renderer='minisecbgp:templates/topology/autonomousSystemAddEdit.jinja2')
def autonomousSystemAddEdit(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        form = AutonomousSystemDataForm(request.POST)

        autonomous_system = request.dbsession.query(models.AutonomousSystem).\
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]).\
            filter_by(autonomous_system=form.autonomous_system.data).first()
        form = AutonomousSystemDataForm(request.POST, obj=autonomous_system)

        form.id_region.choices = [(row.id, row.region) for row in
                                  request.dbsession.query(models.Region).filter(
                                      models.Region.id_topology == request.matchdict["id_topology"])]

        query = 'select ixp.id as id, ' \
                'r.region  || \' - \' || ixp.internet_exchange_point as ixp ' \
                'from internet_exchange_point ixp, ' \
                'region r ' \
                'where ixp.id_topology = %s ' \
                'and ixp.id_region = r.id ' \
                'order by ixp' % (request.matchdict["id_topology"])
        form.internet_exchange_point.choices = [(row.id, row.ixp) for row in
                                                request.dbsession.bind.execute(query)]

        type_of_users = request.dbsession.query(models.TypeOfUser).\
            filter_by(id_topology=request.matchdict["id_topology"]).all()
        TypeOfUserForm = type_of_user(type_of_users)
        typeofuserform = TypeOfUserForm(request.POST)

        form.type_of_service.choices = [(row.id, row.type_of_service) for row in
                                        request.dbsession.query(models.TypeOfService).filter(
                                            models.TypeOfService.id_topology == request.matchdict["id_topology"])]

        if autonomous_system:
            dictionary['header_message'] = 'Edit or delete the existing Autonomous System'

            form.id_region.default = autonomous_system.id_region

            checked_ixps = request.dbsession.query(models.AutonomousSystemInternetExchangePoint).\
                filter_by(id_autonomous_system=autonomous_system.id).all()
            list_checked_ixp = list()
            for checked_ixp in checked_ixps:
                list_checked_ixp.append(checked_ixp.id_internet_exchange_point)
            form.internet_exchange_point.default = list_checked_ixp

            checked_toss = request.dbsession.query(models.TypeOfServiceAutonomousSystem).\
                filter_by(id_autonomous_system=autonomous_system.id).all()
            list_checked_tos = list()
            for checked_tos in checked_toss:
                list_checked_tos.append(checked_tos.id_type_of_service)
            form.type_of_service.default = list_checked_tos

            form.process()

            query = 'select \'type_of_user_\' || tou.id as id, ' \
                    'coalesce((select touas.number ' \
                    'from type_of_user_autonomous_system touas ' \
                    'where touas.id_autonomous_system = %s ' \
                    'and touas.id_type_of_user = tou.id), 0) as number ' \
                    'from type_of_user tou ' \
                    'where tou.id_topology = %s' % (autonomous_system.id, request.matchdict["id_topology"])
            result_proxy = request.dbsession.bind.execute(query)
            type_of_user_autonomous_systems = list()
            for row in result_proxy:
                type_of_user_autonomous_systems.append(dict(row))
            for name, field in typeofuserform._fields.items():
                for touas in type_of_user_autonomous_systems:
                    if touas['id'] == field.id:
                        field.data = touas['number']
        else:
            dictionary['header_message'] = 'Create new Autonomous System'

        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['form'] = form
        dictionary['typeofuserform'] = typeofuserform

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='autonomousSystemShowAll', renderer='minisecbgp:templates/topology/autonomousSystemShowAll.jinja2')
def autonomousSystemShowAll(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        autonomousSystems = request.dbsession.query(models.AutonomousSystem, models.Region).\
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]).\
            filter(models.AutonomousSystem.id_region == models.Region.id).\
            order_by(models.AutonomousSystem.autonomous_system.asc()).all()
        dictionary['autonomousSystems'] = autonomousSystems
        number_of_autonomous_systems = request.dbsession.query(models.AutonomousSystem).\
            filter_by(id_topology=request.matchdict["id_topology"]).count()
        dictionary['tabs'] = number_of_autonomous_systems // 10000
        dictionary['number_of_accordions_in_last_tab'] = (number_of_autonomous_systems % 10000) // 1000
        form = AutonomousSystemDataForm(request.POST)
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
