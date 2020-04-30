import subprocess

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
    downloading = request.dbsession.query(models.DownloadingTopology).first()
    if downloading.downloading == 1:
        dictionary['message'] = 'Warning: there is an update process running in the background. ' \
                  'Wait for it finish to see the new topology installed and access topology detail.'
        dictionary['css_class'] = 'warningMessage'
    dictionary['updating'] = downloading.downloading
    dictionary['topologies'] = all_topologies
    dictionary['topologies_url'] = request.route_url('topologies')
    dictionary['topologiesDetail_url'] = request.route_url('topologiesDetail', id_topology='')

    return dictionary


@view_config(route_name='topologiesAgreement', renderer='minisecbgp:templates/topology/topologiesLinksAgreements.jinja2')
def topologies_agreement(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    dictionary['agreements'] = request.dbsession.query(models.LinkAgreement).all()

    return dictionary


@view_config(route_name='topologiesDetail', renderer='minisecbgp:templates/topology/topologiesDetail.jinja2')
def topologies_detail(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        dictionary['unique_as'] = request.dbsession.query(models.AutonomousSystem.id)\
            .filter_by(id_topology=request.matchdict["id_topology"]).count()

        dictionary['unique_as_stub'] = request.dbsession.query(models.AutonomousSystem.id) \
            .filter(models.AutonomousSystem.stub == 0) \
            .filter_by(id_topology=request.matchdict["id_topology"]).count()

        query = 'select la.agreement as agreement, ' \
                '(select count(l.id) ' \
                'from link l ' \
                'where l.id_topology = %s ' \
                'and l.id_link_agreement = la.id) as p2c ' \
                'from link_agreement la ' \
                'group by la.id, la.agreement;' % request.matchdict["id_topology"]
        dictionary['p2cs'] = request.dbsession.bind.execute(query)

        query = 'select la.agreement as agreement, ' \
                '(select count(l.id) ' \
                'from link l ' \
                'where l.id_topology = %s ' \
                'and l.id_link_agreement = la.id ' \
                'and l.id_autonomous_system1 in (select id ' \
                'from autonomous_system ' \
                'where id_topology = %s ' \
                'and stub = 0) ' \
                'and l.id_autonomous_system2 in (select id ' \
                'from autonomous_system ' \
                'where id_topology = %s ' \
                'and stub = 0)) as p2c ' \
                'from link_agreement la ' \
                'group by la.id, la.agreement;' % (request.matchdict["id_topology"],
                                                   request.matchdict["id_topology"],
                                                   request.matchdict["id_topology"])
        dictionary['p2cs_stub'] = request.dbsession.bind.execute(query)

        dictionary['prefixes'] = request.dbsession.query(models.AutonomousSystem, models.Prefix). \
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]). \
            filter(models.AutonomousSystem.id == models.Prefix.id_autonomous_system).count()

        dictionary['prefixes_stub'] = request.dbsession.query(models.Prefix, models.AutonomousSystem).\
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]). \
            filter(models.AutonomousSystem.stub == 0). \
            filter(models.AutonomousSystem.id == models.Prefix.id_autonomous_system).count()

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='topologiesAction', match_param='action=delete',
             renderer='minisecbgp:templates/topology/topologiesShow.jinja2')
def topologies_delete(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    try:
        if request.method == 'POST':
            arguments = ['--id_topology=%s' % request.matchdict["id_topology"]]
            subprocess.Popen(['./venv/bin/delete_topology'] + arguments)

            dictionary['message'] = ('Topology "%s" successfully deleted.' % request.params['topology'])
            dictionary['css_class'] = 'successMessage'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
