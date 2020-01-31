from pyramid.httpexceptions import HTTPFound
from pyramid.security import (
    remember,
    forget,
)
from pyramid.view import (
    forbidden_view_config,
    view_config,
)

from minisecbgp.models import User


@view_config(route_name='login', renderer='minisecbgp:templates/home.jinja2')
def login(request):
    next_url = request.route_url('dashboard')
    message = ''
    if 'form.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']
        user = request.dbsession.query(User).filter_by(username=login).first()
        if user is not None and user.check_password(password):
            headers = remember(request, user.id)
            return HTTPFound(location=next_url, headers=headers)
        message = 'Login Failed'
    return dict(message=message)


@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    next_url = request.route_url('home')
    return HTTPFound(location=next_url, headers=headers)


@forbidden_view_config()
def forbidden_view(request):
    next_url = request.route_url('home')
    return HTTPFound(location=next_url)
