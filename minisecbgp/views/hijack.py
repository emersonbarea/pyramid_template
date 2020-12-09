import ipaddress
import subprocess
import tarfile
import os.path

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from pyramid.response import FileResponse
from wtforms import Form, SelectField, StringField, SubmitField, SelectMultipleField, widgets, IntegerField
from wtforms.validators import InputRequired, Length
from wtforms.widgets.html5 import NumberInput

from minisecbgp import models


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class AttackScenarioDataForm(Form):
    scenario_name = StringField(validators=[InputRequired(),
                                            Length(min=1, max=50,
                                                   message='Scenario name string must be between 1 and 50 characters long.')])
    scenario_description = StringField(validators=[InputRequired(),
                                                   Length(min=1, max=50,
                                                          message='Scenario description string must be between 1 and 50 characters long.')])
    topology = SelectField(coerce=int,
                           validators=[InputRequired()])

    attack_type = SelectField(coerce=int,
                              validators=[InputRequired()])

    attacker = SelectField(choices=[('', '--'),
                                    ('all', 'All ASs'),
                                    ('region', 'All ASs from specific region(s)'),
                                    ('AS', 'Specific AS(s)')])
    attacker_region = StringField(validators=[InputRequired(),
                                              Length(min=1, max=100,
                                                     message='Region name string must be between 1 and 100 characters long.')])
    attacker_autonomous_system = StringField(validators=[InputRequired(),
                                                         Length(min=1, max=100,
                                                                message='ASN string must be between 1 and 100 characters long.')])

    affected_area = SelectField(choices=[('', '--'),
                                         ('all', 'All ASs'),
                                         ('region', 'All ASs from specific region(s)'),
                                         ('AS', 'Specific AS(s)')])
    affected_area_region = StringField(validators=[InputRequired(),
                                                   Length(min=1, max=100,
                                                          message='Region name string must be between 1 and 100 characters long.')])
    affected_area_autonomous_system = StringField(validators=[InputRequired(),
                                                              Length(min=1, max=100,
                                                                     message='ASN string must be between 1 and 100 characters long.')])

    target = SelectField(choices=[('', '--'),
                                  ('all', 'Use the prefix(es) of all ASs'),
                                  ('region', 'Use the prefix(es) of all ASs in the region(s)'),
                                  ('AS', 'Use the prefix(es) of specific AS(s)')])
    target_region = StringField(validators=[InputRequired(),
                                            Length(min=1, max=100,
                                                   message='Region name string must be between 1 and 100 characters long.')])
    target_autonomous_system = StringField(validators=[InputRequired(),
                                                       Length(min=1, max=100,
                                                              message='ASN string must be between 1 and 100 characters long.')])

    shortest_paths = SelectField(choices=[('', '--'),
                                          ('all', 'All Paths'),
                                          ('shortest', 'Choose the number of shortest paths')])
    number_of_shortest_paths = IntegerField(widget=NumberInput(min=1, max=10000, step=1),
                                            validators=[InputRequired()])

    continue_button = SubmitField('Continue')


class RealisticAnalysisDataForm(Form):
    topology_list = SelectField('Choose the topology: ', coerce=int,
                                validators=[InputRequired()])
    include_stub = MultiCheckboxField(choices=[(1, 'Include stub ASs')], coerce=int)
    cluster_list = MultiCheckboxField('Choose the servers on which to spawn the topology: ',
                                      coerce=int, validators=[InputRequired(message='Check at least one cluster node')])
    topology_distribution_method_list = SelectField('Choose how to spawn the topology on cluster nodes: ',
                                                    coerce=int, validators=[InputRequired()])
    router_platform_list = SelectField('Choose which BGP router to use: ',
                                       coerce=int, validators=[InputRequired()])
    emulation_platform_list = SelectField('Choose which emulation platform to use: ',
                                          coerce=int, validators=[InputRequired()])


class RealisticAnalysisDetailDataForm(Form):
    emulate_button = SubmitField('Submit')
    download_button = SubmitField('Download')


def node_status(dbsession, node):
    services = dbsession.query(models.Node, models.NodeService). \
        filter(models.Node.node == node). \
        filter(models.Node.id == models.NodeService.id_node).all()
    for service in services:
        if service.NodeService.status == 1:
            return False

    configurations = dbsession.query(models.Node, models.NodeConfiguration). \
        filter(models.Node.node == node). \
        filter(models.Node.id == models.NodeConfiguration.id_node).all()
    for configuration in configurations:
        if configuration.NodeConfiguration.status == 1:
            return False

    installs = dbsession.query(models.Node, models.NodeInstall). \
        filter(models.Node.node == node). \
        filter(models.Node.id == models.NodeInstall.id_node).all()
    for install in installs:
        if install.NodeInstall.status == 1:
            return False

    return True


@view_config(route_name='hijack', renderer='minisecbgp:templates/hijack/hijack.jinja2')
def hijack(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()

    return dictionary


@view_config(route_name='hijackAttackScenario',
             renderer='minisecbgp:templates/hijack/hijackAttackScenario.jinja2')
def hijack_attack_scenario(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()

    try:
        form = AttackScenarioDataForm(request.POST)
        form.topology.choices = [(row.id, row.topology) for row in
                                 request.dbsession.query(models.Topology).all()]
        form.attack_type.choices = [(row.id, row.scenario_attack_type) for row in
                                    request.dbsession.query(models.ScenarioAttackType).all()]

        availability = True
        downloading = request.dbsession.query(models.DownloadingTopology).first()
        if downloading.downloading == 1:
            availability = False

        if not availability:
            dictionary['message'] = 'Warning: there is an update process running in the background ' \
                                    '(cluster nodes or topology). Wait for it finish to access Realistic Analysis again.'
            dictionary['css_class'] = 'warningMessage'

        dictionary['form'] = form
        dictionary['availability'] = availability

        if request.method == 'POST' and form.validate():

            # attacker
            attacker_list = list()
            if form.attacker.data == 'all':
                attackers = request.dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=form.topology.data).all()
                if attackers:
                    for attacker in attackers:
                        attacker_list.append(attacker.autonomous_system)
                else:
                    dictionary['message'] = 'There is no Autonomous Systems in topology "%s" ' \
                                            'to be used as an attacker' % form.topology.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
            elif form.attacker.data == 'region':
                try:
                    region = request.dbsession.query(models.Region).\
                        filter_by(id_topology=form.topology.data).\
                        filter_by(region=form.attacker_region.data).first()
                except Exception as error:
                    dictionary['message'] = error
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                if region:
                    attackers = request.dbsession.query(models.AutonomousSystem).\
                        filter_by(id_topology=form.topology.data).\
                        filter_by(id_region=region.id).all()
                    if attackers:
                        for attacker in attackers:
                            attacker_list.append(attacker.autonomous_system)
                    else:
                        dictionary['message'] = 'There is no Autonomous Systems in region "%s" ' \
                                                'to be used as an attacker' % form.attacker_region.data
                        dictionary['css_class'] = 'errorMessage'
                        return dictionary
                else:
                    dictionary['message'] = 'The region "%s" does not exist in topology "%s" to be used as ' \
                                            'attacker' % (form.attacker_region.data, form.topology.data)
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
            elif form.attacker.data == 'AS':
                attackers = form.attacker_autonomous_system.data.strip('][').split(',')
                attackers = map(int, attackers)
                attacker_list = list(attackers)
                for attacker in attacker_list:
                    attacker_exist = request.dbsession.query(models.AutonomousSystem).\
                        filter_by(id_topology=form.topology.data).\
                        filter_by(autonomous_system=attacker).first()
                    if not attacker_exist:
                        dictionary['message'] = 'Autonomous System "%s" does not exist to be ' \
                                                'used as an attacker' % attacker
                        dictionary['css_class'] = 'errorMessage'
                        return dictionary

            # affected area
            affected_area_list = list()
            if form.affected_area.data == 'all':
                affected_areas = request.dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=form.topology.data).all()
                if affected_areas:
                    for affected_area in affected_areas:
                        affected_area_list.append(affected_area.autonomous_system)
                else:
                    dictionary['message'] = 'There is no Autonomous Systems in topology "%s" ' \
                                            'to be used in affected area' % form.topology.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
            elif form.affected_area.data == 'region':
                try:
                    region = request.dbsession.query(models.Region).\
                        filter_by(id_topology=form.topology.data).\
                        filter_by(region=form.affected_area_region.data).first()
                except Exception as error:
                    dictionary['message'] = error
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                if region:
                    affected_areas = request.dbsession.query(models.AutonomousSystem).\
                        filter_by(id_topology=form.topology.data).\
                        filter_by(id_region=region.id).all()
                    if affected_areas:
                        for affected_area in affected_areas:
                            affected_area_list.append(affected_area.autonomous_system)
                    else:
                        dictionary['message'] = 'There is no Autonomous Systems in region "%s" ' \
                                                'to be used in affected area' % form.affected_area_region.data
                        dictionary['css_class'] = 'errorMessage'
                        return dictionary
                else:
                    dictionary['message'] = 'The region "%s" does not exist in topology "%s" to be used in ' \
                                            'affected area' % (form.affected_area_region.data, form.topology.data)
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
            elif form.affected_area.data == 'AS':
                affected_areas = form.affected_area_autonomous_system.data.strip('][').split(',')
                affected_areas = map(int, affected_areas)
                affected_area_list = list(affected_areas)
                for affected_area in affected_area_list:
                    affected_area_exist = request.dbsession.query(models.AutonomousSystem). \
                        filter_by(id_topology=form.topology.data). \
                        filter_by(autonomous_system=affected_area).first()
                    if not affected_area_exist:
                        dictionary['message'] = 'Autonomous System "%s" does not exist to be ' \
                                                'used in affected area' % affected_area
                        dictionary['css_class'] = 'errorMessage'
                        return dictionary

            # target
            target_list = list()
            if form.target.data == 'all':
                targets = request.dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=form.topology.data).all()
                if targets:
                    for target in targets:
                        target_list.append(target.autonomous_system)
                else:
                    dictionary['message'] = 'There is no Autonomous Systems in topology "%s" ' \
                                            'to be used as target' % form.topology.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
            elif form.target.data == 'region':
                try:
                    region = request.dbsession.query(models.Region).\
                        filter_by(id_topology=form.topology.data).\
                        filter_by(region=form.target_region.data).first()
                except Exception as error:
                    dictionary['message'] = error
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
                if region:
                    targets = request.dbsession.query(models.AutonomousSystem).\
                        filter_by(id_topology=form.topology.data).\
                        filter_by(id_region=region.id).all()
                    if targets:
                        for target in targets:
                            target_list.append(target.autonomous_system)
                    else:
                        dictionary['message'] = 'There is no Autonomous Systems in region ' \
                                                '"%s" to be used as target' % form.target_region.data
                        dictionary['css_class'] = 'errorMessage'
                        return dictionary
                else:
                    dictionary['message'] = 'The region "%s" does not exist in topology "%s" to be used as ' \
                                            'target' % (form.target_region.data, form.topology.data)
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary
            elif form.target.data == 'AS':
                targets = form.target_autonomous_system.data.strip('][').split(',')
                targets = map(int, targets)
                target_list = list(targets)
                for target in target_list:
                    target_exist = request.dbsession.query(models.AutonomousSystem). \
                        filter_by(id_topology=form.topology.data). \
                        filter_by(autonomous_system=target).first()
                    if not target_exist:
                        dictionary['message'] = 'Autonomous System "%s" does not exist to be ' \
                                                'used as target' % target
                        dictionary['css_class'] = 'errorMessage'
                        return dictionary

            # number of shortest paths
            if form.shortest_paths.data == 'all':
                number_of_shortest_paths = 0
            elif form.shortest_paths.data == 'shortest':
                number_of_shortest_paths = form.number_of_shortest_paths.data

            try:
                scenario_stuff = request.dbsession.query(models.ScenarioStuff).\
                    filter_by(scenario_name=form.scenario_name.data).first()
                if scenario_stuff:
                    dictionary['message'] = 'There is already a scenario with this name: "%s".\n' \
                                            'Try again with another scenario identification.' % \
                                            form.scenario_name.data
                    dictionary['css_class'] = 'errorMessage'
                    return dictionary

                request.dbsession.add(models.ScenarioStuff(
                    scenario_name=form.scenario_name.data,
                    scenario_description=form.scenario_description.data,
                    id_topology=form.topology.data,
                    attacker_list=str(attacker_list),
                    affected_area_list=str(affected_area_list),
                    target_list=str(target_list),
                    attack_type=form.attack_type.data,
                    number_of_shortest_paths=number_of_shortest_paths))
                request.dbsession.flush()
            except Exception as error:
                request.dbsession.rollback()
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'
                return dictionary

            scenario_stuff = request.dbsession.query(models.ScenarioStuff). \
                filter_by(scenario_name=form.scenario_name.data).first()

            arguments = ['--config-file=minisecbgp.ini',
                         '--scenario-id=%s' % scenario_stuff.id]

            subprocess.Popen(['./venv/bin/MiniSecBGP_hijack_attack_scenario'] + arguments)
            return HTTPFound(location=request.route_path('hijackAttackScenarioDetail'))

        dictionary['form'] = form
    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='hijackAttackScenarioDetail',
             renderer='minisecbgp:templates/hijack/hijackAttackScenarioDetail.jinja2')
def hijack_attack_scenario_detail(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()

    return dictionary


@view_config(route_name='hijackRealisticAnalysis',
             renderer='minisecbgp:templates/hijack/hijackRealisticAnalysis.jinja2')
def hijack_realistic_analysis(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        form = RealisticAnalysisDataForm(request.POST)

        # Topology
        form.topology_list.choices = [(row.id, row.topology) for row in
                                      request.dbsession.query(models.Topology).order_by(models.Topology.topology)]

        # Cluster nodes
        query = 'select n.id, ' \
                'n.node ' \
                'from node n, ' \
                'node_service ns, ' \
                'node_configuration nc, ' \
                'node_install ni ' \
                'where n.id = ns.id_node ' \
                'and n.id = nc.id_node ' \
                'and n.id = ni.id_node ' \
                'and ns.id_node not in(select ns.id_node from node_service ns where ns.status in (1,2) group by ns.id_node) ' \
                'and nc.id_node not in(select nc.id_node from node_configuration nc where nc.status in (1,2) group by nc.id_node) ' \
                'and ni.id_node not in(select ni.id_node from node_install ni where ni.status in (1,2) group by ni.id_node) ' \
                'group by n.id, n.node'
        result_proxy = request.dbsession.bind.execute(query)
        form.cluster_list.choices = [(row.id, ipaddress.ip_address(row.node)) for row in result_proxy]

        # Topology distribution method on cluster (Customer Cone, Round Robin)
        form.topology_distribution_method_list.choices = [(row.id, row.topology_distribution_method) for row in
                                                          request.dbsession.query(models.TopologyDistributionMethod)]

        # Emulation platform (Mininet, Docker)
        form.emulation_platform_list.choices = [(row.id, row.emulation_platform) for row in
                                                request.dbsession.query(models.EmulationPlatform)]

        # Router platform (Quagga, Bird)
        form.router_platform_list.choices = [(row.id, row.router_platform) for row in
                                             request.dbsession.query(models.RouterPlatform)]

        availability = True
        downloading = request.dbsession.query(models.DownloadingTopology).first()
        if downloading.downloading == 1:
            availability = False

        if not availability:
            dictionary[
                'message'] = 'Warning: there is an update process running in the background (cluster nodes or topology). ' \
                             'Wait for it finish to access Realistic Analysis again.'
            dictionary['css_class'] = 'warningMessage'

        dictionary['form'] = form
        dictionary['availability'] = availability

        if request.method == 'POST' and form.validate():
            if form.include_stub.data:
                include_stub = True
            else:
                include_stub = False

            try:
                request.dbsession.query(models.RealisticAnalysis).delete()
                topology = request.dbsession.query(models.Topology). \
                    filter_by(id=form.topology_list.data).first()
                cluster_list = list()
                query = request.dbsession.query(models.Node). \
                    filter(models.Node.id.in_(form.cluster_list.data))
                result_proxy = query.all()
                for cluster_node in result_proxy:
                    cluster_list.append(cluster_node.hostname)
                topology_distribution_method = request.dbsession.query(models.TopologyDistributionMethod). \
                    filter_by(id=form.topology_distribution_method_list.data).first()
                emulation_platform = request.dbsession.query(models.EmulationPlatform). \
                    filter_by(id=form.emulation_platform_list.data).first()
                router_platform = request.dbsession.query(models.RouterPlatform). \
                    filter_by(id=form.router_platform_list.data).first()
                request.dbsession.add(
                    models.RealisticAnalysis(id_topology_distribution_method=topology_distribution_method.id,
                                             id_emulation_platform=emulation_platform.id,
                                             id_router_platform=router_platform.id,
                                             topology=topology.topology,
                                             include_stub=include_stub))
                request.dbsession.flush()
            except Exception as error:
                request.dbsession.rollback()
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'
                return dictionary

            arguments = ['--config-file=minisecbgp.ini',
                         '--topology=%s' % form.topology_list.data,
                         '--include-stub=%s' % include_stub,
                         '--cluster-list=%s' % cluster_list,
                         '--topology-distribution-method=%s' % form.topology_distribution_method_list.data,
                         '--emulation-platform=%s' % form.emulation_platform_list.data,
                         '--router-platform=%s' % form.router_platform_list.data]
            subprocess.Popen(['./venv/bin/MiniSecBGP_hijack_realistic_analysis'] + arguments)

            return HTTPFound(location=request.route_path('hijackRealisticAnalysisDetail'))

    except Exception as error:
        request.dbsession.rollback()
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='hijackRealisticAnalysisDetail',
             renderer='minisecbgp:templates/hijack/hijackRealisticAnalysisDetail.jinja2')
def hijack_realistic_analysis_detail(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    form = RealisticAnalysisDetailDataForm(request.POST)
    try:
        query = 'select ra.id as id, ' \
                'ra.topology as topology, ' \
                '(select tdm.topology_distribution_method from topology_distribution_method tdm ' \
                'where tdm.id = ra.id_topology_distribution_method) as topology_distribution_method, ' \
                '(select ep.emulation_platform from emulation_platform ep ' \
                'where ep.id = ra.id_emulation_platform) as emulation_platform, ' \
                '(select rp.router_platform from router_platform rp ' \
                'where rp.id = ra.id_router_platform) as router_platform, ' \
                'ra.include_stub as include_stub, ' \
                'ra.output_path as output_path, ' \
                'ra.number_of_autonomous_systems as number_of_autonomous_systems, ' \
                'ra.time_get_data as time_get_data, ' \
                'ra.time_autonomous_system_per_server as time_autonomous_system_per_server, ' \
                'ra.time_emulate_platform_commands as time_emulate_platform_commands, ' \
                'ra.time_router_platform_commands as time_router_platform_commands, ' \
                'ra.time_write_files as time_write_files ' \
                'from realistic_analysis ra;'
        result_proxy = request.dbsession.bind.execute(query)
        realistic_analysis = list()
        for realistic_analyze in result_proxy:
            realistic_analysis.append({'topology': realistic_analyze.topology,
                                       'topology_distribution_method': realistic_analyze.topology_distribution_method,
                                       'emulation_platform': realistic_analyze.emulation_platform,
                                       'router_platform': realistic_analyze.router_platform,
                                       'include_stub': realistic_analyze.include_stub,
                                       'output_path': realistic_analyze.output_path,
                                       'number_of_autonomous_systems': realistic_analyze.number_of_autonomous_systems,
                                       'time_get_data': realistic_analyze.time_get_data,
                                       'time_autonomous_system_per_server': realistic_analyze.time_autonomous_system_per_server,
                                       'time_emulate_platform_commands': realistic_analyze.time_emulate_platform_commands,
                                       'time_router_platform_commands': realistic_analyze.time_router_platform_commands,
                                       'time_write_files': realistic_analyze.time_write_files,
                                       'total_time': (float(realistic_analyze.time_get_data) if realistic_analyze.time_get_data else 0) +
                                                     (float(realistic_analyze.time_emulate_platform_commands) if realistic_analyze.time_emulate_platform_commands else 0) +
                                                     (float(realistic_analyze.time_router_platform_commands) if realistic_analyze.time_router_platform_commands else 0) +
                                                     (float(realistic_analyze.time_write_files) if realistic_analyze.time_write_files else 0)})
        dictionary['realistic_analysis'] = realistic_analysis
        dictionary['form'] = form
        dictionary['hijackRealisticAnalysisDetail_url'] = request.route_url('hijackRealisticAnalysisDetail')

        if request.method == 'POST' and form.validate():

            if form.download_button.data:
                realistic_analysis = request.dbsession.query(models.RealisticAnalysis).first()
                source_dir = str(realistic_analysis.output_path[:-1])
                output_filename = str(realistic_analysis.topology) + '.tar.gz'
                with tarfile.open(source_dir + '/' + output_filename, "w:gz") as tar:
                    tar.add(source_dir, arcname=os.path.basename(source_dir))

                response = FileResponse(source_dir + '/' + output_filename)
                response.headers['Content-Disposition'] = "attachment; filename=%s" % output_filename
                return response

            if form.emulate_button.data:
                os.system('gnome-terminal -- /bin/bash -c "cd %s; exec bash"' %
                          str(dictionary['realistic_analysis'][0]['output_path']).replace(' ', '\ '))

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='hijackAttackType', renderer='minisecbgp:templates/hijack/hijackAttackTypes.jinja2')
def hijack_attack_type(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    dictionary['attack_types'] = request.dbsession.query(models.ScenarioAttackType).all()

    return dictionary
