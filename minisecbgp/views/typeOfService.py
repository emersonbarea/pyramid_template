from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from wtforms import Form, SubmitField, StringField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class ServiceDataForm(Form):
    type_of_service = StringField('Enter the Type of Service name you want to create, edit or delete: ',
                                  validators=[InputRequired(),
                                              Length(min=1, max=50, message='The Type of Service name must be between 1 '
                                                                            'and 50 bytes long (Ex.: Application).')])
    edit_type_of_service = StringField('Enter the new Type of Service name you want to edit the current value: ',
                                       validators=[InputRequired(),
                                                   Length(min=1, max=50, message='The Type of Service name must be between 1 '
                                                                                 'and 50 bytes long (Ex.: Application).')])
    create_button = SubmitField('Create')
    edit_button = SubmitField('Save')
    delete_button = SubmitField('Delete')


@view_config(route_name='typeOfService', renderer='minisecbgp:templates/topology/typeOfService.jinja2')
def typeOfService(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        form = ServiceDataForm(request.POST)
        dictionary['form'] = form

        if request.method == 'POST' and form.validate():

            if form.create_button.data:

                entry = request.dbsession.query(models.TypeOfService). \
                    filter(models.TypeOfService.id_topology == request.matchdict["id_topology"]). \
                    filter(func.lower(models.TypeOfService.type_of_service) == func.lower(form.type_of_service.data)).first()
                if entry:
                    dictionary['message'] = 'Type of Service "%s" already exist in this topology.' % form.type_of_service.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                entry = models.TypeOfService(type_of_service=form.type_of_service.data,
                                             id_topology=request.matchdict["id_topology"])
                request.dbsession.add(entry)
                request.dbsession.flush()
                dictionary['message'] = 'Type of Service "%s" successfully created in this topology.' % form.type_of_service.data
                dictionary['css_class'] = 'successMessage'
                dictionary['form'] = ServiceDataForm()

            elif form.edit_button.data:

                entry = request.dbsession.query(models.TypeOfService). \
                    filter(models.TypeOfService.id_topology == request.matchdict["id_topology"]). \
                    filter(func.lower(models.TypeOfService.type_of_service) == func.lower(form.type_of_service.data)).first()
                if not entry:
                    dictionary['message'] = 'Type of Service "%s" does not exist in this topology.' % form.type_of_service.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                edit_type_of_service = request.dbsession.query(models.TypeOfService). \
                    filter(models.TypeOfService.id_topology == request.matchdict["id_topology"]). \
                    filter_by(type_of_service=form.edit_type_of_service.data).first()
                if edit_type_of_service:
                    dictionary['message'] = 'Type of Service "%s" already exists in this topology.' % form.edit_type_of_service.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                entry.type_of_service = form.edit_type_of_service.data
                dictionary['message'] = 'Type of Service "%s" successfully changed to "%s".' % \
                                        (form.type_of_service.data, form.edit_type_of_service.data)
                dictionary['css_class'] = 'successMessage'
                dictionary['form'] = ServiceDataForm()

            elif form.delete_button.data:

                entry = request.dbsession.query(models.TypeOfService.id). \
                    filter(models.TypeOfService.id_topology == request.matchdict["id_topology"]). \
                    filter(func.lower(models.TypeOfService.type_of_service) == func.lower(form.type_of_service.data)).first()
                if not entry:
                    dictionary['message'] = 'Type of Service "%s" does not exist in this topology.' % form.type_of_service.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                try:
                    request.dbsession.query(models.TypeOfService). \
                        filter_by(id=entry.id).delete()
                    dictionary['message'] = ('Type of Service "%s" successfully deleted.' % form.type_of_service.data)
                    dictionary['css_class'] = 'successMessage'
                    dictionary['form'] = ServiceDataForm()
                except IntegrityError:
                    dictionary['message'] = ('The service "%s" cannot be deleted because it is used by some AS. You must resolve this dependency first to delete it.' % form.type_of_service.data)
                    dictionary['css_class'] = 'errorMessage'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='typeOfServiceShowAllTxt', renderer='minisecbgp:templates/topology/typeOfServiceShowAllTxt.jinja2')
def typeOfServiceShowAllTxt(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['type_of_services'] = request.dbsession.query(models.TypeOfService).\
            filter_by(id_topology=request.matchdict["id_topology"]).\
            order_by(models.TypeOfService.type_of_service.asc()).all()
        dictionary['autonomous_systems'] = request.dbsession.query(models.AutonomousSystem, models.TypeOfServiceAutonomousSystem).\
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]).\
            filter(models.AutonomousSystem.id == models.TypeOfServiceAutonomousSystem.id_autonomous_system).all()

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='typeOfServiceShowAllHtml', renderer='minisecbgp:templates/topology/typeOfServiceShowAllHtml.jinja2')
def typeOfServiceShowAllHtml(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        query = 'select row_number () over (order by tos.type_of_service) as id_tab, ' \
                'tos.id as id_type_of_service, ' \
                'tos.type_of_service as type_of_service, ' \
                'coalesce ((select count(tosas.id_autonomous_system) from type_of_service_autonomous_system tosas where tosas.id_type_of_service = tos.id), 0) as number_of_autonomous_system_per_type_of_service ' \
                'from type_of_service tos ' \
                'where tos.id_topology = %s;' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        type_of_services = list()
        for type_of_service in result_proxy:
            type_of_services.append({'id_tab': type_of_service.id_tab,
                                     'id_type_of_service': type_of_service.id_type_of_service,
                                     'type_of_service': type_of_service.type_of_service,
                                     'number_of_accordions_per_type_of_service': int(
                                         (str(type_of_service.number_of_autonomous_system_per_type_of_service)[:-3]) if (
                                             str(type_of_service.number_of_autonomous_system_per_type_of_service)[:-3]) else 0),
                                     'number_of_autonomous_system_last_accordion_per_type_of_service': int(
                                         str(type_of_service.number_of_autonomous_system_per_type_of_service)[-3:]),
                                     'number_of_autonomous_system_per_type_of_service': type_of_service.number_of_autonomous_system_per_type_of_service})
        dictionary['type_of_services'] = type_of_services

        query = 'select tosas.id_type_of_service as id_type_of_service, ' \
                'asys.autonomous_system as autonomous_system, ' \
                'tos.type_of_service as type_of_service ' \
                'from autonomous_system asys, ' \
                'type_of_service_autonomous_system tosas, ' \
                'type_of_service tos ' \
                'where asys.id_topology = %s ' \
                'and asys.id = tosas.id_autonomous_system ' \
                'and tosas.id_type_of_service = tos.id ' \
                'order by tos.type_of_service, asys.autonomous_system' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        autonomous_systems_per_type_of_service = list()
        for autonomous_system_per_type_of_service in result_proxy:
            autonomous_systems_per_type_of_service.append(
                {'id_type_of_service': autonomous_system_per_type_of_service.id_type_of_service,
                 'autonomous_system': autonomous_system_per_type_of_service.autonomous_system,
                 'type_of_service': autonomous_system_per_type_of_service.type_of_service})
        dictionary['autonomous_systems_per_type_of_service'] = autonomous_systems_per_type_of_service

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
