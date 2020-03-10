import subprocess

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy.exc import IntegrityError
from wtforms import Form, StringField, PasswordField, SelectField
from wtforms.validators import InputRequired, Length
from minisecbgp import models


class ClusterDataForm(Form):
    node = StringField('Node name/IP address*',
                       validators=[InputRequired(),
                                   Length(min=1, max=50, message=('Node name/IP address must be between 1 and 50 '
                                                                  'characters long.'))])
    node_type = StringField('Node type *')

    username = StringField('Cluster node Username *',
                           validators=[InputRequired(),
                                       Length(min=1, max=50, message=('Username must be between 1 and 50 characters '
                                                                      'long.'))])
    password = PasswordField('Cluster node Password *',
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
                               service_app=2,
                               conf_user=2,
                               conf_ssh=2,
                               install_remote_prerequisites=2,
                               install_containernet=2,
                               install_metis=2,
                               install_maxinet=2
                               )
            request.dbsession.add(node)
            request.dbsession.flush()

            arguments = ['--config_file=minisecbgp.ini',
                         '--execution_type=create_node',
                         '--hostname=%s' % form.node.data,
                         '--username=%s' % form.username.data,
                         '--password=%s' % form.password.data]
            subprocess.Popen(['tests'] + arguments)

            arguments = ['--config_file=minisecbgp.ini',
                         '--hostname=%s' % form.node.data,
                         '--username=%s' % form.username.data,
                         '--password=%s' % form.password.data]
            subprocess.Popen(['config'] + arguments)

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
    entry = request.dbsession.query(models.Node).filter_by(id=request.matchdict["id"]).first()

    return {'entry': entry}
