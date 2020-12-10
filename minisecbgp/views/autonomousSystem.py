import ipaddress

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy import or_
from wtforms import Form, SubmitField, IntegerField, SelectField, SelectMultipleField, widgets
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
    create_button = SubmitField('Create', )
    edit_button = SubmitField('Update')
    delete_button = SubmitField('Delete')


class DisplayAutonomousSystemDataForm(Form):
    display_autonomous_system = IntegerField()


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

    def delete(id_autonomous_system):
        type_of_user_autonomous_system = 'delete from type_of_user_autonomous_system ' \
                'where id_autonomous_system = %s' % id_autonomous_system
        request.dbsession.bind.execute(type_of_user_autonomous_system)
        type_of_service_autonomous_system = 'delete from type_of_service_autonomous_system ' \
                                            'where id_autonomous_system = %s' % id_autonomous_system
        request.dbsession.bind.execute(type_of_service_autonomous_system)
        autonomous_system_internet_exchange_point = 'delete from autonomous_system_internet_exchange_point ' \
                                                    'where id_autonomous_system = %s' % id_autonomous_system
        request.dbsession.bind.execute(autonomous_system_internet_exchange_point)

    def insert(internet_exchange_point, type_of_service, type_of_user_form, id_autonomous_system):
        for ixp in internet_exchange_point:
            autonomous_system_internet_exchange_point = 'insert into autonomous_system_internet_exchange_point ' \
                                                        '(id_internet_exchange_point, id_autonomous_system) ' \
                                                        'values (%s, %s)' % (ixp, id_autonomous_system)
            request.dbsession.bind.execute(autonomous_system_internet_exchange_point)
        for tos in type_of_service:
            type_of_service_autonomous_system = 'insert into type_of_service_autonomous_system ' \
                                                '(id_autonomous_system, id_type_of_service) ' \
                                                'values (%s, %s)' % (id_autonomous_system, tos)
            request.dbsession.bind.execute(type_of_service_autonomous_system)
        for name, field in type_of_user_form._fields.items():
            if not field.data == 0:
                type_of_user_autonomous_system = 'insert into type_of_user_autonomous_system ' \
                                                 '(id_autonomous_system, id_type_of_user, number) ' \
                                                 'values (%s, %s, %s)' % \
                                                 (id_autonomous_system, int(field.id.split('_')[3]), field.data)
                request.dbsession.bind.execute(type_of_user_autonomous_system)

    dictionary = dict()
    try:
        form = AutonomousSystemDataForm(request.POST)
        display_autonomous_system_form = DisplayAutonomousSystemDataForm()
        display_autonomous_system_form.display_autonomous_system.data = form.autonomous_system.data

        type_of_users = request.dbsession.query(models.TypeOfUser). \
            filter_by(id_topology=request.matchdict["id_topology"]).all()
        TypeOfUserForm = type_of_user(type_of_users)
        type_of_user_form = TypeOfUserForm(request.POST)

        autonomous_system = request.dbsession.query(models.AutonomousSystem). \
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]). \
            filter_by(autonomous_system=form.autonomous_system.data).first()
        if autonomous_system:
            form = AutonomousSystemDataForm(request.POST, obj=autonomous_system)

        if form.create_button.data:
            try:
                entry = 'insert into autonomous_system (id_topology, id_region, autonomous_system, stub) ' \
                        'values (%s, %s, %s, %s)' % (request.matchdict["id_topology"], form.id_region.data,
                                                     form.autonomous_system.data, True)
                request.dbsession.bind.execute(entry)

                new_autonomous_system = request.dbsession.query(models.AutonomousSystem).\
                    filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]).\
                    filter_by(autonomous_system=form.autonomous_system.data).first()

                insert(form.internet_exchange_point.data, form.type_of_service.data, type_of_user_form,
                       new_autonomous_system.id)

                dictionary['message'] = 'Autonomous System "%s" successfully created.' % form.autonomous_system.data
                dictionary['css_class'] = 'successMessage'
                request.override_renderer = 'minisecbgp:templates/topology/autonomousSystem.jinja2'
                form = AutonomousSystemDataForm()

            except Exception as error:
                request.dbsession.rollback()
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        elif form.edit_button.data:
            try:
                delete(autonomous_system.id)
                insert(form.internet_exchange_point.data, form.type_of_service.data, type_of_user_form,
                       autonomous_system.id)
                region = request.dbsession.query(models.AutonomousSystem).filter_by(id=autonomous_system.id).first()
                region.id_region = form.id_region.data

                dictionary['message'] = 'Autonomous System "%s" successfully updated.' % form.autonomous_system.data
                dictionary['css_class'] = 'successMessage'

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        elif form.delete_button.data:
            try:
                delete(autonomous_system.id)

                request.dbsession.query(models.Prefix). \
                    filter_by(id_autonomous_system=autonomous_system.id).delete()
                request.dbsession.query(models.Link). \
                    filter(or_(models.Link.id_autonomous_system1 == autonomous_system.id,
                               models.Link.id_autonomous_system2 == autonomous_system.id)).delete()
                request.dbsession.query(models.AutonomousSystem). \
                    filter_by(id=autonomous_system.id).delete()

                dictionary['message'] = 'Autonomous System "%s" successfully deleted.' % form.autonomous_system.data
                dictionary['css_class'] = 'successMessage'
                request.override_renderer = 'minisecbgp:templates/topology/autonomousSystem.jinja2'
                form = AutonomousSystemDataForm()

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

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
            for name, field in type_of_user_form._fields.items():
                for touas in type_of_user_autonomous_systems:
                    if touas['id'] == field.id:
                        field.data = touas['number']

            query = 'select la.agreement as agreement, ' \
                    '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                    'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                    '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                    'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                    'l.mask as mask, ' \
                    'l.description as description, ' \
                    'l.bandwidth as bandwidth, ' \
                    'l.delay as delay, ' \
                    'l.load as load ' \
                    'from link l, link_agreement la ' \
                    'where l.id_link_agreement = la.id ' \
                    'and (l.id_autonomous_system1 = %s or l.id_autonomous_system2 = %s) ' \
                    'order by l.id_autonomous_system2;' % (autonomous_system.id, autonomous_system.id)
            result_proxy = request.dbsession.bind.execute(query)
            links = list()
            for link in result_proxy:
                links.append({'autonomous_system1': link.autonomous_system1,
                              'autonomous_system2': link.autonomous_system2,
                              'description': (link.description if link.description else '--'),
                              'ip_autonomous_system1': str(ipaddress.ip_address(link.ip_autonomous_system1)),
                              'ip_autonomous_system2': str(ipaddress.ip_address(link.ip_autonomous_system2)),
                              'mask': '/' + str(link.mask),
                              'bandwidth': (link.bandwidth if link.bandwidth else '--'),
                              'load': (link.load if link.load else '--'),
                              'delay': (link.delay if link.load else '--'),
                              'agreement': link.agreement})
            dictionary['links'] = links

            query = 'select p.prefix as prefix, ' \
                    'p.mask as mask ' \
                    'from prefix p ' \
                    'where p.id_autonomous_system = %s;' % autonomous_system.id
            result_proxy = request.dbsession.bind.execute(query)
            prefixes = list()
            for prefix in result_proxy:
                prefixes.append({'prefix': str(ipaddress.ip_address(prefix.prefix)),
                                 'mask': '/' + str(prefix.mask)})
            dictionary['prefixes'] = prefixes

        else:
            dictionary['header_message'] = 'Create new Autonomous System'

        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['autonomous_system'] = autonomous_system
        dictionary['form'] = form
        dictionary['display_autonomous_system_form'] = display_autonomous_system_form
        dictionary['type_of_user_form'] = type_of_user_form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='autonomousSystemShowAllTxt', renderer='minisecbgp:templates/topology/autonomousSystemShowAllTxt.jinja2')
def autonomousSystemShowAllTxt(request):
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
        form = AutonomousSystemDataForm(request.POST)
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='autonomousSystemShowAllHtml', renderer='minisecbgp:templates/topology/autonomousSystemShowAllHtml.jinja2')
def autonomousSystemShowAllHtml(request):
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
