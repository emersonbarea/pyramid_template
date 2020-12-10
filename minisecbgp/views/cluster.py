import ipaddress
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
                                   IPAddress(ipv4=True, ipv6=True, message='Enter only IPv4 or IPv6 address format.')])
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


def nodes(request):
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

            message = ''
            css_class = ''
    except Exception as error:
        nodes = ''
        message = error
        css_class = 'errorMessage'

    return nodes, message, css_class


@view_config(route_name='cluster', renderer='minisecbgp:templates/cluster/showCluster.jinja2')
def cluster(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['nodes'], dictionary['message'], dictionary['css_class'] = nodes(request)
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

    form = ClusterDataForm(request.POST)

    if request.method == 'POST' and form.validate():
        try:
            node = request.dbsession.query(models.Node).\
                filter_by(node=str(ipaddress.ip_address(form.node.data))).first()
            if not node:
                arguments = ['--config-file=minisecbgp.ini',
                             '--node-ip-address=%s' % form.node.data,
                             '--master=False']
                subprocess.run(['./venv/bin/MiniSecBGP_node_create'] + arguments)                       # wait to finish

                arguments = ['--config-file=minisecbgp.ini',
                             '--execution-type=manual',
                             '--node-ip-address=%s' % form.node.data,
                             '--username=%s' % form.username.data,
                             '--password=%s' % form.password.data]
                subprocess.Popen(['./venv/bin/MiniSecBGP_node_service'] + arguments)                    # runs in parallel

                arguments = ['--config-file=minisecbgp.ini',
                             '--node-ip-address=%s' % form.node.data,
                             '--username=%s' % form.username.data,
                             '--password=%s' % form.password.data]

                subprocess.run(['./venv/bin/MiniSecBGP_node_configuration'] + arguments)                # wait to finish

                subprocess.Popen(['./venv/bin/MiniSecBGP_node_install'] + arguments)                    # runs in parallel

                message = ('Node "%s" successfully included in cluster.' % form.node.data)
                css_class = 'successMessage'

                request.dbsession.flush()
            else:
                message = ('Node "%s" already exists in cluster.' % form.node.data)
                css_class = 'errorMessage'

        except IntegrityError as e:
            request.dbsession.rollback()
            message = ('Node "%s" already exists in cluster.' % form.node.data)
            css_class = 'errorMessage'

        request.override_renderer = 'minisecbgp:templates/cluster/showCluster.jinja2'

        dictionary = dict()
        dictionary['nodes'], message_temp, css_class_temp = nodes(request)
        if message_temp:
            message = message_temp
        if css_class_temp:
            css_class = css_class_temp

        dictionary['message'] = message
        dictionary['css_class'] = css_class
        dictionary['cluster_url'] = request.route_url('cluster')
        dictionary['cluster_detail_url'] = request.route_url('clusterDetail', id='')

        return dictionary

    return {'form': form}


@view_config(route_name='clusterAction', match_param='action=delete', renderer='minisecbgp:templates/cluster'
                                                                               '/deleteCluster.jinja2')
def delete(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    form = ClusterDataFormSelectField(request.POST)
    form.cluster_list.choices = [(row.id, ipaddress.ip_address(row.node)) for row in
                                 request.dbsession.query(models.Node).filter(models.Node.master.is_(False))]

    if request.method == 'POST' and form.validate():
        value = dict(form.cluster_list.choices).get(form.cluster_list.data)
        try:
            node = request.dbsession.query(models.Node).filter(models.Node.id == form.cluster_list.data).first()

            services = request.dbsession.query(models.NodeService). \
                filter_by(id_node=node.id).all()

            configurations = request.dbsession.query(models.NodeConfiguration). \
                filter_by(id_node=node.id).all()

            installs = request.dbsession.query(models.NodeInstall). \
                filter_by(id_node=node.id).all()

            command = 'sudo -u minisecbgpuser bash -c \'sudo rm /etc/cron.d/MiniSecBGP_node_service_%s\' 2> /dev/null' % node.node
            result = local_command.local_command(command)

            for install in installs:
                request.dbsession.delete(install)
            for configuration in configurations:
                request.dbsession.delete(configuration)
            for service in services:
                request.dbsession.delete(service)
            request.dbsession.delete(node)

            message = ('Cluster node "%s" successfully deleted.' % value)
            css_class = 'successMessage'

            request.dbsession.flush()
        except IntegrityError as e:
            request.dbsession.rollback()
            message = ('Cluster node "%s" does not exist.' % form.cluster_list.data)
            css_class = 'errorMessage'

        request.override_renderer = 'minisecbgp:templates/cluster/showCluster.jinja2'

        dictionary = dict()
        dictionary['nodes'], message_temp, css_class_temp = nodes(request)
        if message_temp:
            message = message_temp
        if css_class_temp:
            css_class = css_class_temp

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
                'hostname': node_temp.hostname if node_temp.hostname else '--',
                'master': node_temp.master}

        services = request.dbsession.query(models.NodeService, models.Service).\
            filter(models.NodeService.id_node == request.matchdict["id"]).\
            filter(models.NodeService.id_service == models.Service.id).\
            order_by(models.Service.id).all()

        configurations = request.dbsession.query(models.NodeConfiguration, models.Configuration).\
            filter(models.NodeConfiguration.id_node == request.matchdict["id"]).\
            filter(models.NodeConfiguration.id_configuration == models.Configuration.id).\
            order_by(models.Configuration.id).all()

        installs = request.dbsession.query(models.NodeInstall, models.Install).\
            filter(models.NodeInstall.id_node == request.matchdict["id"]).\
            filter(models.NodeInstall.id_install == models.Install.id).\
            order_by(models.Install.id).all()

        dictionary['node'] = node
        dictionary['services'] = services
        dictionary['configurations'] = configurations
        dictionary['installs'] = installs
        dictionary['cluster_detail_url'] = request.route_url('clusterDetail', id='')

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
