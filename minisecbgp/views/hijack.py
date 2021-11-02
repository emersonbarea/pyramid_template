import ipaddress
import subprocess
import tarfile
import os.path
from datetime import datetime

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from pyramid.response import FileResponse
from wtforms import Form, SelectField, StringField, SubmitField, SelectMultipleField, widgets, IntegerField, \
    DateTimeField
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
    events_button = SubmitField('Events and Behavior')


class HijackEventsDateTimeDataForm(Form):
    start_datetime = DateTimeField('Start time: ',
                                   format='%Y-%m-%d %H:%M:%S',
                                   validators=[InputRequired()])
    end_datetime = DateTimeField('End time: ',
                                 format='%Y-%m-%d %H:%M:%S',
                                 validators=[InputRequired()])
    edit_button = SubmitField('Save')


class HijackEventsAnnouncementDataForm(Form):
    announcement_datetime = DateTimeField('Date and Time: ',
                                          format='%Y-%m-%d %H:%M:%S',
                                          validators=[InputRequired()])
    announced_prefix = StringField('Announced Prefix: ',
                                   validators=[InputRequired(),
                                               Length(min=9, max=18,
                                               message='Only valid prefix format. Ex.: 1.0.0.0/8 or 200.233.127.252/24.')])
    announcer = StringField('AS announcer: ',
                            validators=[InputRequired(),
                                        Length(min=1, max=18,
                                               message='Only a valid ASN in this topology.')])
    create_announcement_button = SubmitField('Save')
    announcement_id_event = IntegerField()
    delete_announcement_button = SubmitField('Del')


class HijackEventsWithdrawDataForm(Form):
    withdrawn_datetime = DateTimeField('Date and Time: ',
                                       format='%Y-%m-%d %H:%M:%S',
                                       validators=[InputRequired()])
    withdrawn_in_out = SelectField('In/Out:',
                                   validators=[InputRequired()],
                                   choices=[('out', 'Out'),
                                            ('in', 'In')])
    withdrawer = StringField('AS Withdrawer: ',
                             validators=[InputRequired(),
                                         Length(min=1, max=18,
                                                message='Only a valid ASN in this topology.')])
    withdrawn_peer = StringField('Peer AS: ',
                                 validators=[InputRequired(),
                                             Length(min=1, max=18,
                                                    message='Only a valid ASN in this topology.')])
    withdrawn_prefix_as_source = SelectField('Withdraw by prefix or AS source:',
                                             validators=[InputRequired()],
                                             choices=[('prefix', 'Prefix'),
                                                      ('as', 'AS source')])
    withdrawn_prefix = StringField('Withdrawn Prefix: ',
                                   validators=[Length(min=9, max=18,
                                                      message='Only valid prefix format. Ex.: 1.0.0.0/8 or 200.233.127.252/24.')])
    withdrawn = StringField('Withdrawn AS Source: ',
                            validators=[Length(min=1, max=18,
                                               message='Only a valid ASN in this topology.')])
    create_withdraw_button = SubmitField('Save')
    withdrawn_id_event = IntegerField()
    delete_withdrawn_button = SubmitField('Del')


class HijackEventsPrependDataForm(Form):
    prepend_datetime = DateTimeField('Date and Time: ',
                                     format='%Y-%m-%d %H:%M:%S',
                                     validators=[InputRequired()])
    prepend_in_out = SelectField('In/Out:',
                                 validators=[InputRequired()],
                                 choices=[('out', 'Out'),
                                          ('in', 'In')])
    prepend_prefix = StringField('Prefix: ',
                                 validators=[Length(min=9, max=18,
                                                    message='Only valid prefix format. Ex.: 1.0.0.0/8 or 200.233.127.252/24.')])
    prepended = StringField('Prepended AS: ',
                            validators=[InputRequired(),
                                        Length(min=1, max=18,
                                               message='Only a valid ASN in this topology.')])
    prepender = StringField('AS Prepender: ',
                            validators=[InputRequired(),
                                        Length(min=1, max=18,
                                               message='Only a valid ASN in this topology.')])
    prepend_peer = StringField('Peer AS: ',
                               validators=[InputRequired(),
                                           Length(min=1, max=18,
                                                  message='Only a valid ASN in this topology.')])
    times_prepended = IntegerField('How many times will be prepended:',
                                   validators=[InputRequired(),
                                               Length(min=1, max=10,
                                                      message='How many times the AS will be prepended.')])
    create_prepend_button = SubmitField('Save')
    prepend_id_event = IntegerField()
    delete_prepend_button = SubmitField('Del')


class HijackEventsMonitoringDataForm(Form):
    monitoring_datetime = DateTimeField('Monitor event date and time: ',
                                        format='%Y-%m-%d %H:%M:%S',
                                        validators=[InputRequired()])
    monitor_by = SelectField('Monitoring frequency:',
                             validators=[InputRequired()],
                             choices=[('automatic_time_slot', 'Automatic Time Slot'),
                                      ('specific_time_slot', 'Specific Time Slot')])
    amount_of_time_slot = IntegerField('Amount of time slots:',
                                       validators=[InputRequired(),
                                                   Length(min=1, max=10,
                                                          message='How many times slots the scenario will be monitored.')])
    which_as_will_be_monitored = SelectField('Which AS will be monitored?:',
                                             validators=[InputRequired()],
                                             choices=[('all', 'All'),
                                                      ('only_one_as', 'Only one AS')])
    monitor = StringField('AS that will be monitored: ',
                          validators=[InputRequired(),
                                      Length(min=1, max=18,
                                             message='Only a valid ASN in this topology.')])
    sleep_time = IntegerField('Sleep time between last BGP event and monitor task (sec.):',
                              validators=[InputRequired(),
                                          Length(min=1, max=10,
                                                 message='How long will the system wait between the last BGP event '
                                                         'runs and the monitoring task.')])
    create_monitoring_button = SubmitField('Save')
    monitoring_id_event = IntegerField()
    delete_monitoring_button = SubmitField('Del')


class HijackEventsRestrictMode(Form):
    restrict_mode = SelectField('Restrict mode:',
                                validators=[InputRequired()],
                                choices=[('permissive', 'Permissive'),
                                         ('restrictive', 'Restrictive')])
    edit_restrict_mode_button = SubmitField('Save')


class HijackEventsButtonDataForm(Form):
    generate_files_button = SubmitField('Submit')
    download_button = SubmitField('Download')
    emulate_button = SubmitField('Confirm')


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

                # delete previous realistic analysis if exist
                request.dbsession.query(models.RealisticAnalysis).filter_by(id_topology=topology.id).delete()

                # create new realistic analysis database entry
                realistic_analysis = models.RealisticAnalysis(
                    id_topology_distribution_method=topology_distribution_method.id,
                    id_emulation_platform=emulation_platform.id,
                    id_router_platform=router_platform.id,
                    id_topology=topology.id,
                    include_stub=include_stub)
                request.dbsession.add(realistic_analysis)
                request.dbsession.flush()

                id_realistic_analysis = realistic_analysis.id

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

            return HTTPFound(location=request.route_path('hijackRealisticAnalysisDetail', id_realistic_analysis=id_realistic_analysis))

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
    form_button = HijackEventsButtonDataForm(request.POST)

    id_realistic_analysis = request.matchdict['id_realistic_analysis']

    try:
        query = 'select (select t.topology from topology t where t.id = ra.id_topology) as topology, ' \
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
                'ra.time_write_files as time_write_files, ' \
                'ra.time_copy_files as time_copy_files ' \
                'from realistic_analysis ra ' \
                'where ra.id = %s;' % id_realistic_analysis
        result_proxy = request.dbsession.bind.execute(query)

        realistic_analysis = list()
        for realistic_analyze in result_proxy:
            realistic_analysis.append({'id_realistic_analysis': id_realistic_analysis,
                                       'topology': realistic_analyze.topology,
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
                                       'time_copy_files': realistic_analyze.time_copy_files,
                                       'total_time': (float(realistic_analyze.time_get_data) if realistic_analyze.time_get_data else 0) +
                                                     (float(realistic_analyze.time_autonomous_system_per_server) if realistic_analyze.time_autonomous_system_per_server else 0) +
                                                     (float(realistic_analyze.time_emulate_platform_commands) if realistic_analyze.time_emulate_platform_commands else 0) +
                                                     (float(realistic_analyze.time_router_platform_commands) if realistic_analyze.time_router_platform_commands else 0) +
                                                     (float(realistic_analyze.time_write_files) if realistic_analyze.time_write_files else 0) +
                                                     (float(realistic_analyze.time_copy_files) if realistic_analyze.time_copy_files else 0)})

        dictionary['realistic_analysis'] = realistic_analysis
        dictionary['form'] = form
        dictionary['form_button'] = form_button
        dictionary['hijackRealisticAnalysisDetail_url'] = request.route_url('hijackRealisticAnalysisDetail', id_realistic_analysis=id_realistic_analysis)

        if request.method == 'POST':
            if form.events_button.data:
                return HTTPFound(location=request.route_path('hijackEvents', id_realistic_analysis=id_realistic_analysis,restrict_mode='permissive'))

            if form_button.emulate_button.data:
                os.system('gnome-terminal -- /bin/bash -c "cd %s; ./topology.py; exec bash"' %
                          str(realistic_analysis[0]['output_path']).replace(' ', '\ '))

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


@view_config(route_name='hijackEvents', renderer='minisecbgp:templates/hijack/hijackEvents.jinja2')
def hijack_events(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    form_datetime = HijackEventsDateTimeDataForm(request.POST)
    form_announcement = HijackEventsAnnouncementDataForm(request.POST)
    form_withdrawn = HijackEventsWithdrawDataForm(request.POST)
    form_prepend = HijackEventsPrependDataForm(request.POST)
    form_monitoring = HijackEventsMonitoringDataForm(request.POST)
    form_restrict_mode = HijackEventsRestrictMode(request.POST)
    form_button = HijackEventsButtonDataForm(request.POST)

    realistic_analysis = request.dbsession.query(models.RealisticAnalysis).\
        filter_by(id=request.matchdict['id_realistic_analysis']).first()

    topology = request.dbsession.query(models.Topology).\
        filter_by(id=realistic_analysis.id_topology).first()

    event_behaviour = request.dbsession.query(models.EventBehaviour).\
        filter_by(id_topology=topology.id).first()

    if request.method == 'GET' and event_behaviour:

        form_restrict_mode.restrict_mode.data = event_behaviour.restrict_mode

    if request.method == 'POST':

        if form_datetime.edit_button.data:
            try:
                start_datetime = datetime.strptime(str(form_datetime.start_datetime.data), '%Y-%m-%d %H:%M:%S')
                end_datetime = datetime.strptime(str(form_datetime.end_datetime.data), '%Y-%m-%d %H:%M:%S')

                if start_datetime > end_datetime:
                    raise ValueError('Start datetime must be less than end datetime.')

                if event_behaviour:
                    event_behaviour.start_datetime = start_datetime
                    event_behaviour.end_datetime = end_datetime
                else:
                    event_behaviour = (models.EventBehaviour(id_topology=realistic_analysis.id_topology,
                                                             start_datetime=start_datetime,
                                                             end_datetime=end_datetime,
                                                             restrict_mode='permissive'))
                    request.dbsession.add(event_behaviour)
                request.dbsession.flush()

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_restrict_mode.edit_restrict_mode_button.data:
            try:
                event_behaviour.restrict_mode = form_restrict_mode.restrict_mode.data
                request.dbsession.flush()
            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_announcement.create_announcement_button.data:
            try:
                if not datetime.strptime(str(form_announcement.announcement_datetime.data), '%Y-%m-%d %H:%M:%S'):
                    raise ValueError('Event datetime must be in "%Y-%m-%d %H:%M:%S" format.')

                if datetime.strptime(str(form_announcement.announcement_datetime.data), '%Y-%m-%d %H:%M:%S') < \
                        datetime.strptime(str(event_behaviour.start_datetime), '%Y-%m-%d %H:%M:%S') or \
                        datetime.strptime(str(form_announcement.announcement_datetime.data), '%Y-%m-%d %H:%M:%S') > \
                        datetime.strptime(str(event_behaviour.end_datetime), '%Y-%m-%d %H:%M:%S'):
                    raise ValueError('Event datetime must be between Start time and End time (Events and Behaviour)')

                if not type(ipaddress.ip_network(form_announcement.announced_prefix.data)) is ipaddress.IPv4Network:
                    raise ValueError('Announced prefix must be a valid IPv4 network.')

                announcer = request.dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=topology.id).\
                    filter_by(autonomous_system=form_announcement.announcer.data).first()
                if not announcer:
                    raise ValueError('The AS announcer must be a valid ASN in topology.')

                event_announcement = models.EventAnnouncement(
                    id_event_behaviour=event_behaviour.id,
                    event_datetime=datetime.strptime(str(form_announcement.announcement_datetime.data), '%Y-%m-%d %H:%M:%S'),
                    prefix=form_announcement.announced_prefix.data,
                    announcer=form_announcement.announcer.data)
                request.dbsession.add(event_announcement)

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_withdrawn.create_withdraw_button.data:
            try:
                if not datetime.strptime(str(form_withdrawn.withdrawn_datetime.data), '%Y-%m-%d %H:%M:%S'):
                    raise ValueError('Event datetime must be in "%Y-%m-%d %H:%M:%S" format.')

                if datetime.strptime(str(form_withdrawn.withdrawn_datetime.data), '%Y-%m-%d %H:%M:%S') < \
                        datetime.strptime(str(event_behaviour.start_datetime), '%Y-%m-%d %H:%M:%S') or \
                        datetime.strptime(str(form_withdrawn.withdrawn_datetime.data), '%Y-%m-%d %H:%M:%S') > \
                        datetime.strptime(str(event_behaviour.end_datetime), '%Y-%m-%d %H:%M:%S'):
                    raise ValueError('Event datetime must be between Start time and End time (Events and Behaviour)')

                if form_withdrawn.withdrawn_prefix.data and \
                        not type(ipaddress.ip_network(form_withdrawn.withdrawn_prefix.data)) is ipaddress.IPv4Network:
                    raise ValueError('Withdrawn prefix must be a valid IPv4 network.')

                withdrawer = request.dbsession.query(models.AutonomousSystem).\
                    filter_by(id_topology=topology.id).\
                    filter_by(autonomous_system=form_withdrawn.withdrawer.data).first()
                if not withdrawer:
                    raise ValueError('The AS withdrawer must be a valid ASN in topology.')

                withdrawn_peer = request.dbsession.query(models.AutonomousSystem). \
                    filter_by(id_topology=topology.id). \
                    filter_by(autonomous_system=form_withdrawn.withdrawn_peer.data).first()
                if not withdrawn_peer:
                    raise ValueError('The peer must be a valid ASN in topology.')

                if form_withdrawn.withdrawn_prefix_as_source.data == 'prefix':
                    form_withdrawn.withdrawn.data = None
                elif form_withdrawn.withdrawn_prefix_as_source.data == 'as':
                    form_withdrawn.withdrawn_prefix.data = None

                event_withdrawn = models.EventWithdrawn(
                    id_event_behaviour=event_behaviour.id,
                    event_datetime=datetime.strptime(str(form_withdrawn.withdrawn_datetime.data), '%Y-%m-%d %H:%M:%S'),
                    in_out=form_withdrawn.withdrawn_in_out.data,
                    prefix=form_withdrawn.withdrawn_prefix.data,
                    withdrawer=form_withdrawn.withdrawer.data,
                    peer=form_withdrawn.withdrawn_peer.data,
                    withdrawn=form_withdrawn.withdrawn.data
                )
                request.dbsession.add(event_withdrawn)

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_prepend.create_prepend_button.data:
            try:
                if not datetime.strptime(str(form_prepend.prepend_datetime.data), '%Y-%m-%d %H:%M:%S'):
                    raise ValueError('Event datetime must be in "%Y-%m-%d %H:%M:%S" format.')

                if datetime.strptime(str(form_prepend.prepend_datetime.data), '%Y-%m-%d %H:%M:%S') < \
                        datetime.strptime(str(event_behaviour.start_datetime), '%Y-%m-%d %H:%M:%S') or \
                        datetime.strptime(str(form_prepend.prepend_datetime.data), '%Y-%m-%d %H:%M:%S') > \
                        datetime.strptime(str(event_behaviour.end_datetime), '%Y-%m-%d %H:%M:%S'):
                    raise ValueError('Event datetime must be between Start time and End time (Events and Behaviour)')

                # must be (in/out)
                # Prepender must be a valid ASN
                prepender = request.dbsession.query(models.AutonomousSystem). \
                    filter_by(id_topology=topology.id). \
                    filter_by(autonomous_system=form_prepend.prepender.data).first()
                if not prepender:
                    raise ValueError('The AS prepender must be a valid ASN in topology.')

                # must be (in)
                if form_prepend.prepend_in_out.data == 'in':

                    form_prepend.prepend_peer.data = None

                    # Prepended must be a valid ASN
                    prepended = request.dbsession.query(models.AutonomousSystem). \
                        filter_by(id_topology=topology.id). \
                        filter_by(autonomous_system=form_prepend.prepended.data).first()
                    if not prepended:
                        raise ValueError('The prepended AS must be a valid ASN in an Inbound AS-Path Prepending.')

                    # Prepender and Prepended must be peer
                    query = 'select count(l.id) from link l where ' \
                            '(l.id_autonomous_system1 = %s and l.id_autonomous_system2 = %s) ' \
                            'or ' \
                            '(l.id_autonomous_system1 = %s and l.id_autonomous_system2 = %s)' % \
                            (prepender.id, prepended.id, prepended.id, prepender.id)
                    result_proxy = request.dbsession.bind.execute(query)
                    if int(list(result_proxy)[0][0]) == 0:
                        raise ValueError('AS Prepender and Prepended AS must be peer in an Inbound AS-Path Prepending.')

                    form_prepend.prepend_peer.data = form_prepend.prepended.data

                # must be (out)
                if form_prepend.prepend_in_out.data == 'out':

                    # Peer must be a valid ASN
                    peer = request.dbsession.query(models.AutonomousSystem). \
                        filter_by(id_topology=topology.id). \
                        filter_by(autonomous_system=form_prepend.prepend_peer.data).first()
                    if not peer:
                        raise ValueError('The peer AS must be a valid ASN in an Outbound AS-Path Prepending.')

                    # Prepender and Peer must be peer
                    query = 'select count(l.id) from link l where ' \
                            '(l.id_autonomous_system1 = %s and l.id_autonomous_system2 = %s) ' \
                            'or ' \
                            '(l.id_autonomous_system1 = %s and l.id_autonomous_system2 = %s)' % \
                            (prepender.id, peer.id, peer.id, prepender.id)
                    result_proxy = request.dbsession.bind.execute(query)
                    if int(list(result_proxy)[0][0]) == 0:
                        raise ValueError('AS prepender and AS peer must be BGP peer in an Outbound AS-Path Prepending.')

                if form_prepend.prepend_prefix.data and \
                        not type(ipaddress.ip_network(form_prepend.prepend_prefix.data)) is ipaddress.IPv4Network:
                    raise ValueError('Prepended prefix must be a valid IPv4 network.')

                event = models.EventPrepend(
                    id_event_behaviour=event_behaviour.id,
                    event_datetime=datetime.strptime(str(form_prepend.prepend_datetime.data), '%Y-%m-%d %H:%M:%S'),
                    in_out=form_prepend.prepend_in_out.data,
                    prefix=form_prepend.prepend_prefix.data,
                    prepender=form_prepend.prepender.data,
                    prepended=form_prepend.prepended.data,
                    peer=form_prepend.prepend_peer.data,
                    hmt=form_prepend.times_prepended.data)
                request.dbsession.add(event)

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_monitoring.create_monitoring_button.data:
            try:

                time_slots = list()
                if form_monitoring.monitor_by.data == 'automatic_time_slot':
                    start_datetime = int(datetime.strptime(str(event_behaviour.start_datetime),
                                                           '%Y-%m-%d %H:%M:%S').strftime('%s'))
                    end_datetime = int(datetime.strptime(str(event_behaviour.end_datetime),
                                                         '%Y-%m-%d %H:%M:%S').strftime('%s'))
                    amount_of_time_slot = form_monitoring.amount_of_time_slot.data + 2
                    # time slots definition
                    if amount_of_time_slot > 0:
                        time_slot_interval = int((end_datetime - start_datetime) / (amount_of_time_slot - 1))
                        reference_time = start_datetime
                        for time_event in range(amount_of_time_slot - 1):
                            time_slots.append(reference_time)
                            reference_time = reference_time + time_slot_interval
                        time_slots.append(end_datetime)
                    else:
                        time_slots.append(start_datetime)
                        time_slots.append(end_datetime)
                elif form_monitoring.monitor_by.data == 'specific_time_slot':
                    if not datetime.strptime(str(form_monitoring.monitoring_datetime.data), '%Y-%m-%d %H:%M:%S'):
                        raise ValueError('Event datetime must be in "%Y-%m-%d %H:%M:%S" format.')
                    if datetime.strptime(str(form_monitoring.monitoring_datetime.data), '%Y-%m-%d %H:%M:%S') < \
                            datetime.strptime(str(event_behaviour.start_datetime), '%Y-%m-%d %H:%M:%S') or \
                            datetime.strptime(str(form_monitoring.monitoring_datetime.data), '%Y-%m-%d %H:%M:%S') > \
                            datetime.strptime(str(event_behaviour.end_datetime), '%Y-%m-%d %H:%M:%S'):
                        raise ValueError(
                            'Event datetime must be between Start time and End time (Events and Behaviour)')
                    time_slots.append(int(datetime.strptime(str(form_monitoring.monitoring_datetime.data),
                                                            '%Y-%m-%d %H:%M:%S').strftime('%s')))

                autonomous_systems = list()
                if form_monitoring.which_as_will_be_monitored.data == 'all':
                    for time_slot in time_slots:
                        event_monitoring = models.EventMonitoring(
                            id_event_behaviour=event_behaviour.id,
                            event_datetime=datetime.fromtimestamp(time_slot),
                            monitor=None,
                            all=True,
                            sleep_time=form_monitoring.sleep_time.data)
                        request.dbsession.add(event_monitoring)
                elif form_monitoring.which_as_will_be_monitored.data == 'only_one_as':
                    query = 'select asys.autonomous_system as autonomous_system ' \
                            'from event_behaviour as eb, ' \
                            'autonomous_system as asys ' \
                            'where eb.id_topology = asys.id_topology ' \
                            'and eb.id = %s ' \
                            'and asys.autonomous_system = %s;' % \
                            (event_behaviour.id, form_monitoring.monitor.data)
                    result_proxy = request.dbsession.bind.execute(query)
                    for autonomous_system in result_proxy:
                        autonomous_systems.append(autonomous_system.autonomous_system)
                    if not autonomous_systems:
                        raise ValueError('Autonomous System does not exist in the topology')
                    for time_slot in time_slots:
                        for autonomous_system in autonomous_systems:
                            event_monitoring = models.EventMonitoring(
                                id_event_behaviour=event_behaviour.id,
                                event_datetime=datetime.fromtimestamp(time_slot),
                                monitor=autonomous_system,
                                sleep_time=form_monitoring.sleep_time.data)
                            request.dbsession.add(event_monitoring)

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_announcement.delete_announcement_button.data:
            try:
                request.dbsession.query(models.EventAnnouncement).\
                    filter_by(id=form_announcement.announcement_id_event.data).delete()
            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_withdrawn.delete_withdrawn_button.data:
            try:
                request.dbsession.query(models.EventWithdrawn).\
                    filter_by(id=form_withdrawn.withdrawn_id_event.data).delete()

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_prepend.delete_prepend_button.data:
            try:
                request.dbsession.query(models.EventPrepend).\
                    filter_by(id=form_prepend.prepend_id_event.data).delete()

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_monitoring.delete_monitoring_button.data:
            try:
                request.dbsession.query(models.EventMonitoring).\
                    filter_by(id=form_monitoring.monitoring_id_event.data).delete()
            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

        if form_button.generate_files_button.data:

            # delete previous event detail if exist
            request.dbsession.query(models.EventDetail).filter_by(id_event_behaviour=event_behaviour.id).delete()

            # create new event detail database entry
            event_detail = models.EventDetail(id_event_behaviour=event_behaviour.id)
            request.dbsession.add(event_detail)
            request.dbsession.flush()

            arguments = ['--config-file=minisecbgp.ini',
                         '--id-event-behaviour=%s' % event_behaviour.id]

            if event_behaviour.restrict_mode == 'permissive':
                subprocess.Popen(['./venv/bin/MiniSecBGP_hijack_events_permissive_mode'] + arguments)
            elif event_behaviour.restrict_mode == 'restrictive':
                subprocess.Popen(['./venv/bin/MiniSecBGP_hijack_events_restrictive_mode'] + arguments)

            #subprocess.Popen(['./venv/bin/MiniSecBGP_hijack_events'] + arguments)

            return HTTPFound(location=request.route_path('hijackEventsDetail', id_event_behaviour=event_behaviour.id))

    if event_behaviour:

        form_datetime.start_datetime.data = datetime.strptime(
            str(event_behaviour.start_datetime), '%Y-%m-%d %H:%M:%S')
        form_datetime.end_datetime.data = datetime.strptime(
            str(event_behaviour.end_datetime), '%Y-%m-%d %H:%M:%S')

        dictionary['events_announcement'] = request.dbsession.query(models.EventAnnouncement). \
            filter_by(id_event_behaviour=event_behaviour.id). \
            order_by(models.EventAnnouncement.event_datetime).all()

        dictionary['events_withdrawn'] = request.dbsession.query(models.EventWithdrawn). \
            filter_by(id_event_behaviour=event_behaviour.id). \
            order_by(models.EventWithdrawn.event_datetime).all()

        dictionary['events_prepend'] = request.dbsession.query(models.EventPrepend). \
            filter_by(id_event_behaviour=event_behaviour.id). \
            order_by(models.EventPrepend.event_datetime).all()

        dictionary['events_monitoring'] = request.dbsession.query(models.EventMonitoring). \
            filter_by(id_event_behaviour=event_behaviour.id). \
            order_by(models.EventMonitoring.event_datetime).all()

        dictionary['event_behaviour'] = True

    dictionary['realistic_analysis'] = realistic_analysis
    dictionary['topology'] = topology
    dictionary['form_datetime'] = form_datetime
    dictionary['form_announcement'] = form_announcement
    dictionary['form_withdrawn'] = form_withdrawn
    dictionary['form_prepend'] = form_prepend
    dictionary['form_monitoring'] = form_monitoring
    dictionary['form_restrict_mode'] = form_restrict_mode
    dictionary['form_button'] = form_button

    return dictionary


@view_config(route_name='hijackEventsDetail', renderer='minisecbgp:templates/hijack/hijackEventsDetail.jinja2')
def hijack_events_detail(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    id_event_behaviour = request.matchdict['id_event_behaviour']
    dictionary = dict()
    form_button = HijackEventsButtonDataForm(request.POST)

    try:
        query = 'select ed.id_event_behaviour as id_event_behaviour, ' \
                '(select t.topology ' \
                'from topology t, ' \
                'event_behaviour eb ' \
                'where t.id = eb.id_topology ' \
                'and eb.id = ed.id_event_behaviour) as topology, ' \
                'ed.time_get_data as time_get_data, ' \
                'ed.time_announcement_commands as time_announcement_commands, ' \
                'ed.time_withdrawn_commands as time_withdrawn_commands, ' \
                'ed.time_prepends_commands as time_prepends_commands, ' \
                'ed.time_write_config_files as time_write_config_files, ' \
                'ed.time_monitoring_commands as time_monitoring_commands, ' \
                'ed.time_write_monitoring_files as time_write_monitoring_files ' \
                'from event_detail ed ' \
                'where ed.id_event_behaviour = %s;' % id_event_behaviour
        result_proxy = request.dbsession.bind.execute(query)

        events = list()
        for event in result_proxy:
            events.append({'id_event_behaviour': event.id_event_behaviour,
                           'topology': event.topology,
                           'time_get_data': event.time_get_data,
                           'time_announcement_commands': event.time_announcement_commands,
                           'time_withdrawn_commands': event.time_withdrawn_commands,
                           'time_prepends_commands': event.time_prepends_commands,
                           'time_write_config_files': event.time_write_config_files,
                           'time_monitoring_commands': event.time_monitoring_commands,
                           'time_write_monitoring_files': event.time_write_monitoring_files,
                           'total_time': (float(event.time_get_data) if event.time_get_data else 0) +
                                         (float(event.time_announcement_commands) if event.time_announcement_commands else 0) +
                                         (float(event.time_withdrawn_commands) if event.time_withdrawn_commands else 0) +
                                         (float(event.time_prepends_commands) if event.time_prepends_commands else 0) +
                                         (float(event.time_write_config_files) if event.time_write_config_files else 0) +
                                         (float(event.time_monitoring_commands) if event.time_monitoring_commands else 0) +
                                         (float(event.time_write_monitoring_files) if event.time_write_monitoring_files else 0)})

        dictionary['events'] = events

        dictionary['form_button'] = form_button
        dictionary['hijackEventsDetail_url'] = request.route_url('hijackEventsDetail', id_event_behaviour=id_event_behaviour)

        if request.method == 'POST':
            realistic_analysis = request.dbsession.query(models.EventBehaviour, models.RealisticAnalysis). \
                filter(models.EventBehaviour.id == id_event_behaviour). \
                filter(models.EventBehaviour.id_topology == models.RealisticAnalysis.id_topology).first()

            if form_button.download_button.data:
                source_dir = str(realistic_analysis.RealisticAnalysis.output_path[:-1])
                output_filename = dictionary['events'][0]['topology'] + '.tar.gz'
                with tarfile.open(source_dir + '/' + output_filename, "w:gz") as tar:
                    tar.add(source_dir, arcname=os.path.basename(source_dir))

                response = FileResponse(source_dir + '/' + output_filename)
                response.headers['Content-Disposition'] = "attachment; filename=%s" % output_filename
                return response

            if form_button.emulate_button.data:
                os.system('gnome-terminal -- /bin/bash -c "cd %s; ./topology.py; exec bash"' %
                          str(realistic_analysis.RealisticAnalysis.output_path).replace(' ', '\ '))

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
