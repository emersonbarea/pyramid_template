import ipaddress
import os
import subprocess

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy.exc import IntegrityError
from wtforms import Form, SelectField, IntegerField, StringField, SubmitField, SelectMultipleField, widgets
from wtforms.validators import InputRequired, Length
from wtforms.widgets.html5 import NumberInput

import pandas as pd

from minisecbgp import models


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class AffectedAreaDataForm(Form):
    attacker = SelectField('Choose the <b><i>attacker</i></b> '
                           '(Which AS will announce the hijacked prefix): *',
                           choices=[('', '--'),
                                    ('all', 'All ASs'),
                                    ('region', 'All ASs from a region'),
                                    ('AS', 'Specify the ASN')])
    regionAttacker = StringField('Attacker\'s region name: *',
                                 validators=[InputRequired(),
                                             Length(min=1, max=100,
                                                    message='Region name string must be between 1 and 100 characters long.')])
    ASAttacker = StringField('Attacker\'s ASN: *',
                             validators=[InputRequired(),
                                         Length(min=1, max=100,
                                                message='ASN string must be between 1 and 100 characters long.')])

    target = SelectField('Choose the <b><i>affected area</i></b> '
                         '(Check if this AS receives and accepts the hijacked route): *',
                         choices=[('', '--'),
                                  ('all', 'All ASs'),
                                  ('region', 'All ASs from a region'),
                                  ('AS', 'Specify the ASN')])
    regionTarget = StringField('Target\'s region name: *',
                               validators=[InputRequired(),
                                           Length(min=1, max=100,
                                                  message='Region name string must be between 1 and 100 characters long.')])
    ASTarget = StringField('Target\'s ASN: *',
                           validators=[InputRequired(),
                                       Length(min=1, max=100,
                                              message='ASN string must be between 1 and 100 characters long.')])

    prefix = SelectField('Choose the <b><i>prefix target</i></b> '
                         '(Which prefix will be hijacked): *',
                         choices=[('', '--'),
                                  ('target', 'Use the target\'s prefix'),
                                  ('all', 'All AS\'s prefixes'),
                                  ('region', 'All AS\'s prefixes from a region'),
                                  ('AS', 'Use the prefix of a specific AS'),
                                  ('prefix', 'Enter the prefix')])
    regionPrefix = StringField('Name of the region where all AS\'s prefixes will be hijacked: *',
                               validators=[InputRequired(),
                                           Length(min=1, max=100,
                                                  message='Region name string must be between 1 and 100 characters long.')])
    ASPrefix = StringField('ASN from which its prefix will be hijacked: *',
                           validators=[InputRequired(),
                                       Length(min=1, max=100,
                                              message='ASN string must be between 1 and 100 characters long.')])
    prefixPrefix = StringField('Specific prefix that will be hijacked: *',
                               validators=[InputRequired(),
                                           Length(min=1, max=100,
                                                  message='Prefix string must be between 1 and 100 characters long.')])

    path = SelectField('Number of shortest <b><i>paths</i></b> '
                       '(How many shortest paths should be considered in the report): *',
                       choices=[('', '--'),
                                ('all', 'All Paths'),
                                ('shortest', 'Choose the number of shortest paths')])
    shortestPath = IntegerField('Number of shortest paths: *',
                                widget=NumberInput(min=0, max=10000, step=1),
                                validators=[InputRequired()])

    continue_button = SubmitField('Continue')


class RealisticAnalysisDataForm(Form):
    realistic_analysis = StringField('Realistic Analysis name/description: *',
                                     validators=[InputRequired(),
                                                 Length(min=1, max=50,
                                                        message='Realistic Analysis name/description string must be between '
                                                                '1 and 50 characters long.')])
    topology_list = SelectField('Choose the topology: ', coerce=int,
                                validators=[InputRequired()])
    stub = MultiCheckboxField(choices=[(1, 'Include stub ASs')], coerce=int)
    cluster_list = MultiCheckboxField('Choose the servers on which to spawn the topology: ',
                                      coerce=int, validators=[InputRequired(message='Check at least one cluster node')])
    topology_distribution_method_list = SelectField('Choose how to spawn the topology on cluster nodes: ',
                                                    coerce=int, validators=[InputRequired()])
    router_platform_list = SelectField('Choose which BGP router to use: ',
                                       coerce=int, validators=[InputRequired()])
    emulation_platform_list = SelectField('Choose which emulation platform to use: ',
                                          coerce=int, validators=[InputRequired()])


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


@view_config(route_name='hijack', renderer='minisecbgp:templates/hijack/hijackHistory.jinja2')
def hijack(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()

    return dictionary


@view_config(route_name='hijackAffectedArea', renderer='minisecbgp:templates/hijack/hijackAffectedArea.jinja2')
def hijackAffectedArea(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()

    try:
        form = AffectedAreaDataForm(request.POST)
        dictionary['form'] = form

        if request.method == 'POST' and form.validate():
            form = AffectedAreaDataForm()
            dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='hijackRealisticAnalysis',
             renderer='minisecbgp:templates/hijack/hijackRealisticAnalysis.jinja2')
def hijackRealisticAnalysis(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        form = RealisticAnalysisDataForm(request.POST)

        form.topology_list.choices = [(row.id, row.topology) for row in
                                      request.dbsession.query(models.Topology).order_by(models.Topology.topology)]

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

        form.topology_distribution_method_list.choices = [(row.id, row.topology_distribution_method) for row in
                                                          request.dbsession.query(models.TopologyDistributionMethod)]

        form.emulation_platform_list.choices = [(row.id, row.emulation_platform) for row in
                                                request.dbsession.query(models.EmulationPlatform)]

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
            try:
                realistic_analysis = request.dbsession.query(models.RealisticAnalysis).\
                    filter_by(realistic_analysis=form.realistic_analysis.data).first()
            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'
                return dictionary

            if realistic_analysis:
                dictionary['message'] = 'The Realistic Analysis name/description "%s" already exist. Choose another ' \
                                        'name/description.' % form.realistic_analysis.data
                dictionary['css_class'] = 'errorMessage'
                return dictionary

            if form.stub.data:
                topology_length = 'FULL'
            else:
                topology_length = 'STUB'

            topology_distribution_method = (dict(form.topology_distribution_method_list.choices).get(form.topology_distribution_method_list.data)).upper()
            emulation_platform = (dict(form.emulation_platform_list.choices).get(form.emulation_platform_list.data)).upper()
            router_platform = (dict(form.router_platform_list.choices).get(form.router_platform_list.data)).upper()

            arguments = ['--config-file=minisecbgp.ini',
                         '--realistic-analysis-name=%s' % form.realistic_analysis.data,
                         '--topology=%s' % form.topology_list.data,
                         '--topology-length=%s' % topology_length,
                         '--topology-distribution-method=%s' % topology_distribution_method,
                         '--emulation-platform=%s' % emulation_platform,
                         '--router-platform=%s' % router_platform]
            subprocess.Popen(['./venv/bin/MiniSecBGP_realistic_analysis'] + arguments)

    except Exception as error:
        request.dbsession.rollback()
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
