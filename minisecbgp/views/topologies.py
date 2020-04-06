import math

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


@view_config(route_name='topologies', renderer='minisecbgp:templates/topology/topologiesShow.jinja2')
def topologies(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    all_topologies = request.dbsession.query(models.Topology, models.TopologyType).\
        filter(models.Topology.id_topology_type == models.TopologyType.id).all()
    downloading = request.dbsession.query(models.RealisticTopologyDownloadingCaidaDatabase).first()
    if downloading.downloading == 1:
        message = 'Warning: there is an update process running in the background. ' \
                  'Wait for it finish to see the new topology installed and access topology detail.'
        css_class = 'warningMessage'
        dictionary['message'] = message
        dictionary['css_class'] = css_class

    dictionary['updating'] = downloading.downloading
    dictionary['topologies'] = all_topologies
    dictionary['topologies_url'] = request.route_url('topologies')
    dictionary['topologiesDetail_url'] = request.route_url('topologiesDetail', id_topology='')

    return dictionary


@view_config(route_name='topologiesDetail',
             renderer='minisecbgp:templates/topology/topologiesDetail.jinja2')
def topologiesDetail(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    try:
        topology = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        unique_as = request.dbsession.query(models.AutonomousSystem.id)\
            .filter_by(id_topology=request.matchdict["id_topology"]).count()

        unique_as_stub = request.dbsession.query(models.AutonomousSystem.id) \
            .filter(models.AutonomousSystem.stub == 0) \
            .filter_by(id_topology=request.matchdict["id_topology"]).count()

        query = 'select rta.agreement as agreement, count(l.id) as p2c ' \
                'from link l, realistic_topology_agreement rta ' \
                'where l.id_topology = %s ' \
                'and l.id_agreement = rta.id ' \
                'group by l.id_agreement, rta.agreement;' % request.matchdict["id_topology"]
        p2cs = request.dbsession.bind.execute(query)

        query_stub = 'select count(l.id) as p2c, rta.agreement as agreement ' \
                     'from link l, realistic_topology_agreement rta ' \
                     'where l.id_topology = %s ' \
                     'and l.id_autonomous_system1 in (select id from autonomous_system where id_topology = %s and stub = 0) ' \
                     'and l.id_autonomous_system2 in (select id from autonomous_system where id_topology = %s and stub = 0) ' \
                     'and l.id_agreement = rta.id ' \
                     'group by l.id_agreement, rta.agreement;' % (request.matchdict["id_topology"],
                                                                  request.matchdict["id_topology"],
                                                                  request.matchdict["id_topology"])
        p2cs_stub = request.dbsession.bind.execute(query_stub)

        return {'topology': topology, 'unique_as': unique_as, 'p2cs': p2cs, 'unique_as_stub': unique_as_stub, 'p2cs_stub': p2cs_stub}

    except Exception as error:
        message = 'Error in detailing topology.'
        css_class = 'errorMessage'

        return {'message': message, 'css_class': css_class}


@view_config(route_name='topologiesAction', match_param='action=delete',
             renderer='minisecbgp:templates/topology/topologiesShow.jinja2')
def delete(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        dictionary = dict()
        if request.method == 'POST':
            prefix = 'delete from prefix where id_autonomous_system in (' \
                     'select id from autonomous_system where id_topology = %s);' % request.params['id_topology']
            link = 'delete from link where id_autonomous_system1 in (' \
                   'select id from autonomous_system where id_topology = %s);' % request.params['id_topology']
            autonomous_system = 'delete from autonomous_system where id_topology = %s;' % request.params['id_topology']
            topology = 'delete from topology where id = %s;' % request.params['id_topology']

            request.dbsession.bind.execute(prefix)
            request.dbsession.bind.execute(link)
            request.dbsession.bind.execute(autonomous_system)
            request.dbsession.bind.execute(topology)

            message = ('Topology "%s" successfully deleted.' % request.params['topology'])
            css_class = 'successMessage'
            dictionary['message'] = message
            dictionary['css_class'] = css_class
    except Exception as error:
        message = ('Error to delete topology "%s".' % request.params['topology'])
        css_class = 'errorMessage'
        dictionary['message'] = message
        dictionary['css_class'] = css_class

    return dictionary


@view_config(route_name='topologiesAction', match_param='action=autonomousSystem',
             renderer='minisecbgp:templates/topology/topologiesAutonomousSystem.jinja2')
def autonomousSystem(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        topology = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        autonomousSystems = request.dbsession.query(models.AutonomousSystem).\
            filter_by(id_topology=topology.id).order_by(models.AutonomousSystem.autonomous_system.asc()).all()
        number_of_autonomous_systems = request.dbsession.query(models.AutonomousSystem).\
            filter_by(id_topology=topology.id).count()
        tabs = number_of_autonomous_systems // 10000
        accordions = (number_of_autonomous_systems % 10000) / 1000
        accordions_dec, accordions_int = math.modf(accordions)
        accordions_dec = accordions_dec * 1000
        if accordions > 1:
            print('if')
            accordions_str = format((number_of_autonomous_systems % 10000) / 1000, '.3f')
        else:
            print('else')
            accordions_str = str((accordions % 10000) / 1000)[-3:]

        print('topology', topology.id,
              'number_of_autonomous_systems', number_of_autonomous_systems,
              'tabs', tabs,
              'accordions', accordions,
              'accordions_dec', accordions_dec,
              'accordions_str', accordions_str)

        dictionary = dict()
        dictionary['topology'] = topology
        dictionary['autonomousSystems'] = autonomousSystems
        dictionary['tabs'] = tabs
        dictionary['accordions'] = accordions
        dictionary['accordions_str'] = accordions_str
        dictionary['accordions_int'] = int(accordions_int)
        dictionary['accordions_dec'] = int(accordions_dec)

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
                                                        id_topology=topology.id)
            request.dbsession.add(autonomous_system)
            request.dbsession.flush()
            message = 'The Autonomous System Number %s successfully created in this topology.' % form.autonomous_system.data
            css_class = 'successMessage'
            dictionary['message'] = message
            dictionary['css_class'] = css_class
            url = request.route_url('topologiesAction', action='autonomousSystem', id_topology=topology.id)

            return HTTPFound(location=url)

        return dictionary

    except Exception as error:
        print(error)


@view_config(route_name='topologiesAction', match_param='action=link',
             renderer='minisecbgp:templates/topology/topologiesLink.jinja2')
def link(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        topology = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
    except Exception as error:
        print(error)

    return {'topology': topology}


@view_config(route_name='topologiesAction', match_param='action=prefix',
             renderer='minisecbgp:templates/topology/topologiesPrefix.jinja2')
def prefix(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        topology = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
    except Exception as error:
        print(error)

    return {'topology': topology}
