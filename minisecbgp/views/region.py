from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
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
                entry = models.Region(region=form.region.data,
                                      id_topology=request.matchdict["id_topology"])
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


@view_config(route_name='regionShowAll', renderer='minisecbgp:templates/topology/regionShowAll.jinja2')
def regionShowAll(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['regions'] = request.dbsession.query(models.Region).\
            filter(models.Region.id_topology == request.matchdict["id_topology"]).\
            filter(models.Region.region != '-- undefined region --').\
            order_by(models.Region.region.asc()).all()
        number_of_regions = request.dbsession.query(models.Region).\
            filter_by(id_topology=request.matchdict["id_topology"]).count()
        dictionary['tabs'] = number_of_regions // 10000
        dictionary['number_of_accordions_in_last_tab'] = (number_of_regions % 10000) // 1000
        form = RegionDataForm(request.POST)
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
