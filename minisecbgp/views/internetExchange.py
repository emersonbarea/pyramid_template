from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from wtforms import Form, StringField, SubmitField, SelectField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class InternetExchangePointDataForm(Form):
    internet_exchange_point = StringField('Enter the IX name you want to create, edit or delete: ',
                                          validators=[InputRequired(),
                                                      Length(min=1, max=50,
                                                             message=('Internet eXchange Point name must be between 1 and 50 '
                                                                      'characters long.'))])
    edit_internet_exchange_point = StringField('Enter the new IX name to change the current value: ',
                                               validators=[InputRequired(),
                                                           Length(min=1, max=50,
                                                                  message=('Internet eXchange Point name must be between 1 and 50 '
                                                                           'characters long.'))])
    create_button = SubmitField('Create')
    edit_button = SubmitField('Save')
    delete_button = SubmitField('Delete')


class TopologyRegionDataFormSelectField(Form):
    region_list = SelectField('region_list', coerce=int,
                              validators=[InputRequired()])
    edit_region_list = SelectField('edit_region_list', coerce=int,
                                   validators=[InputRequired()])


@view_config(route_name='internetExchange', renderer='minisecbgp:templates/topology/internetExchange.jinja2')
def internetExchange(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        form = InternetExchangePointDataForm(request.POST)
        dictionary['form'] = form

        form_region = TopologyRegionDataFormSelectField(request.POST)
        form_region.region_list.choices = [(row.id, row.region) for row in
                                           request.dbsession.query(models.Region).filter(
                                               models.Region.id_topology == request.matchdict["id_topology"])]
        form_region.edit_region_list.choices = [(row.id, row.region) for row in
                                                request.dbsession.query(models.Region).filter(
                                                    models.Region.id_topology == request.matchdict["id_topology"])]
        dictionary['form_region'] = form_region

        if request.method == 'POST':

            if form.create_button.data:
                region_name = dict(form_region.region_list.choices).get(form_region.region_list.data)
                region = request.dbsession.query(models.InternetExchangePoint). \
                    filter(models.InternetExchangePoint.id_region == form_region.region_list.data). \
                    filter(models.InternetExchangePoint.internet_exchange_point == form.internet_exchange_point.data).\
                    first()
                if region:
                    dictionary['message'] = 'The Internet eXchange Point %s already exists in the %sern region of the topology.' % \
                                            (form.internet_exchange_point.data, region_name)
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                region = models.InternetExchangePoint(id_topology=request.matchdict["id_topology"],
                                                      id_region=form_region.region_list.data,
                                                      internet_exchange_point=form.internet_exchange_point.data)
                request.dbsession.add(region)
                request.dbsession.flush()
                dictionary['message'] = 'Internet eXchange Point %s successfully created in %sern region of the topology.' % \
                                        (form.internet_exchange_point.data, region_name)
                dictionary['css_class'] = 'successMessage'

            elif form.edit_button.data:
                region_name = dict(form_region.region_list.choices).get(form_region.region_list.data)
                internet_exchange_point = request.dbsession.query(models.InternetExchangePoint). \
                    filter(models.InternetExchangePoint.id_region == form_region.edit_region_list.data). \
                    filter(models.InternetExchangePoint.internet_exchange_point == form.edit_internet_exchange_point.data). \
                    first()
                if internet_exchange_point:
                    dictionary[
                        'message'] = 'The Internet eXchange Point %s already exists in the %sern region of the topology.' % \
                                     (form.edit_internet_exchange_point.data, region_name)
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                internet_exchange_point = request.dbsession.query(models.InternetExchangePoint). \
                    filter(models.InternetExchangePoint.id_region == form_region.region_list.data). \
                    filter(models.InternetExchangePoint.internet_exchange_point == form.internet_exchange_point.data). \
                    first()
                internet_exchange_point.internet_exchange_point = form.edit_internet_exchange_point.data
                internet_exchange_point.id_region = form_region.edit_region_list.data
                request.dbsession.flush()
                dictionary[
                    'message'] = 'Internet eXchange Point %s successfully updated in %sern region of the topology.' % \
                                 (form.internet_exchange_point.data, region_name)
                dictionary['css_class'] = 'successMessage'
            elif form.delete_button.data:
                region_name = dict(form_region.region_list.choices).get(form_region.region_list.data)
                internet_exchange_point = request.dbsession.query(models.InternetExchangePoint.id). \
                    filter(models.InternetExchangePoint.id_topology == request.matchdict["id_topology"]). \
                    filter(models.InternetExchangePoint.id_region == form_region.region_list.data). \
                    filter_by(internet_exchange_point=form.internet_exchange_point.data).first()
                if not internet_exchange_point:
                    dictionary['message'] = 'Internet eXchange Point %s does not exists in the %sern region of the topology.' % \
                                     (form.internet_exchange_point.data, region_name)
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                request.dbsession.query(models.AutonomousSystemInternetExchangePoint). \
                    filter_by(id_internet_exchange_point=internet_exchange_point.id).delete()
                request.dbsession.query(models.InternetExchangePoint). \
                    filter_by(id=internet_exchange_point.id).delete()
                dictionary['message'] = 'Internet eXchange Point %s in the %sern region successfully deleted.' % \
                                        (form.internet_exchange_point.data, region_name)
                dictionary['css_class'] = 'successMessage'

            form_region = TopologyRegionDataFormSelectField()
            form_region.region_list.choices = [(row.id, row.region) for row in
                                               request.dbsession.query(models.Region).filter(
                                                   models.Region.id_topology == request.matchdict["id_topology"])]
            form_region.edit_region_list.choices = [(row.id, row.region) for row in
                                                    request.dbsession.query(models.Region).filter(
                                                        models.Region.id_topology == request.matchdict["id_topology"])]
            dictionary['form_region'] = form_region
            form = InternetExchangePointDataForm()
            dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='internetExchangeShowAll', renderer='minisecbgp:templates/topology/internetExchangeShowAll.jinja2')
def internetExchangeShowAll(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['internet_exchange_point'] = request.dbsession.query(models.InternetExchangePoint, models.Region).\
            filter(models.InternetExchangePoint.id_topology == request.matchdict["id_topology"]).\
            filter(models.InternetExchangePoint.id_region == models.Region.id).\
            order_by(models.InternetExchangePoint.internet_exchange_point.asc()).all()
        dictionary['accordions'] = len(dictionary['internet_exchange_point'])
        dictionary['region'] = request.dbsession.query(models.Region).\
            filter_by(id_topology=request.matchdict["id_topology"]).\
            order_by(models.Region.region.asc()).all()
        dictionary['tabs'] = len(dictionary['region'])
        dictionary['autonomous_systems'] = request.dbsession.query(
            models.InternetExchangePoint, models.AutonomousSystemInternetExchangePoint, models.AutonomousSystem).\
            filter(models.InternetExchangePoint.id_topology == request.matchdict["id_topology"]).\
            filter(models.InternetExchangePoint.id == models.AutonomousSystemInternetExchangePoint.id_internet_exchange_point).\
            filter(models.AutonomousSystemInternetExchangePoint.id_autonomous_system == models.AutonomousSystem.id).all()
        dictionary['number_of_autonomous_systems'] = len(dictionary['autonomous_systems'])

        form = InternetExchangePointDataForm(request.POST)
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
