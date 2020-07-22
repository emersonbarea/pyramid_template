import ipaddress
import os
import subprocess

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy.exc import IntegrityError
from wtforms import Form, StringField, PasswordField, SelectField
from wtforms.validators import InputRequired, Length, IPAddress
from minisecbgp import models

from minisecbgp.scripts.services import local_command


class ClusterDataForm(Form):
    node = StringField('Cluster node IP address (Ex.: 192.168.1.1): *',
                       validators=[InputRequired(),
                                   IPAddress(ipv4=True, message='Enter only IPv4 address format.')])
    node_type = StringField('Node type: *')

    username = StringField('Cluster node Username: *',
                           validators=[InputRequired(),
                                       Length(min=1, max=50, message=('Username must be between 1 and 50 characters '
                                                                      'long.'))])
    password = PasswordField('Cluster node Password: *',
                             validators=[InputRequired(),
                                         Length(min=1, max=50, message=('Password must be between 1 and 50 characters '
                                                                        'long.'))])


class ClusterDataFormSelectField(Form):
    cluster_list = SelectField('cluster_list', coerce=int,
                               validators=[InputRequired()])


@view_config(route_name='cluster', renderer='minisecbgp:templates/cluster/showCluster.jinja2')
def cluster(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        nodes_temp = request.dbsession.query(models.Node).all()
        nodes = list()
        for node in nodes_temp:
            services = request.dbsession.query(models.NodeService, models.Service).\
                filter(models.NodeService.id_service == models.Service.id).\
                filter(models.NodeService.id_node == node.id).all()
            all_services = 1
            for service in services:                                                          # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
                if service.NodeService.status == 0 and all_services != 2:
                    all_services = 0
                if service.NodeService.status == 1:
                    all_services = 1
                    break
                elif service.NodeService.status == 2:
                    all_services = 2

            configurations = request.dbsession.query(models.NodeConfiguration, models.Configuration).\
                filter(models.NodeConfiguration.id_configuration == models.Configuration.id).\
                filter(models.NodeConfiguration.id_node == node.id).all()
            all_configurations = 1
            for configuration in configurations:                                              # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
                if configuration.NodeConfiguration.status == 0 and all_configurations != 2:
                    all_configurations = 0
                if configuration.NodeConfiguration.status == 1:
                    all_configurations = 1
                    break
                elif configuration.NodeConfiguration.status == 2:
                    all_configurations = 2

            installs = request.dbsession.query(models.NodeInstall, models.Install).\
                filter(models.NodeInstall.id_install == models.Install.id).\
                filter(models.NodeInstall.id_node == node.id).all()
            all_installs = 1
            for install in installs:                                                          # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
                if install.NodeInstall.status == 0 and all_installs != 2:
                    all_installs = 0
                if install.NodeInstall.status == 1:
                    all_installs = 1
                    break
                elif install.NodeInstall.status == 2:
                    all_installs = 2

            nodes.append({'id': node.id,
                          'node': str(ipaddress.ip_address(node.node)),
                          'hostname': node.hostname,
                          'master': ('master' if node.master else 'worker'),
                          'all_services': all_services,
                          'all_configurations': all_configurations,
                          'all_installs': all_installs})

        dictionary['nodes'] = nodes
        dictionary['cluster_url'] = request.route_url('cluster')
        dictionary['cluster_detail_url'] = request.route_url('clusterDetail', id='')

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='clusterAction', match_param='action=create', renderer='minisecbgp:templates/cluster'
                                                                               '/createCluster.jinja2')
def create(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    master = request.dbsession.query(models.Node).filter(models.Node.master == 1).first()
    if master:
        form = ClusterDataForm(request.POST, node_type='worker')
        nodeTypeMessage = ' - WORKER'
        nodeType = '0'
    else:
        form = ClusterDataForm(request.POST, node_type='master')
        nodeTypeMessage = ' - MASTER'
        nodeType = '1'

    if request.method == 'POST' and form.validate():
        try:
            node = models.Node(node=int(ipaddress.ip_address(form.node.data)),
                               status=2,
                               hostname=2,
                               username=form.username.data,
                               master=nodeType,
                               service_ping=2,
                               service_ssh=2,
                               all_services=2,
                               conf_user=2,
                               conf_ssh=2,
                               install_remote_prerequisites=2,
                               install_mininet=2,
                               install_containernet=2,
                               install_metis=2,
                               install_maxinet=2,
                               all_install=2
                               )
            request.dbsession.add(node)
            request.dbsession.flush()

            arguments = ['--config-file=minisecbgp.ini',
                         '--execution-type=manual',
                         '--node-ip-address=%s' % form.node.data,
                         '--username=%s' % form.username.data,
                         '--password=%s' % form.password.data]
            subprocess.Popen(['./venv/bin/MiniSecBGP_node_service'] + arguments)

            arguments = ['--config-file=minisecbgp.ini',
                         '--node-ip-address=%s' % form.node.data,
                         '--username=%s' % form.username.data,
                         '--password=%s' % form.password.data]

            subprocess.Popen(['./venv/bin/MiniSecBGP_node_configuration'] + arguments)

            subprocess.Popen(['./venv/bin/MiniSecBGP_node_install'] + arguments)

            home_dir = os.getcwd()
            command = 'sudo -u minisecbgpuser bash -c \'echo -e "# Start job every 1 minute (monitor %s)\n' \
                      '* * * * * minisecbgpuser %s/venv/bin/MiniSecBGP_node_service ' \
                      '--config-file=%s/minisecbgp.ini ' \
                      '--execution-type=\\"scheduled\\" ' \
                      '--node-ip-address=\\"%s\\" ' \
                      '--username=\\"\\" ' \
                      '--password=\\"\\"" | ' \
                      'sudo tee /etc/cron.d/MiniSecBGP_node_service_%s\'' % \
                      (form.node.data, home_dir, home_dir, form.node.data, form.node.data)
            result = local_command.local_command(command)
            if result[0] == 1:
                print('Crontab error', str(result[2].decode()))

            message = ('Node "%s" successfully included in cluster.' % form.node.data)
            css_class = 'successMessage'

        except IntegrityError as e:
            request.dbsession.rollback()
            message = ('Node "%s" already exists in cluster.' % form.node.data)
            css_class = 'errorMessage'

        request.override_renderer = 'minisecbgp:templates/cluster/showCluster.jinja2'

        nodes_temp = request.dbsession.query(models.Node).all()
        nodes = list()
        for n in nodes_temp:
            nodes.append({'id': n.id,
                          'node': str(ipaddress.ip_address(n.node)),
                          'status': n.status,
                          'hostname': n.hostname,
                          'hostname_status': n.hostname_status,
                          'username': n.username,
                          'master': n.master,
                          'service_ping': n.service_ping,
                          'service_ssh': n.service_ssh,
                          'service_ssh_status': n.service_ssh_status,
                          'all_services': n.all_services,
                          'conf_user': n.conf_user,
                          'conf_user_status': n.conf_user_status,
                          'conf_ssh': n.conf_ssh,
                          'conf_ssh_status': n.conf_ssh_status,
                          'install_remote_prerequisites': n.install_remote_prerequisites,
                          'install_remote_prerequisites_status': n.install_remote_prerequisites_status,
                          'install_mininet': n.install_mininet,
                          'install_mininet_status': n.install_mininet_status,
                          'install_containernet': n.install_containernet,
                          'install_containernet_status': n.install_containernet_status,
                          'install_metis': n.install_metis,
                          'install_metis_status': n.install_metis_status,
                          'install_maxinet': n.install_maxinet,
                          'install_maxinet_status': n.install_maxinet_status,
                          'all_install': n.all_install})

        dictionary = dict()
        dictionary['nodes'] = nodes
        dictionary['message'] = message
        dictionary['css_class'] = css_class
        dictionary['cluster_url'] = request.route_url('cluster')
        dictionary['cluster_detail_url'] = request.route_url('clusterDetail', id='')

        return dictionary

    return {'form': form, 'nodeTypeMessage': nodeTypeMessage}


@view_config(route_name='clusterAction', match_param='action=delete', renderer='minisecbgp:templates/cluster'
                                                                               '/deleteCluster.jinja2')
def delete(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    form = ClusterDataFormSelectField(request.POST)
    form.cluster_list.choices = [(row.id, ipaddress.ip_address(row.node)) for row in
                                 request.dbsession.query(models.Node).filter(models.Node.master != 1)]

    if request.method == 'POST' and form.validate():
        value = dict(form.cluster_list.choices).get(form.cluster_list.data)
        try:
            node = request.dbsession.query(models.Node).filter(models.Node.id == form.cluster_list.data).first()
            host = str(ipaddress.ip_address(node.node))
            request.dbsession.delete(node)

            command = 'sudo -u minisecbgpuser bash -c \'sudo rm /etc/cron.d/MiniSecBGP_node_service_%s\'' % host
            result = local_command.local_command(command)
            if result[0] == 1:
                print('Crontab delete error', str(result[2].decode()))

            message = ('Cluster node "%s" successfully deleted.' % value)
            css_class = 'successMessage'

        except IntegrityError as e:
            request.dbsession.rollback()
            message = ('Cluster node "%s" does not exist.' % form.cluster_list.data)
            css_class = 'errorMessage'

        request.override_renderer = 'minisecbgp:templates/cluster/showCluster.jinja2'

        nodes_temp = request.dbsession.query(models.Node).all()
        nodes = list()
        for n in nodes_temp:
            nodes.append({'id': n.id,
                          'node': str(ipaddress.ip_address(n.node)),
                          'status': n.status,
                          'hostname': n.hostname,
                          'hostname_status': n.hostname_status,
                          'username': n.username,
                          'master': n.master,
                          'service_ping': n.service_ping,
                          'service_ssh': n.service_ssh,
                          'service_ssh_status': n.service_ssh_status,
                          'all_services': n.all_services,
                          'conf_user': n.conf_user,
                          'conf_user_status': n.conf_user_status,
                          'conf_ssh': n.conf_ssh,
                          'conf_ssh_status': n.conf_ssh_status,
                          'install_remote_prerequisites': n.install_remote_prerequisites,
                          'install_remote_prerequisites_status': n.install_remote_prerequisites_status,
                          'install_mininet': n.install_mininet,
                          'install_mininet_status': n.install_mininet_status,
                          'install_containernet': n.install_containernet,
                          'install_containernet_status': n.install_containernet_status,
                          'install_metis': n.install_metis,
                          'install_metis_status': n.install_metis_status,
                          'install_maxinet': n.install_maxinet,
                          'install_maxinet_status': n.install_maxinet_status,
                          'all_install': n.all_install})

        dictionary = dict()
        dictionary['nodes'] = nodes
        dictionary['message'] = message
        dictionary['css_class'] = css_class
        dictionary['cluster_url'] = request.route_url('cluster')
        dictionary['cluster_detail_url'] = request.route_url('clusterDetail', id='')

        return dictionary

    return {'form': form}


@view_config(route_name='clusterDetail', renderer='minisecbgp:templates/cluster/detailCluster.jinja2')
def clusterDetail(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()

    try:
        node_temp = request.dbsession.query(models.Node).\
            filter_by(id=request.matchdict["id"]).first()
        node = {'id': node_temp.id,
                'node': str(ipaddress.ip_address(node_temp.node)),
                'status': node_temp.status,
                'hostname': node_temp.hostname,
                'hostname_status': node_temp.hostname_status,
                'username': node_temp.username,
                'master': node_temp.master,
                'service_ping': node_temp.service_ping,
                'service_ssh': node_temp.service_ssh,
                'service_ssh_status': node_temp.service_ssh_status,
                'all_services': node_temp.all_services,
                'conf_user': node_temp.conf_user,
                'conf_user_status': node_temp.conf_user_status,
                'conf_ssh': node_temp.conf_ssh,
                'conf_ssh_status': node_temp.conf_ssh_status,
                'install_remote_prerequisites': node_temp.install_remote_prerequisites,
                'install_remote_prerequisites_status': node_temp.install_remote_prerequisites_status,
                'install_mininet': node_temp.install_mininet,
                'install_mininet_status': node_temp.install_mininet_status,
                'install_containernet': node_temp.install_containernet,
                'install_containernet_status': node_temp.install_containernet_status,
                'install_metis': node_temp.install_metis,
                'install_metis_status': node_temp.install_metis_status,
                'install_maxinet': node_temp.install_maxinet,
                'install_maxinet_status': node_temp.install_maxinet_status,
                'all_install': node_temp.all_install}

        dictionary['node'] = node
        dictionary['cluster_detail_url'] = request.route_url('clusterDetail', id='')

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
