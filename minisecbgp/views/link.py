import ipaddress

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from wtforms import Form, StringField, SubmitField, SelectField, IntegerField, validators
from wtforms.validators import Length, InputRequired
from wtforms.widgets.html5 import NumberInput

from minisecbgp import models


class LinkDataForm(Form):
    autonomous_system = IntegerField('Enter the ASN for which you want to create, edit or delete a BGP Peering: ',
                                     widget=NumberInput(min=0, max=4294967295, step=1),
                                     validators=[InputRequired()])
    link_list = SelectField('Or, if you want to edit or delete an existent peer, choose it below: ',
                            coerce=int)
    autonomous_system1 = IntegerField('Peering source Autonomous System: ',
                                      widget=NumberInput(min=0, max=4294967295, step=1))
    ip_autonomous_system1 = StringField('IP address of the peering source interface (decimal. Ex.: 10.0.0.1): *',
                                        validators=[Length(min=7, max=15, message='The IPv4 prefix must be between 7 and 15 bytes long '
                                                                                  '(Ex.: 1.1.1.1 or 200.200.200.201).')])
    autonomous_system2 = IntegerField('Peering destination Autonomous System: ',
                                      widget=NumberInput(min=0, max=4294967295, step=1))
    ip_autonomous_system2 = StringField('IP address of the peering destination interface (decimal. Ex.: 10.0.0.2): *',
                                        validators=[Length(min=7, max=15, message='The IPv4 prefix must be between 7 and 15 bytes long '
                                                                                  '(Ex.: 1.1.1.1 or 200.200.200.201).')])
    mask = IntegerField('Mask (source and destination interfaces) (prefix length. Ex.30): *',
                        widget=NumberInput(min=8, max=30, step=2))
    description = StringField('Description: ',
                              validators=[Length(min=0, max=50, message='The description must be between 0 and 50 bytes long.')])
    bandwidth = IntegerField('Link bandwidth (Kbps): ',
                             widget=NumberInput(min=0, max=1000000000, step=1),
                             validators=[validators.Optional()])
    delay = IntegerField('Link delay (ms): ',
                         widget=NumberInput(min=0, max=1000000000, step=1),
                         validators=[validators.Optional()])
    load = IntegerField('Link load (%): ',
                        widget=NumberInput(min=0, max=100, step=1),
                        validators=[validators.Optional()])
    agreement_list = SelectField('Peers agreement: *', coerce=int)

    edit_autonomous_system1 = IntegerField('Enter the ASN for which you want to create, edit or delete a BGP Peering: ',
                                           widget=NumberInput(min=0, max=4294967295, step=1))
    edit_ip_autonomous_system1 = StringField('Source interface IP (decimal. Ex.: 10.0.0.1) *',
                                             validators=[Length(min=7, max=15, message='The IPv4 prefix must be between 7 and 15 bytes long '
                                                                                       '(Ex.: 1.1.1.1 or 200.200.200.201).')])
    edit_autonomous_system2 = IntegerField('Enter the ASN for which you want to create, edit or delete a BGP Peering: ',
                                           widget=NumberInput(min=0, max=4294967295, step=1))
    edit_ip_autonomous_system2 = StringField('Destination interface IP (decimal. Ex.: 10.0.0.2): *',
                                             validators=[Length(min=7, max=15, message='The IPv4 prefix must be between 7 and 15 bytes long '
                                                                                       '(Ex.: 1.1.1.1 or 200.200.200.201).')])
    edit_mask = IntegerField('Mask (source and destination interfaces) (prefix length. Ex.30): *',
                             widget=NumberInput(min=8, max=30, step=2))
    edit_description = StringField('Description: ',
                                   validators=[Length(min=0, max=50, message='The description must be between 0 and 50 bytes long.')])
    edit_bandwidth = IntegerField('Bandwidth (Kbps): ',
                                  widget=NumberInput(min=0, max=1000000000, step=1),
                                  validators=[validators.Optional()])
    edit_delay = IntegerField('Delay (ms): ',
                              widget=NumberInput(min=0, max=1000000000, step=1),
                              validators=[validators.Optional()])
    edit_load = IntegerField('Load (%): ',
                             widget=NumberInput(min=0, max=100, step=1),
                             validators=[validators.Optional()])
    edit_agreement_list = SelectField('Agreement: *', coerce=int)
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


@view_config(route_name='linkAction', match_param='action=addEditDelete',
             renderer='minisecbgp:templates/topology/linkAddEditDelete.jinja2')
def linkAddEditDelete(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    def stub(autonomous_system1, autonomous_system2):
        query = 'select count(id) as count ' \
                'from link ' \
                'where id_autonomous_system1 = %s ' \
                'or id_autonomous_system2 = %s;' % (autonomous_system1, autonomous_system1)
        count_autonomous_system1 = request.dbsession.bind.execute(query)
        for stub_autonomous_system1 in count_autonomous_system1:
            if stub_autonomous_system1.count > 1:
                autonomous_system = request.dbsession.query(models.AutonomousSystem).\
                    filter_by(id=autonomous_system1).first()
                autonomous_system.stub = False
            else:
                autonomous_system = request.dbsession.query(models.AutonomousSystem).\
                    filter_by(id=autonomous_system1).first()
                autonomous_system.stub = True

        query = 'select count(id) as count ' \
                'from link ' \
                'where id_autonomous_system1 = %s ' \
                'or id_autonomous_system2 = %s;' % (autonomous_system2, autonomous_system2)
        count_autonomous_system2 = request.dbsession.bind.execute(query)
        for stub_autonomous_system2 in count_autonomous_system2:
            if stub_autonomous_system2.count > 1:
                autonomous_system = request.dbsession.query(models.AutonomousSystem).\
                    filter_by(id=autonomous_system2).first()
                autonomous_system.stub = False
            else:
                autonomous_system = request.dbsession.query(models.AutonomousSystem).\
                    filter_by(id=autonomous_system2).first()
                autonomous_system.stub = True

    def fillSelectFields():
        query = 'select l.id as id_link, ' \
                'la.agreement as agreement, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                'l.mask as mask, ' \
                'l.description as description, ' \
                'l.bandwidth as bandwidth, ' \
                'l.delay as delay, ' \
                'l.load as load ' \
                'from link l, link_agreement la ' \
                'where l.id_link_agreement = la.id ' \
                'and (l.id_autonomous_system1 = %s or l.id_autonomous_system2 = %s) ' \
                'order by l.id_autonomous_system2;' % (autonomousSystem.id, autonomousSystem.id)
        links_temp = request.dbsession.bind.execute(query)
        links = list()
        for l in links_temp:
            links.append({'id_link': l.id_link,
                          'link': 'AS ' + str(l.autonomous_system1) +
                                  ' ( ' + l.ip_autonomous_system1 +
                                  ' / ' + str(l.mask) +
                                  ' ) <--> AS ' + str(l.autonomous_system2) +
                                  ' ( ' + l.ip_autonomous_system2 +
                                  ' / ' + str(l.mask) +
                                  ' ) -- ( Bw : ' + (str(l.bandwidth) if l.bandwidth else '__') +
                                  ' Kbps ) -- ( Load : ' + (str(l.load) if l.load else '__') +
                                  ' % ) -- ( Delay : ' + (str(l.delay) if l.delay else '__') +
                                  ' ms ) -- ( Agreement : ' + l.agreement +
                                  ' ) -- ( Description : ' + (l.description if l.description else '__') + ' )'})
        dictionary['links'] = links
        form.link_list.choices = [(row['id_link'], row['link']) for row in links]
        form.agreement_list.choices = [(row.id, row.agreement) for row in
                                       request.dbsession.query(models.LinkAgreement)]
        form.edit_agreement_list.choices = [(row.id, row.agreement) for row in
                                            request.dbsession.query(models.LinkAgreement)]

    def clearFields():
        form.ip_autonomous_system1.data = ''
        form.autonomous_system2.data = ''
        form.ip_autonomous_system2.data = ''
        form.mask.data = ''
        form.description.data = ''
        form.bandwidth.data = ''
        form.delay.data = ''
        form.load.data = ''
        fillSelectFields()

    def insert(id_topology, id_link_agreement, autonomous_system1, autonomous_system2, ip_autonomous_system1,
               ip_autonomous_system2, mask, description, bandwidth, delay, load, message):
        as1_id = request.dbsession.query(models.AutonomousSystem). \
            filter(models.AutonomousSystem.id_topology == id_topology). \
            filter(models.AutonomousSystem.autonomous_system == autonomous_system1).first()
        as2_id = request.dbsession.query(models.AutonomousSystem). \
            filter(models.AutonomousSystem.id_topology == id_topology). \
            filter(models.AutonomousSystem.autonomous_system == autonomous_system2).first()
        if not as1_id or not as2_id:
            dictionary[
                'message'] = 'Confirm if Autonomous System Numbers informed really exists in this topology: ASN %s and %s' % \
                             (autonomous_system1, autonomous_system2)
            dictionary['css_class'] = 'errorMessage'
            return dictionary
        ip1 = ipaddress.ip_address(ip_autonomous_system1)
        ip2 = ipaddress.ip_address(ip_autonomous_system2)
        network1 = ipaddress.ip_network(str(ip_autonomous_system1) + '/' + str(mask), strict=False)
        network2 = ipaddress.ip_network(str(ip_autonomous_system2) + '/' + str(mask), strict=False)
        if (network1 != network2) or \
                (ip1 == ip2) or \
                (ip1 not in list(network2.hosts())) or \
                (ip2 not in list(network1.hosts())):
            dictionary['message'] = 'Error detected in IP address: %s/%s - %s/%s' % (
                ip1, mask, ip2, mask)
            dictionary['css_class'] = 'errorMessage'
            return dictionary
        entry = 'insert into link (id_topology, id_link_agreement, id_autonomous_system1, id_autonomous_system2, ' \
                'ip_autonomous_system1, ip_autonomous_system2, mask, description, bandwidth, delay, load) values ' \
                '(%s, %s, %s, %s, \'%s\', \'%s\', %s, %s, %s, %s, %s)' % (
                 id_topology, id_link_agreement,
                 as1_id.id, as2_id.id, str(ip_autonomous_system1), str(ip_autonomous_system2), mask,
                 '\'' + str(description) + '\'' if description else 'Null',
                 bandwidth if bandwidth else 'Null',
                 delay if delay else 'Null',
                 load if load else 'Null')
        request.dbsession.bind.execute(entry)
        stub(as1_id.id, as2_id.id)
        clearFields()
        dictionary['message'] = message
        dictionary['css_class'] = 'successMessage'

    def delete(id_link):
        link_autonomous_systems = request.dbsession.query(models.Link).filter_by(id=id_link).first()
        entry = 'delete from link where id = %s' % id_link
        request.dbsession.bind.execute(entry)
        stub(link_autonomous_systems.id_autonomous_system1, link_autonomous_systems.id_autonomous_system2)
        clearFields()
        dictionary['message'] = 'Link successfully removed'
        dictionary['css_class'] = 'successMessage'

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
        form.edit_autonomous_system1.data = dictionary['autonomous_system']

        fillSelectFields()

        if request.method == 'POST':

            if form.add_button.data:
                if form.autonomous_system1.validate(form.autonomous_system1.data) and \
                        form.ip_autonomous_system1.validate(form.ip_autonomous_system1.data) and \
                        form.autonomous_system2.validate(form.autonomous_system2.data) and \
                        form.ip_autonomous_system2.validate(form.ip_autonomous_system2.data) and \
                        form.mask.validate(form.mask.data) and \
                        form.description.validate(form.description.data) and \
                        form.bandwidth.validate(form.bandwidth.data) and \
                        form.delay.validate(form.delay.data) and \
                        form.load.validate(form.load.data) and \
                        form.agreement_list.validate(form.agreement_list.data):

                    insert(request.matchdict["id_topology"], form.agreement_list.data, form.autonomous_system1.data,
                           form.autonomous_system2.data, form.ip_autonomous_system1.data, form.ip_autonomous_system2.data,
                           form.mask.data, form.description.data, form.bandwidth.data, form.delay.data, form.load.data,
                           'Link successfully created')

            elif form.edit_button.data:
                if form.edit_autonomous_system1.validate(form.edit_autonomous_system1.data) and \
                        form.edit_ip_autonomous_system1.validate(form.edit_ip_autonomous_system1.data) and \
                        form.edit_autonomous_system2.validate(form.edit_autonomous_system2.data) and \
                        form.edit_ip_autonomous_system2.validate(form.edit_ip_autonomous_system2.data) and \
                        form.edit_mask.validate(form.edit_mask.data) and \
                        form.edit_description.validate(form.edit_description.data) and \
                        form.edit_bandwidth.validate(form.edit_bandwidth.data) and \
                        form.edit_delay.validate(form.edit_delay.data) and \
                        form.edit_load.validate(form.edit_load.data) and \
                        form.edit_agreement_list.validate(form.edit_agreement_list.data):

                    delete(form.link_list.data)

                    insert(request.matchdict["id_topology"], form.edit_agreement_list.data, form.edit_autonomous_system1.data,
                           form.edit_autonomous_system2.data, form.edit_ip_autonomous_system1.data, form.edit_ip_autonomous_system2.data,
                           form.edit_mask.data, form.edit_description.data, form.edit_bandwidth.data, form.edit_delay.data,
                           form.edit_load.data, 'Link successfully updated')

            elif form.delete_button.data:
                delete(form.link_list.data)

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='linkShowAllTxt', renderer='minisecbgp:templates/topology/linkShowAllTxt.jinja2')
def linkShowAllTxt(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        query = 'select l.id as id_link, ' \
                'la.agreement as agreement, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                'l.mask as mask, l.description as description, ' \
                'coalesce(cast(l.bandwidth as varchar), \'_\') as bandwidth, ' \
                'coalesce(cast(l.delay as varchar), \'_\') as delay, ' \
                'coalesce(cast(l.load as varchar), \'_\') as load ' \
                'from link l, link_agreement la ' \
                'where l.id_link_agreement = la.id ' \
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

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='linkShowAllHtml', renderer='minisecbgp:templates/topology/linkShowAllHtml.jinja2')
def linkShowAllHtml(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    try:
        dictionary['topology'] = request.dbsession.query(models.Topology) \
            .filter_by(id=request.matchdict["id_topology"]).first()

        query = 'select l.id as id_link, ' \
                'la.agreement as agreement, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system1) as autonomous_system1, ' \
                'l.ip_autonomous_system1 as ip_autonomous_system1, ' \
                '(select asys.autonomous_system from autonomous_system asys where asys.id = l.id_autonomous_system2) as autonomous_system2, ' \
                'l.ip_autonomous_system2 as ip_autonomous_system2, ' \
                'l.mask as mask, l.description as description, ' \
                'coalesce(cast(l.bandwidth as varchar), \'_\') as bandwidth, ' \
                'coalesce(cast(l.delay as varchar), \'_\') as delay, ' \
                'coalesce(cast(l.load as varchar), \'_\') as load ' \
                'from link l, link_agreement la ' \
                'where l.id_link_agreement = la.id ' \
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
