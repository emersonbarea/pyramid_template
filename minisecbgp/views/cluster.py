from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy.exc import IntegrityError
from wtforms import (
    Form,
    StringField,
    PasswordField,
    RadioField,
)
from wtforms.validators import (
    InputRequired,
    Length,
)
from .. import models

import os


class ClusterDataForm(Form):
    node = StringField('Node name/IP address*',
                       validators=[InputRequired(),
                                   Length(min=5, max=30, message=('Node name/IP address must be between 5 and 30 '
                                                                  'characters long.'))])
    username = StringField('Cluster node Username *',
                           validators=[InputRequired(),
                                       Length(min=5, max=30, message=('Username must be between 5 and 30 characters '
                                                                      'long.'))])
    password_hash = PasswordField('Cluster node Password *',
                                  validators=[InputRequired(),
                                              Length(min=5, max=30, message=('Password must be between 5 and 30 '
                                                                             'characters long.'))])
    master = RadioField('Server type *',
                        coerce=int,
                        validators=[InputRequired()],
                        choices=[(0, 'worker'), (1, 'master')])


@view_config(route_name='cluster', renderer='minisecbgp:templates/cluster/cluster.jinja2')
def user(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    #testezica.testezica()
    #print('teste')

    return {}


@view_config(route_name='clusterAction', match_param='action=show', renderer='minisecbgp:templates/cluster'
                                                                             '/showCluster.jinja2')
def show(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    return {}


@view_config(route_name='clusterAction', match_param='action=create', renderer='minisecbgp:templates/cluster'
                                                                               '/createCluster.jinja2')
def create(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    form = ClusterDataForm(request.POST)

    print('teste')

    if request.method == 'POST' and form.validate():
        try:
            entry = models.Cluster(node=form.node.data, username=form.username.data, master=form.master.data)
            entry.set_password(form.password_hash.data)

            # insert row
            request.dbsession.add(entry)
            request.dbsession.flush()

            # topology graph
            with open('minisecbgp:templates/cluster/showCluster.jinja2', 'w') as write_to_file:
                write_to_file.write('          nodes.push({id: "%s"\n' % (form.node.data))
            write_to_file.close()

            message = ('Node "%s" successfully included in cluster.' % form.node.data)
            css_class = 'successMessage'

        except IntegrityError as e:
            request.dbsession.rollback()

            message = ('Node "%s" already exists in cluster.' % form.node.data)
            css_class = 'errorMessage'

        request.override_renderer = 'minisecbgp:templates/cluster/cluster.jinja2'
        return {'message': message, 'css_class': css_class}

    return {'form': form}
