from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden

from ..scripts import testezica


@view_config(route_name='cluster', renderer='minisecbgp:templates/cluster/cluster.jinja2')
def user(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    testezica.testezica()

    return {}
