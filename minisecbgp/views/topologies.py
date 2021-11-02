import os
import subprocess
import tarfile

from pyramid.response import FileResponse
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from wtforms import Form, SubmitField, StringField
from wtforms.validators import Length, InputRequired

from minisecbgp import models


class TopologiesDetailDataForm(Form):
    topology_name = StringField('Type the name for the new topology: ',
                                validators=[InputRequired(),
                                            Length(min=1, max=255,
                                                   message='Topology name string must be between 1 and 255 characters long.')])
    download_button = SubmitField('Download')
    duplicate_button = SubmitField('Duplicate Topology')
    delete_button = SubmitField('Delete Topology')
    emulate_button = SubmitField('Confirm')


@view_config(route_name='topologies', renderer='minisecbgp:templates/topology/topologiesShow.jinja2')
def topologies(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    topology_types = request.dbsession.query(models.TopologyType).\
        order_by(models.TopologyType.id).all()
    topologies = request.dbsession.query(models.Topology, models.TopologyType).\
        filter(models.Topology.id_topology_type == models.TopologyType.id).all()
    downloading = request.dbsession.query(models.DownloadingTopology).first()
    if downloading.downloading == 1:
        dictionary['message'] = 'Warning: there is an update process running in the background. ' \
                  'Wait for it finish to see the new topology installed and access topology detail.'
        dictionary['css_class'] = 'warningMessage'
    dictionary['updating'] = downloading.downloading
    dictionary['topology_types'] = topology_types
    dictionary['topologies'] = topologies
    dictionary['topologies_url'] = request.route_url('topologies')
    dictionary['topologiesDetail_url'] = request.route_url('topologiesDetail', id_topology='')

    return dictionary


@view_config(route_name='topologiesAgreement', renderer='minisecbgp:templates/topology/topologiesLinksAgreements.jinja2')
def topologies_agreement(request):
    user = request.user
    if user is None:
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
    form = TopologiesDetailDataForm(request.POST)

    if request.method == 'POST' and form.validate():

        if form.download_button.data:
            realistic_analysis = request.dbsession.query(models.RealisticAnalysis).\
                filter_by(id_topology=request.matchdict['id_topology']).first()
            query = 'select t.topology ' \
                    'from topology t ' \
                    'where t.id = %s;' % request.matchdict['id_topology']
            topology_name = list(request.dbsession.bind.execute(query))[0][0]

            source_dir = str(realistic_analysis.output_path[:-1])
            output_filename = topology_name + '.tar.gz'

            with tarfile.open(source_dir + '/' + output_filename, "w:gz") as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))

            response = FileResponse(source_dir + '/' + output_filename)
            response.headers['Content-Disposition'] = "attachment; filename=%s" % output_filename
            return response

        elif form.duplicate_button.data:
            topology_already_exist = request.dbsession.query(models.Topology).\
                filter_by(topology=form.topology_name.data).first()

            if topology_already_exist:
                dictionary['message'] = 'The topology name you choose already exist (%s). Please choose another name and try again.' % form.topology_name.data
                dictionary['css_class'] = 'errorMessage'
            else:
                arguments = ['--config-file=minisecbgp.ini',
                             '--topology=%s' % request.matchdict["id_topology"],
                             '--new-topology-name=%s' % form.topology_name.data]
                result = subprocess.Popen(['./venv/bin/MiniSecBGP_duplicate_topology'] + arguments,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                command_result, command_result_error = result.communicate()
                if command_result:
                    dictionary['message'] = command_result
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                url = request.route_url('topologies')
                return HTTPFound(location=url)

        elif form.delete_button.data:
            return HTTPFound(location=request.route_url('topologiesAction', action='delete', id_topology=request.matchdict['id_topology']))

        elif form.emulate_button.data:
            output_path = request.dbsession.query(models.RealisticAnalysis.output_path).\
                filter_by(id_topology=request.matchdict["id_topology"]).first()
            os.system('gnome-terminal -- /bin/bash -c "cd %s; ./topology.py; exec bash"' %
                      str(output_path[0]).replace(' ', '\ '))

    dictionary['form'] = form

    try:
        dictionary['topology'] = request.dbsession.query(models.Topology).\
            filter_by(id=request.matchdict["id_topology"]).first()

        dictionary['unique_as'] = request.dbsession.query(models.AutonomousSystem.id).\
            filter_by(id_topology=request.matchdict["id_topology"]).count()

        dictionary['unique_as_stub'] = request.dbsession.query(models.AutonomousSystem.id).\
            filter(models.AutonomousSystem.stub.is_(False)).\
            filter_by(id_topology=request.matchdict["id_topology"]).count()

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
                'and not stub) ' \
                'and l.id_autonomous_system2 in (select id ' \
                'from autonomous_system ' \
                'where id_topology = %s ' \
                'and not stub)) as p2c ' \
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
            filter(models.AutonomousSystem.stub.is_(False)). \
            filter(models.AutonomousSystem.id == models.Prefix.id_autonomous_system).count()

        query = 'select eb.start_datetime as start_datetime, ' \
                'eb.end_datetime as end_datetime, ' \
                'eb.restrict_mode ' \
                'from event_behaviour eb ' \
                'where eb.id_topology = %s;' % request.matchdict["id_topology"]
        dictionary['event_behaviour'] = list(request.dbsession.bind.execute(query))

        query = 'select b.resource as resource, ' \
                'b.url as url ' \
                'from bgplay b ' \
                'where b.id_event_behaviour = (' \
                'select eb.id ' \
                'from event_behaviour eb ' \
                'where eb.id_topology = %s);' % request.matchdict["id_topology"]
        dictionary['bgplay'] = list(request.dbsession.bind.execute(query))

        query = 'select event_datetime as event_datetime, ' \
                'prefix as prefix, ' \
                'announcer as announcer ' \
                'from event_announcement ea ' \
                'where ea.id_event_behaviour = (' \
                'select eb.id ' \
                'from event_behaviour eb ' \
                'where eb.id_topology = %s)' \
                'order by event_datetime;' % request.matchdict["id_topology"]
        dictionary['events_announcement'] = list(request.dbsession.bind.execute(query))

        query = 'select event_datetime as event_datetime, ' \
                'in_out as in_out, ' \
                'prefix as prefix, ' \
                'withdrawer as withdrawer, ' \
                'peer as peer, ' \
                'withdrawn as withdrawn ' \
                'from event_withdrawn ew ' \
                'where ew.id_event_behaviour = (' \
                'select eb.id ' \
                'from event_behaviour eb ' \
                'where eb.id_topology = %s)' \
                'order by event_datetime;' % request.matchdict["id_topology"]
        dictionary['events_withdrawn'] = list(request.dbsession.bind.execute(query))

        query = 'select event_datetime as event_datetime, ' \
                'in_out as in_out, ' \
                'prefix as prefix, ' \
                'prepender as prepender, ' \
                'prepended as prepended, ' \
                'peer as peer, ' \
                'hmt as hmt ' \
                'from event_prepend ep ' \
                'where ep.id_event_behaviour = (' \
                'select eb.id ' \
                'from event_behaviour eb ' \
                'where eb.id_topology = %s)' \
                'order by event_datetime;' % request.matchdict["id_topology"]
        dictionary['events_prepend'] = list(request.dbsession.bind.execute(query))

        query = 'select em.event_datetime as event_datetime, ' \
                'em.monitor as monitor, ' \
                'em.all as all, ' \
                'em.sleep_time ' \
                'from event_monitoring em ' \
                'where em.id_event_behaviour = (' \
                'select eb.id ' \
                'from event_behaviour eb ' \
                'where eb.id_topology = %s)' \
                'order by event_datetime;' % request.matchdict["id_topology"]
        dictionary['events_monitoring'] = list(request.dbsession.bind.execute(query))

        query = 'select ra.include_stub as include_stub, ' \
                '(select tdm.topology_distribution_method ' \
                'from topology_distribution_method tdm ' \
                'where tdm.id = ra.id_topology_distribution_method) as topology_distribution_method, ' \
                '(select ep.emulation_platform ' \
                'from emulation_platform ep ' \
                'where ep.id = ra.id_emulation_platform) as emulation_platform, ' \
                '(select rp.router_platform ' \
                'from router_platform rp ' \
                'where rp.id = ra.id_router_platform) as router_platform, ' \
                'ra.output_path as output_path, ' \
                'ra.time_get_data as time_get_data, ' \
                'ra.time_autonomous_system_per_server as time_autonomous_system_per_server, ' \
                'ra.time_emulate_platform_commands as time_emulate_platform_commands, ' \
                'ra.time_router_platform_commands as time_router_platform_commands, ' \
                'ra.time_write_files as time_write_files, ' \
                'ra.time_copy_files as time_copy_files, ' \
                'cast(ra.time_get_data as float) + ' \
                'cast(ra.time_autonomous_system_per_server as float) + ' \
                'cast(ra.time_emulate_platform_commands as float) + ' \
                'cast(ra.time_router_platform_commands as float) + ' \
                'cast(ra.time_write_files as float) + ' \
                'cast(ra.time_copy_files as float) as total_time ' \
                'from realistic_analysis ra ' \
                'where ra.id_topology = %s;' % request.matchdict["id_topology"]
        dictionary['realistic_analysis'] = list(request.dbsession.bind.execute(query))

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
        if request.matchdict.get('id_topology'):

            topology = request.dbsession.query(models.Topology.topology).\
                filter_by(id=request.matchdict["id_topology"]).first()

            arguments = ['--config-file=minisecbgp.ini',
                         '--topology=%s' % request.matchdict["id_topology"]]
            subprocess.Popen(['./venv/bin/MiniSecBGP_delete_topology'] + arguments)

            dictionary['message'] = ('Topology "%s" successfully deleted.' % topology.topology)
            dictionary['css_class'] = 'successMessage'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='topologiesAction', match_param='action=draw',
             renderer='minisecbgp:templates/topology/topologiesDraw.jinja2')
def topologies_draw(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()

    try:
        topology = request.dbsession.query(models.Topology).\
            filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['topology'] = topology

        query = 'select asys.id as id, ' \
                'asys.autonomous_system as label, ' \
                'r.region as region, ' \
                'c.background_color as background_color, ' \
                'c.text_color as text_color ' \
                'from autonomous_system asys, ' \
                'region r, ' \
                'color c ' \
                'where asys.id_topology = %s ' \
                'and asys.id_region = r.id ' \
                'and r.id_color = c.id' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        autonomous_systems = list()
        for autonomous_system in result_proxy:
            autonomous_systems.append({'id': autonomous_system.id,
                                       'label': autonomous_system.label,
                                       'region': autonomous_system.region,
                                       'background_color': autonomous_system.background_color,
                                       'text_color': autonomous_system.text_color})
        dictionary['nodes'] = autonomous_systems

        query = 'select r.region as region, ' \
                'c.background_color as background_color, ' \
                'c.text_color as text_color ' \
                'from region r, ' \
                'color c ' \
                'where r.id_topology = %s ' \
                'and r.id_color = c.id' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        regions_group = list()
        for region_group in result_proxy:
            regions_group.append({'region': region_group.region,
                                  'background_color': region_group.background_color,
                                  'text_color': region_group.text_color})
        dictionary['regions_group'] = regions_group

        links = request.dbsession.query(models.Link).\
            filter_by(id_topology=request.matchdict["id_topology"]).all()
        dictionary['edges'] = links
        dictionary['full_stub'] = 'FULL TOPOLOGY'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='topologiesAction', match_param='action=drawStub',
             renderer='minisecbgp:templates/topology/topologiesDraw.jinja2')
def topologies_draw_stub(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()

    try:
        topology = request.dbsession.query(models.Topology).\
            filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['topology'] = topology

        query = 'select asys.id as id, ' \
                'asys.autonomous_system as label, ' \
                'r.region as region, ' \
                'c.background_color as background_color, ' \
                'c.text_color as text_color ' \
                'from autonomous_system asys, ' \
                'region r, ' \
                'color c ' \
                'where asys.id_topology = %s ' \
                'and not asys.stub ' \
                'and asys.id_region = r.id ' \
                'and r.id_color = c.id' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        autonomous_systems = list()
        for autonomous_system in result_proxy:
            autonomous_systems.append({'id': autonomous_system.id,
                                       'label': autonomous_system.label,
                                       'region': autonomous_system.region,
                                       'background_color': autonomous_system.background_color,
                                       'text_color': autonomous_system.text_color})
        dictionary['nodes'] = autonomous_systems

        query = 'select r.region as region, ' \
                'c.background_color as background_color, ' \
                'c.text_color as text_color ' \
                'from region r, ' \
                'color c ' \
                'where r.id_topology = %s ' \
                'and r.id_color = c.id' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        regions_group = list()
        for region_group in result_proxy:
            regions_group.append({'region': region_group.region,
                                  'background_color': region_group.background_color,
                                  'text_color': region_group.text_color})
        dictionary['regions_group'] = regions_group

        query = 'select distinct ' \
                'l.id_autonomous_system1 as id_autonomous_system1, ' \
                'l.id_autonomous_system2 as id_autonomous_system2, ' \
                'l.id_link_agreement ' \
                'from autonomous_system asys, ' \
                'link l ' \
                'where asys.id_topology = %s ' \
                'and not asys.stub ' \
                'and (asys.id = l.id_autonomous_system1 or asys.id = l.id_autonomous_system2)' % request.matchdict["id_topology"]
        result_proxy = request.dbsession.bind.execute(query)
        links = list()
        for link in result_proxy:
            links.append({'id_autonomous_system1': link.id_autonomous_system1,
                          'id_autonomous_system2': link.id_autonomous_system2,
                          'id_link_agreement': link.id_link_agreement})
        dictionary['edges'] = links
        dictionary['full_stub'] = 'NON STUB TOPOLOGY'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
