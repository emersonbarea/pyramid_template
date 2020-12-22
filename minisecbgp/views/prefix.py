import ipaddress

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from wtforms import Form, StringField, SubmitField, SelectField, IntegerField
from wtforms.validators import Length, InputRequired
from wtforms.widgets.html5 import NumberInput

from minisecbgp import models


class PrefixDataForm(Form):
    autonomous_system = IntegerField('Enter the ASN for which you want to create, edit or delete a BGP Prefixes: ',
                                     widget=NumberInput(min=0, max=4294967295, step=1),
                                     validators=[InputRequired()])
    prefix_list = SelectField('Or, if you want to edit or delete an existent IPv4 prefix and mask, choose them below: ',
                              coerce=int)
    prefix_add = StringField('If you want to add a new BGP IPv4 prefix, enter the IPv4 and mask here (Ex.: 10.0.0.0/30): ',
                             validators=[Length(min=9, max=18, message=(
                                 'The BGP IPv4 prefix and mask must be between 9 and 18 bytes long '
                                 '(Ex.: 1.1.1.0/8 and 200.200.200.200/30)'))])
    prefix_edit = StringField('Enter the new BGP prefix (IPv4 address and prefix length. Ex.: 192.168.1.0/30): ',
                              validators=[Length(min=9, max=18, message=(
                                  'The BGP IPv4 prefix and mask must be between 9 and 18 bytes long '
                                  '(Ex.: 1.1.1.0/8 and 200.200.200.200/30)'))])
    add_button = SubmitField('Add')
    edit_button = SubmitField('Save')
    delete_button = SubmitField('Delete')


@view_config(route_name='prefix', renderer='minisecbgp:templates/topology/prefix.jinja2')
def prefix(request):
    user = request.user
    if user is None:
        raise HTTPForbidden
    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['form'] = PrefixDataForm(request.POST)
    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='prefixAction', match_param='action=addEditDelete',
             renderer='minisecbgp:templates/topology/prefixAddEditDelete.jinja2')
def prefixAddEditDelete(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    try:
        topology = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['topology'] = topology

        form = PrefixDataForm(request.POST)
        dictionary['form'] = form

        if request.method == 'POST':
            if int(form.autonomous_system.data) > 4294967295:
                dictionary['message'] = 'Invalid Autonomous System Number. Please enter only 16 bits or 32 bits valid ASN.'
                dictionary['css_class'] = 'errorMessage'
                request.override_renderer = 'minisecbgp:templates/topology/prefix.jinja2'
                return dictionary

        autonomousSystem = request.dbsession.query(models.AutonomousSystem). \
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]). \
            filter(models.AutonomousSystem.autonomous_system == form.autonomous_system.data).first()
        if not autonomousSystem:
            dictionary['message'] = 'The Autonomous System Number %s does not exist in topology %s' % \
                                    (form.autonomous_system.data, topology.topology)
            dictionary['css_class'] = 'errorMessage'
            request.override_renderer = 'minisecbgp:templates/topology/prefix.jinja2'
            return dictionary
        dictionary['autonomous_system'] = form.autonomous_system.data

        prefixes_temp = request.dbsession.query(models.Prefix).\
            filter_by(id_autonomous_system=autonomousSystem.id).\
            order_by(models.Prefix.prefix.asc()).all()
        prefixes = list()
        for p in prefixes_temp:
            prefixes.append({'id_prefix': p.id,
                             'prefix': p.prefix + '/' + str(p.mask)})
        form.prefix_list.choices = [(row['id_prefix'], row['prefix']) for row in prefixes]

        if request.method == 'POST':

            if form.add_button.data:
                if form.prefix_add.validate(form.prefix_add.data):
                    ipaddress.ip_network(form.prefix_add.data)
                    entry = models.Prefix(id_autonomous_system=autonomousSystem.id,
                                          prefix=form.prefix_add.data.split('/')[0],
                                          mask=int(form.prefix_add.data.split('/')[1]))
                    request.dbsession.add(entry)
                    request.dbsession.flush()
                    prefixes_temp = request.dbsession.query(models.Prefix). \
                        filter_by(id_autonomous_system=autonomousSystem.id).\
                        order_by(models.Prefix.prefix.asc()).all()
                    prefixes = list()
                    for p in prefixes_temp:
                        prefixes.append({'id_prefix': p.id,
                                         'prefix': p.prefix + '/' + str(p.mask)})
                    form.prefix_list.choices = [(row['id_prefix'], row['prefix']) for row in prefixes]
                    dictionary['message'] = 'BGP Prefix %s added successfully' % form.prefix_add.data
                    dictionary['css_class'] = 'successMessage'
                    form.prefix_add.data = ''
            elif form.edit_button.data:
                if form.prefix_edit.validate(form.prefix_edit.data):
                    ipaddress.ip_network(form.prefix_edit.data)
                    value = dict(form.prefix_list.choices).get(form.prefix_list.data)
                    request.dbsession.query(models.Prefix).filter(models.Prefix.id == form.prefix_list.data).delete()
                    entry = models.Prefix(id_autonomous_system=autonomousSystem.id,
                                          prefix=int(ipaddress.ip_address(form.prefix_edit.data.split('/')[0])),
                                          mask=int(form.prefix_edit.data.split('/')[1]))
                    request.dbsession.add(entry)
                    request.dbsession.flush()
                    prefixes_temp = request.dbsession.query(models.Prefix). \
                        filter_by(id_autonomous_system=autonomousSystem.id). \
                        order_by(models.Prefix.prefix.asc()).all()
                    prefixes = list()
                    for p in prefixes_temp:
                        prefixes.append({'id_prefix': p.id,
                                         'prefix': p.prefix + '/' + str(p.mask)})
                    form.prefix_list.choices = [(row['id_prefix'], row['prefix']) for row in prefixes]
                    dictionary['message'] = 'BGP Prefix %s successfully updated to %s.' % (value, form.prefix_edit.data)
                    dictionary['css_class'] = 'successMessage'

            elif form.delete_button.data:
                value = dict(form.prefix_list.choices).get(form.prefix_list.data)
                request.dbsession.query(models.Prefix).filter(models.Prefix.id == form.prefix_list.data).delete()
                request.dbsession.flush()
                prefixes_temp = request.dbsession.query(models.Prefix). \
                    filter_by(id_autonomous_system=autonomousSystem.id). \
                    order_by(models.Prefix.prefix.asc()).all()
                prefixes = list()
                for p in prefixes_temp:
                    prefixes.append({'id_prefix': p.id,
                                     'prefix': p.prefix + '/' + str(p.mask)})
                form.prefix_list.choices = [(row['id_prefix'], row['prefix']) for row in prefixes]
                dictionary['message'] = 'BGP Prefix %s removed successfully' % value
                dictionary['css_class'] = 'successMessage'
    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='prefixShowAllTxt', renderer='minisecbgp:templates/topology/prefixShowAllTxt.jinja2')
def prefixShowAllTxt(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        prefixes_temp = request.dbsession.query(models.AutonomousSystem, models.Prefix). \
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]). \
            filter(models.AutonomousSystem.id == models.Prefix.id_autonomous_system).\
            order_by(models.AutonomousSystem.autonomous_system.asc()).\
            order_by(models.Prefix.prefix.asc()).all()
        prefixes = list()
        for p in prefixes_temp:
            prefixes.append({'id_prefix': p.Prefix.id,
                             'prefix': p.Prefix.prefix,
                             'mask': p.Prefix.mask,
                             'id_autonomous_system': p.Prefix.id_autonomous_system,
                             'autonomous_system': p.AutonomousSystem.autonomous_system,
                             'id_topology': p.AutonomousSystem.id_topology})
        dictionary['prefixes'] = prefixes

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='prefixShowAllHtml', renderer='minisecbgp:templates/topology/prefixShowAllHtml.jinja2')
def prefixShowAllHtml(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        prefixes_temp = request.dbsession.query(models.AutonomousSystem, models.Prefix). \
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]). \
            filter(models.AutonomousSystem.id == models.Prefix.id_autonomous_system).\
            order_by(models.AutonomousSystem.autonomous_system.asc()).\
            order_by(models.Prefix.prefix.asc()).all()
        prefixes = list()
        for p in prefixes_temp:
            prefixes.append({'id_prefix': p.Prefix.id,
                             'prefix': str(ipaddress.ip_address(p.Prefix.prefix)),
                             'mask': p.Prefix.mask,
                             'id_autonomous_system': p.Prefix.id_autonomous_system,
                             'autonomous_system': p.AutonomousSystem.autonomous_system,
                             'id_topology': p.AutonomousSystem.id_topology})
        dictionary['prefixes'] = prefixes
        number_of_autonomous_systems = request.dbsession.query(models.AutonomousSystem). \
            filter_by(id_topology=request.matchdict["id_topology"]).count()
        dictionary['tabs'] = number_of_autonomous_systems // 10000
        dictionary['number_of_accordions_in_last_tab'] = (number_of_autonomous_systems % 10000) // 1000

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
