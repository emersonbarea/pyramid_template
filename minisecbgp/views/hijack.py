from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden

from minisecbgp import models


@view_config(route_name='hijack', renderer='minisecbgp:templates/hijack/hijack.jinja2')
def hijack(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()

    return dictionary


@view_config(route_name='hijackAffectedArea', renderer='minisecbgp:templates/hijack/hijackAffectedArea.jinja2')
def hijackAffectedArea(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()

    return dictionary


@view_config(route_name='hijackRealisticAnalysis', renderer='minisecbgp:templates/hijack/hijackRealisticAnalysis.jinja2')
def hijackRealisticAnalysis(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()

    return dictionary
