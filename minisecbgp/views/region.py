from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from wtforms import Form, SubmitField, StringField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class RegionDataForm(Form):
    region = StringField('Enter the Region name you want to create, edit or delete: ',
                         validators=[InputRequired(),
                                     Length(min=1, max=50, message='The Region name must be between 1 '
                                                                   'and 50 bytes long (Ex.: IX-IFTO).')])
    edit_region = StringField('Enter the new Region name you want to edit the current value: ',
                              validators=[InputRequired(),
                                          Length(min=1, max=50, message='The Region name must be between 1 and '
                                                                        '50 bytes long (Ex.: IX-IFTO).')])
    create_button = SubmitField('Create')
    edit_button = SubmitField('Save')
    delete_button = SubmitField('Delete')


@view_config(route_name='region', renderer='minisecbgp:templates/topology/region.jinja2')
def region(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        form = RegionDataForm(request.POST)
        dictionary['form'] = form

        if request.method == 'POST' and form.validate():

            if form.region.data == '-- undefined region --':
                dictionary['message'] = '"%s" is a reserved name.' % form.region.data
                dictionary['css_class'] = 'errorMessage'
                return dictionary

            if form.create_button.data:

                entry = request.dbsession.query(models.Region). \
                    filter(models.Region.id_topology == request.matchdict["id_topology"]). \
                    filter_by(region=form.region.data).first()
                if entry:
                    dictionary['message'] = 'Region "%s" already exist in this topology.' % form.region.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary

                id_color = request.dbsession.query(func.max(models.Region.id_color) + 1).\
                    filter_by(id_topology=request.matchdict["id_topology"]).first()

                entry = models.Region(region=form.region.data,
                                      id_topology=request.matchdict["id_topology"],
                                      id_color=id_color)
                request.dbsession.add(entry)
                request.dbsession.flush()
                dictionary['message'] = 'Region "%s" successfully created in this topology.' % form.region.data
                dictionary['css_class'] = 'successMessage'
                dictionary['form'] = RegionDataForm()

            elif form.edit_button.data:

                entry = request.dbsession.query(models.Region). \
                    filter(models.Region.id_topology == request.matchdict["id_topology"]). \
                    filter_by(region=form.region.data).first()
                if not entry:
                    dictionary['message'] = 'Region "%s" does not exist in this topology.' % form.region.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                edit_region = request.dbsession.query(models.Region). \
                    filter(models.Region.id_topology == request.matchdict["id_topology"]). \
                    filter_by(region=form.edit_region.data).first()
                if edit_region:
                    dictionary['message'] = 'Region "%s" already exists in this topology.' % form.edit_region.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                entry.region = form.edit_region.data
                dictionary['message'] = 'Region "%s" successfully changed to "%s".' % \
                                        (form.region.data, form.edit_region.data)
                dictionary['css_class'] = 'successMessage'
                dictionary['form'] = RegionDataForm()

            elif form.delete_button.data:

                entry = request.dbsession.query(models.Region.id). \
                    filter(models.Region.id_topology == request.matchdict["id_topology"]). \
                    filter_by(region=form.region.data).first()
                if not entry:
                    dictionary['message'] = 'Region "%s" does not exist in this topology.' % form.region.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                try:
                    request.dbsession.query(models.Region). \
                        filter_by(id=entry.id).delete()
                    dictionary['message'] = ('Region "%s" successfully deleted.' % form.region.data)
                    dictionary['css_class'] = 'successMessage'
                    dictionary['form'] = RegionDataForm()
                except IntegrityError:
                    dictionary['message'] = ('The region "%s" cannot be deleted because it is used by some AS. You must resolve this dependency first to delete it.' % form.region.data)
                    dictionary['css_class'] = 'errorMessage'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='regionShowAllTxt', renderer='minisecbgp:templates/topology/regionShowAllTxt.jinja2')
def regionShowAllTxt(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['regions'] = request.dbsession.query(models.Region). \
            filter(models.Region.id_topology == request.matchdict["id_topology"]). \
            order_by(models.Region.region.asc()).all()
        query = 'select r.id as id_region, ' \
                'r.region as region, ' \
                'asys.autonomous_system as autonomous_system ' \
                'from region r, ' \
                'autonomous_system asys ' \
                'where r.id_topology = %s ' \
                'and r.id = asys.id_region ' \
                'order by r.id, asys.autonomous_system' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        autonomous_systems_per_region = list()
        for autonomous_system_per_region in result_proxy:
            autonomous_systems_per_region.append({'id_region': autonomous_system_per_region.id_region,
                                                  'region': autonomous_system_per_region.region,
                                                  'autonomous_system': autonomous_system_per_region.autonomous_system})
        dictionary['autonomous_systems_per_region'] = autonomous_systems_per_region

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='regionShowAllHtml', renderer='minisecbgp:templates/topology/regionShowAllHtml.jinja2')
def regionShowAllHtml(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        query = 'select row_number () over (order by r.id) as id_tab, ' \
                'r.id as id_region, ' \
                'r.region as region, ' \
                '(select count(asys.id) ' \
                'from autonomous_system asys ' \
                'where asys.id_region = r.id) as number_of_autonomous_system_per_region ' \
                'from region r ' \
                'where r.id_topology = %s' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        regions = list()
        for region in result_proxy:
            regions.append({'id_tab': region.id_tab,
                            'id_region': region.id_region,
                            'region': region.region,
                            'number_of_accordions_per_region': int(
                                (str(region.number_of_autonomous_system_per_region)[:-3]) if (
                                str(region.number_of_autonomous_system_per_region)[:-3]) else 0),
                            'number_of_autonomous_system_last_accordion_per_region': int(
                                str(region.number_of_autonomous_system_per_region)[-3:]),
                            'number_of_autonomous_system_per_region': region.number_of_autonomous_system_per_region})
        dictionary['regions'] = regions

        query = 'select asys.id_region as id_region, ' \
                'asys.autonomous_system as autonomous_system ' \
                'from autonomous_system asys ' \
                'where asys.id_topology = %s ' \
                'order by asys.autonomous_system' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        autonomous_systems_per_region = list()
        for autonomous_system_per_region in result_proxy:
            autonomous_systems_per_region.append({'id_region': autonomous_system_per_region.id_region,
                                                  'autonomous_system': autonomous_system_per_region.autonomous_system})
        dictionary['autonomous_systems_per_region'] = autonomous_systems_per_region

        dictionary['tabs'] = request.dbsession.query(models.Region).\
            filter_by(id_topology=request.matchdict["id_topology"]).count()

        query = 'select asys.id_region as id_region, ' \
                'count(asys.id) as number_of_autonomous_system ' \
                'from autonomous_system asys ' \
                'where asys.id_topology = %s ' \
                'group by asys.id_region' % request.matchdict["id_topology"]
        dictionary['number_of_autonomous_system_per_region'] = request.dbsession.bind.execute(query)

        form = RegionDataForm(request.POST)
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
