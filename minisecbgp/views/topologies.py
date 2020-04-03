from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden

from minisecbgp import models


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
    dictionary['realisticTopologies_url'] = request.route_url('realisticTopologies')
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








        

        return {'topology': topology}

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

    pass

    return {}


@view_config(route_name='topologiesAction', match_param='action=link',
             renderer='minisecbgp:templates/topology/topologiesLink.jinja2')
def link(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    pass

    return {}


@view_config(route_name='topologiesAction', match_param='action=prefix',
             renderer='minisecbgp:templates/topology/topologiesPrefix.jinja2')
def prefix(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    pass

    return {}
