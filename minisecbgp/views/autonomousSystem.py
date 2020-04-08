from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from wtforms import Form, StringField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class AutonomousSystemDataForm(Form):
    autonomous_system = StringField('Add new Autonomous System (only digit a new 16 or 32 bits ASN): ',
                                    validators=[InputRequired(),
                                                Length(min=1, max=32, message=('Autonomous System Number must be between 1 and 32 '
                                                                               'characters long.'))])


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

        if request.method == 'POST' and form.validate():
            for autonomousSystemNumber in autonomousSystems:
                if autonomousSystemNumber.autonomous_system == int(form.autonomous_system.data):
                    message = 'The Autonomous System Number already exists in this topology.'
                    css_class = 'errorMessage'
                    dictionary['message'] = message
                    dictionary['css_class'] = css_class
                    return dictionary

            autonomous_system = models.AutonomousSystem(autonomous_system=form.autonomous_system.data,
                                                        stub=1,
                                                        id_topology=request.matchdict["id_topology"])
            request.dbsession.add(autonomous_system)
            request.dbsession.flush()
            dictionary['message'] = 'Autonomous System Number %s successfully created in this topology.' % form.autonomous_system.data
            dictionary['css_class'] = 'successMessage'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='autonomousSystemAction', match_param='action=showAll',
             renderer='minisecbgp:templates/topology/autonomousSystemShowAll.jinja2')
def autonomousSystemShowAll(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        autonomousSystems = request.dbsession.query(models.AutonomousSystem).\
            filter_by(id_topology=request.matchdict["id_topology"]).\
            order_by(models.AutonomousSystem.autonomous_system.asc()).all()
        dictionary['autonomousSystems'] = autonomousSystems
        number_of_autonomous_systems = request.dbsession.query(models.AutonomousSystem).\
            filter_by(id_topology=request.matchdict["id_topology"]).count()
        dictionary['tabs'] = number_of_autonomous_systems // 10000
        dictionary['number_of_accordions_in_last_tab'] = (number_of_autonomous_systems % 10000) // 1000
        form = AutonomousSystemDataForm(request.POST)
        dictionary['form'] = form

        if request.method == 'POST' and form.validate():
            for autonomousSystemNumber in autonomousSystems:
                if autonomousSystemNumber.autonomous_system == int(form.autonomous_system.data):
                    message = 'The Autonomous System Number informed already exists in this topology.'
                    css_class = 'errorMessage'
                    dictionary['message'] = message
                    dictionary['css_class'] = css_class
                    return dictionary

            autonomous_system = models.AutonomousSystem(autonomous_system=form.autonomous_system.data,
                                                        stub=1,
                                                        id_topology=request.matchdict["id_topology"])
            request.dbsession.add(autonomous_system)
            request.dbsession.flush()
            dictionary['message'] = 'The Autonomous System Number %s successfully created in this topology.' % form.autonomous_system.data
            dictionary['css_class'] = 'successMessage'
            url = request.route_url('topologiesAction', action='autonomousSystem', id_topology=request.matchdict["id_topology"])

            return HTTPFound(location=url)

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='autonomousSystemAction', match_param='action=delete',
             renderer='minisecbgp:templates/topology/autonomousSystem.jinja2')
def autonomousSystemDelete(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['form'] = AutonomousSystemDataForm(request.POST)
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        print('topology', request.matchdict["id_topology"], 'AS', request.matchdict["id_autonomous_system"])

        autonomous_system = request.dbsession.query(models.AutonomousSystem.id).\
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]).\
            filter_by(autonomous_system=request.matchdict["id_autonomous_system"]).first()

        request.dbsession.query(models.Prefix).\
            filter_by(id_autonomous_system=autonomous_system.id).delete()

        request.dbsession.query(models.Link).\
            filter_by(id_autonomous_system1=autonomous_system.id).delete()

        request.dbsession.query(models.Link). \
            filter_by(id_autonomous_system2=autonomous_system.id).delete()

        request.dbsession.query(models.AutonomousSystem).\
            filter_by(id=autonomous_system.id).delete()

        dictionary['message'] = ('Autonomous System %s and all of its links and prefixes successfully deleted.'
                                 % request.matchdict["id_autonomous_system"])
        dictionary['css_class'] = 'successMessage'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
