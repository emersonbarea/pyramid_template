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


@view_config(route_name='typeOfServiceShowAll', renderer='minisecbgp:templates/topology/typeOfServiceShowAll.jinja2')
def typeOfServiceShowAll(request):
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
        number_of_types_of_service = request.dbsession.query(models.TypeOfService).\
            filter_by(id_topology=request.matchdict["id_topology"]).count()
        dictionary['tabs'] = number_of_types_of_service // 10000
        dictionary['number_of_accordions_in_last_tab'] = (number_of_types_of_service % 10000) // 1000
        form = ServiceDataForm(request.POST)
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
