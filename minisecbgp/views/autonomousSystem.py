from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from wtforms import Form, SubmitField, IntegerField, SelectField
from wtforms.validators import InputRequired
from wtforms.widgets.html5 import NumberInput

from minisecbgp import models


class AutonomousSystemDataForm(Form):
    autonomous_system = IntegerField('Add new Autonomous System (only digit a new 16 or 32 bits ASN): ',
                                     widget=NumberInput(min=0, max=4294967295, step=1),
                                     validators=[InputRequired()])
    edit_autonomous_system = IntegerField('Enter a new valid ASN (16 bit or 32 bits ASN) to change the current ASN: ',
                                          widget=NumberInput(min=0, max=4294967295, step=1),
                                          validators=[InputRequired()])
    create_button = SubmitField('Create')
    edit_button = SubmitField('Save')
    delete_button = SubmitField('Delete')


class TopologyRegionDataFormSelectField(Form):
    region_list = SelectField('region_list', coerce=int,
                              validators=[InputRequired()])
    edit_region_list = SelectField('edit_region_list', coerce=int,
                                   validators=[InputRequired()])


@view_config(route_name='autonomousSystem', renderer='minisecbgp:templates/topology/autonomousSystem.jinja2')
def autonomousSystem(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        autonomousSystems = request.dbsession.query(models.AutonomousSystem). \
            filter_by(id_topology=request.matchdict["id_topology"]).\
            order_by(models.AutonomousSystem.autonomous_system.asc()).all()
        dictionary['autonomousSystems'] = autonomousSystems

        form = AutonomousSystemDataForm(request.POST)
        dictionary['form'] = form

        form_region = TopologyRegionDataFormSelectField(request.POST)
        form_region.region_list.choices = [(row.id, row.region) for row in
                                           request.dbsession.query(models.Region).filter(
                                               models.Region.id_topology == request.matchdict["id_topology"])]
        form_region.edit_region_list.choices = [(row.id, row.region) for row in
                                                request.dbsession.query(models.Region).filter(
                                                    models.Region.id_topology == request.matchdict["id_topology"])]
        dictionary['form_region'] = form_region

        if request.method == 'POST' and form.validate():

            if (int(form.autonomous_system.data) > 4294967295) or (int(form.edit_autonomous_system.data) > 4294967295):
                dictionary['message'] = 'Invalid Autonomous System Number. Please enter only 16 bits or 32 bits valid ASN.'
                dictionary['css_class'] = 'errorMessage'
                return dictionary

            if form.create_button.data:

                for autonomousSystemNumber in autonomousSystems:
                    if autonomousSystemNumber.autonomous_system == int(form.autonomous_system.data):
                        dictionary['message'] = 'The Autonomous System Number %s already exists in this topology.' % form.autonomous_system.data
                        dictionary['css_class'] = 'errorMessage'
                        return dictionary
                autonomous_system = models.AutonomousSystem(autonomous_system=form.autonomous_system.data,
                                                            stub=1,
                                                            id_topology=request.matchdict["id_topology"],
                                                            id_region=form_region.region_list.data)
                request.dbsession.add(autonomous_system)
                request.dbsession.flush()
                dictionary[
                    'message'] = 'Autonomous System Number %s successfully created in this topology.' % form.autonomous_system.data
                dictionary['css_class'] = 'successMessage'
                dictionary['form'] = AutonomousSystemDataForm()

            elif form.edit_button.data:

                autonomous_system = request.dbsession.query(models.AutonomousSystem). \
                    filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]). \
                    filter(models.AutonomousSystem.id_region == form_region.region_list.data). \
                    filter_by(autonomous_system=form.autonomous_system.data).first()
                if not autonomous_system:
                    dictionary[
                        'message'] = 'Autonomous System Number %s does not exist in this topology.' % form.autonomous_system.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary

                edit_region_name = dict(form_region.region_list.choices).get(form_region.edit_region_list.data)
                if edit_region_name == '-- undefined region --':
                    edit_region_name = 'undefined region'
                else:
                    edit_region_name = '%sern region' % edit_region_name

                autonomous_system.autonomous_system = form.edit_autonomous_system.data
                autonomous_system.id_region = form_region.edit_region_list.data
                dictionary['message'] = 'Autonomous System Number %s successfully changed to %s in %s.' % \
                                        (form.autonomous_system.data, form.edit_autonomous_system.data, edit_region_name)
                dictionary['css_class'] = 'successMessage'
                dictionary['form'] = AutonomousSystemDataForm()

            elif form.delete_button.data:

                autonomous_system = request.dbsession.query(models.AutonomousSystem.id). \
                    filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]). \
                    filter_by(autonomous_system=form.autonomous_system.data).first()

                if not autonomous_system:
                    dictionary['message'] = 'Autonomous System Number %s does not exist in this topology.' % form.autonomous_system.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary

                request.dbsession.query(models.Prefix). \
                    filter_by(id_autonomous_system=autonomous_system.id).delete()
                request.dbsession.query(models.Link). \
                    filter_by(id_autonomous_system1=autonomous_system.id).delete()
                request.dbsession.query(models.Link). \
                    filter_by(id_autonomous_system2=autonomous_system.id).delete()
                request.dbsession.query(models.AutonomousSystem). \
                    filter_by(id=autonomous_system.id).delete()
                dictionary['message'] = ('Autonomous System Number %s and all of its links and prefixes successfully deleted.'
                                         % form.autonomous_system.data)
                dictionary['css_class'] = 'successMessage'
                dictionary['form'] = AutonomousSystemDataForm()

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