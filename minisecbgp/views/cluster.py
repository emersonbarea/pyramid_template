import os
import subprocess

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy.exc import IntegrityError
from wtforms import Form, StringField, PasswordField, SelectField
from wtforms.validators import InputRequired, Length
from minisecbgp import models

from minisecbgp.scripts.services import local_command


class ClusterDataForm(Form):
    node = StringField('Node name/IP address: *',
                       validators=[InputRequired(),
                                   Length(min=1, max=50, message=('Node name/IP address must be between 1 and 50 '
                                                                  'characters long.'))])
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

    nodes = request.dbsession.query(models.Node).all()

    dictionary = dict()
    dictionary['nodes'] = nodes
    dictionary['cluster_url'] = request.route_url('cluster')
    dictionary['cluster_detail_url'] = request.route_url('clusterDetail', id='')

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
            node = models.Node(node=form.node.data,
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
                               install_containernet=2,
                               install_metis=2,
                               install_maxinet=2,
                               all_install=2
                               )
            request.dbsession.add(node)
            request.dbsession.flush()

            arguments = ['--config-file=minisecbgp.ini',
                         '--execution-type=manual',
                         '--hostname=%s' % form.node.data,
                         '--username=%s' % form.username.data,
                         '--password=%s' % form.password.data]
            subprocess.Popen(['./venv/bin/tests'] + arguments)

            arguments = ['--config-file=minisecbgp.ini',
                         '--hostname=%s' % form.node.data,
                         '--username=%s' % form.username.data,
                         '--password=%s' % form.password.data]

            subprocess.Popen(['./venv/bin/config'] + arguments)

            home_dir = os.getcwd()
            command = 'sudo -u minisecbgpuser bash -c \'echo -e "# Start job every 1 minute (monitor %s)\n' \
                      '* * * * * minisecbgpuser %s/venv/bin/tests ' \
                      '--config-file=%s/minisecbgp.ini ' \
                      '--execution-type=\\"scheduled\\" ' \
                      '--hostname=\\"%s\\" ' \
                      '--username=\\"\\" ' \
                      '--password=\\"\\"" | ' \
                      'sudo tee /etc/cron.d/minisecbgp_tests_%s\'' % \
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
        nodes = request.dbsession.query(models.Node).all()

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
    if user is None:
        raise HTTPForbidden

    form = ClusterDataFormSelectField(request.POST)
    form.cluster_list.choices = [(row.id, row.node) for row in
                                 request.dbsession.query(models.Node).filter(models.Node.master != 1)]

    if request.method == 'POST' and form.validate():
        value = dict(form.cluster_list.choices).get(form.cluster_list.data)
        try:
            request.dbsession.query(models.Node).filter(models.Node.id == form.cluster_list.data).delete()

            command = 'sudo -u minisecbgpuser bash -c \'sudo rm /etc/cron.d/minisecbgp_tests_%s\'' % value
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
        nodes = request.dbsession.query(models.Node).all()

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
    dictionary = dict()
    entry = request.dbsession.query(models.Node).filter_by(id=request.matchdict["id"]).first()
    dictionary['entry'] = entry
    dictionary['cluster_detail_url'] = request.route_url('clusterDetail', id='')

    return dictionary
