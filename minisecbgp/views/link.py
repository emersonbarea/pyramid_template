import ipaddress

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from wtforms import Form, StringField, SubmitField, SelectField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class LinkDataForm(Form):
    autonomous_system = StringField('Enter the ASN for which you want to create, edit or delete a BGP Prefix: ',
                                    validators=[InputRequired(),
                                                Length(min=1, max=10, message='Autonomous System Number must be between 1 and 32 bits '
                                                                              'number long.')])
    link_list = SelectField('Or, if you want to edit or delete an existent link, choose them below: ',
                            coerce=int)
    autonomous_system1 = StringField('Source ASN *',
                                     validators=[Length(min=1, max=10, message='Autonomous System Number must be between 1 and 32 bits '
                                                                               'number long.')])
    ip_autonomous_system1 = StringField('Source interface IP (decimal. Ex.: 10.0.0.1) *',
                                        validators=[Length(min=9, max=15, message='The IPv4 prefix must be between 9 and 15 bytes long '
                                                                                  '(Ex.: 1.1.1.1 or 200.200.200.201).')])
    autonomous_system2 = StringField('Destination ASN *',
                                     validators=[Length(min=1, max=10, message='Autonomous System Number must be between 1 and 32 bits '
                                                                               'number long.')])
    ip_autonomous_system2 = StringField('Destination interface IP (decimal. Ex.: 10.0.0.2) *',
                                        validators=[Length(min=9, max=15, message='The IPv4 prefix must be between 9 and 15 bytes long '
                                                                                  '(Ex.: 1.1.1.1 or 200.200.200.201).')])
    mask = StringField('Mask (source and destination interfaces) (prefix length. Ex.30) *',
                       validators=[Length(min=1, max=2, message='The mask (prefix length) must be between 1 and 2 bytes long '
                                                                '(Ex.: 8 or 30).')])
    description = StringField('Description',
                              validators=[Length(min=0, max=50, message='The description must be between 0 and 50 bytes long.')])
    bandwidth = StringField('Bandwidth (Kbps)',
                            validators=[Length(min=0, max=50, message='The bandwidth must be between 0 and 50 bytes long.')])
    delay = StringField('Delay (ms)',
                        validators=[Length(min=0, max=50, message='The delay must be between 0 and 50 bytes long.')])
    load = StringField('Load (%)',
                       validators=[Length(min=0, max=50, message='The link load must be between 0 and 50 bytes long.')])
    agreement_list = SelectField('Agreement *', coerce=int)
    add_button = SubmitField('Add')
    edit_button = SubmitField('Save')
    delete_button = SubmitField('Delete')


@view_config(route_name='link', renderer='minisecbgp:templates/topology/link.jinja2')
def link(request):
    user = request.user
    if user is None:
        raise HTTPForbidden
    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['form'] = LinkDataForm(request.POST)
    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='linkShowAll', renderer='minisecbgp:templates/topology/linkShowAll.jinja2')
def linkShowAll(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        query = 'select l.id as id_link, ' \
                'rta.agreement as agreement, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                'l.mask as mask, l.description as description, ' \
                'coalesce(cast(l.bandwidth as varchar), \'__\') as bandwidth, ' \
                'coalesce(cast(l.delay as varchar), \'__\') as delay, ' \
                'coalesce(cast(l.load as varchar), \'__\') as load ' \
                'from link l, realistic_topology_agreement rta ' \
                'where l.id_agreement = rta.id ' \
                'and l.id_topology = %s ' \
                'order by l.id_autonomous_system1, l.id_autonomous_system2;' % request.matchdict["id_topology"]
        links_temp = request.dbsession.bind.execute(query)
        links = list()
        for l in links_temp:
            links.append({'id_link': l.id_link,
                          'agreement': l.agreement,
                          'autonomous_system1': l.autonomous_system1,
                          'ip_autonomous_system1': str(ipaddress.ip_address(l.ip_autonomous_system1)),
                          'autonomous_system2': l.autonomous_system2,
                          'ip_autonomous_system2': str(ipaddress.ip_address(l.ip_autonomous_system2)),
                          'mask': l.mask,
                          'bandwidth': l.bandwidth,
                          'delay': l.delay,
                          'load': l.load})
        dictionary['links'] = links
        number_of_links = request.dbsession.query(models.Link). \
            filter_by(id_topology=request.matchdict["id_topology"]).count()
        dictionary['tabs'] = number_of_links // 10000
        dictionary['number_of_accordions_in_last_tab'] = (number_of_links % 10000) // 1000

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='linkAction', match_param='action=addEditDelete',
             renderer='minisecbgp:templates/topology/linkAddEditDelete.jinja2')
def linkAddEditDelete(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    try:
        topology = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()
        dictionary['topology'] = topology

        form = LinkDataForm(request.POST)
        dictionary['form'] = form

        if request.method == 'POST':
            if int(form.autonomous_system.data) > 4294967295:
                dictionary['message'] = 'Invalid Autonomous System Number. Please enter only 16 bits or 32 bits valid ASN.'
                dictionary['css_class'] = 'errorMessage'
                request.override_renderer = 'minisecbgp:templates/topology/link.jinja2'
                return dictionary

        autonomousSystem = request.dbsession.query(models.AutonomousSystem). \
            filter(models.AutonomousSystem.id_topology == request.matchdict["id_topology"]). \
            filter(models.AutonomousSystem.autonomous_system == form.autonomous_system.data).first()
        if not autonomousSystem:
            dictionary['message'] = 'The Autonomous System Number %s does not exist in topology %s' % \
                                    (form.autonomous_system.data, topology.topology)
            dictionary['css_class'] = 'errorMessage'
            request.override_renderer = 'minisecbgp:templates/topology/link.jinja2'
            return dictionary
        dictionary['autonomous_system'] = form.autonomous_system.data
        form.autonomous_system1.data = dictionary['autonomous_system']

        query = 'select l.id as id_link, ' \
                'rta.agreement as agreement, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                'l.mask as mask, l.description as description, ' \
                'coalesce(cast(l.bandwidth as varchar), \'__\') as bandwidth, ' \
                'coalesce(cast(l.delay as varchar), \'__\') as delay, ' \
                'coalesce(cast(l.load as varchar), \'__\') as load ' \
                'from link l, realistic_topology_agreement rta ' \
                'where l.id_agreement = rta.id ' \
                'and (l.id_autonomous_system1 = %s or l.id_autonomous_system2 = %s) ' \
                'order by l.id_autonomous_system2;' % (autonomousSystem.id, autonomousSystem.id)
        links_temp = request.dbsession.bind.execute(query)
        links = list()
        for l in links_temp:
            links.append({'id_link': l.id_link,
                          'link': 'AS ' + str(l.autonomous_system1) + ' (' + str(ipaddress.ip_address(l.ip_autonomous_system1)) + ') <--> AS ' +
                                  str(l.autonomous_system2) + ' (' + str(ipaddress.ip_address(l.ip_autonomous_system2)) + ') - Bw: ' +
                                  l.bandwidth + ' Kbps - Load: ' + l.load + ' % - Delay: ' + l.delay + ' ms -- (' + l.agreement + ')'})
        dictionary['links'] = links
        form.link_list.choices = [(row['id_link'], row['link']) for row in links]

        form.agreement_list.choices = [(row.id, row.agreement) for row in
                                       request.dbsession.query(models.RealisticTopologyAgreements)]

        if request.method == 'POST':

            if form.add_button.data:
                if form.prefix_add.validate(form.prefix_add.data):
                    ipaddress.ip_network(form.prefix_add.data)
                    entry = models.Prefix(id_autonomous_system=autonomousSystem.id,
                                          prefix=int(ipaddress.ip_address(form.prefix_add.data.split('/')[0])),
                                          mask=int(form.prefix_add.data.split('/')[1]))
                    request.dbsession.add(entry)
                    request.dbsession.flush()
                    prefixes_temp = request.dbsession.query(models.Prefix). \
                        filter_by(id_autonomous_system=autonomousSystem.id).\
                        order_by(models.Prefix.prefix.asc()).all()
                    prefixes = list()
                    for p in prefixes_temp:
                        prefixes.append({'id_prefix': p.id,
                                         'prefix': str(ipaddress.ip_address(p.prefix)) + '/' + str(p.mask)})
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
                                         'prefix': str(ipaddress.ip_address(p.prefix)) + '/' + str(p.mask)})
                    form.prefix_list.choices = [(row['id_prefix'], row['prefix']) for row in prefixes]
                    dictionary['message'] = 'BGP Prefix %s successfully updated to %s.' % (value, form.prefix_edit.data)
                    dictionary['css_class'] = 'successMessage'

            elif form.delete_button.data:
                delete = 'delete from link where id = %s' % form.link_list.data
                request.dbsession.bind.execute(delete)
                query = 'select l.id as id_link, ' \
                        'rta.agreement as agreement, ' \
                        '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                        'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                        '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                        'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                        'l.mask as mask, l.description as description, ' \
                        'coalesce(cast(l.bandwidth as varchar), \'__\') as bandwidth, ' \
                        'coalesce(cast(l.delay as varchar), \'__\') as delay, ' \
                        'coalesce(cast(l.load as varchar), \'__\') as load ' \
                        'from link l, realistic_topology_agreement rta ' \
                        'where l.id_agreement = rta.id ' \
                        'and (l.id_autonomous_system1 = %s or l.id_autonomous_system2 = %s) ' \
                        'order by l.id_autonomous_system2;' % (autonomousSystem.id, autonomousSystem.id)
                links_temp = request.dbsession.bind.execute(query)
                links = list()
                for l in links_temp:
                    links.append({'id_link': l.id_link,
                                  'link': 'AS ' + str(l.autonomous_system1) + ' (' +
                                          str(ipaddress.ip_address(l.ip_autonomous_system1)) + ') <--> AS ' +
                                          str(l.autonomous_system2) + ' (' +
                                          str(ipaddress.ip_address(l.ip_autonomous_system2)) + ') - Bw: ' +
                                          l.bandwidth + ' Kbps - Load: ' + l.load + ' % - Delay: ' +
                                          l.delay + ' ms -- (' + l.agreement + ')'})
                dictionary['links'] = links
                form.link_list.choices = [(row['id_link'], row['link']) for row in links]
                dictionary['message'] = 'Link removed successfully'
                dictionary['css_class'] = 'successMessage'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
