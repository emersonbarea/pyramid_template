from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden


@view_config(route_name='home', renderer='minisecbgp:templates/home.jinja2')
def home(request):
    return {'project': 'MiniSecBGP'}


@view_config(route_name='dashboard', renderer='minisecbgp:templates/dashboard.jinja2')
def dashboard(request):
    user = request.user
    if user is None:
        raise HTTPForbidden
    return {}
