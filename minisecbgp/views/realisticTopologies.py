import re
import subprocess
import urllib

import requests

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy import func
from wtforms import Form, SelectField, StringField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class AgreementsDataForm(Form):
    agreement = StringField('Agreement identification: ',
                            validators=[InputRequired(),
                                        Length(min=1, max=50,
                                               message='Agreement identificator must be between 1 and 50 characters long.')])
    value = StringField('Value: ',
                        validators=[InputRequired(),
                                    Length(min=1, max=50,
                                           message='Agreement value must be between 1 and 50 characters long.')])


class ParametersDataForm(Form):
    url = StringField('URL: ',
                      validators=[InputRequired(),
                                  Length(min=1, max=100, message='URL must be between 1 and 100 characters long.')])
    file_search_string = StringField('String used for file search: ',
                                     validators=[InputRequired(),
                                                 Length(min=1, max=100,
                                                        message='String must be between 1 and 100 characters long.')])


class ScheduledDownload(Form):
    loop = SelectField('Repeat period: ',
                       choices=[('0', 'Execute only one time'),
                                ('1', 'update daily'),
                                ('7', 'update weekly'),
                                ('30', 'update monthly')])
    date = DateField('Date of the next scheduled download: ', format='%Y-%m-%d')


class TopologyDataForm(Form):
    topology_list = SelectField('Choose topology to download: ', coerce=int, validators=[InputRequired()])


@view_config(route_name='realisticTopologies', renderer='minisecbgp:templates/topology/realisticTopologiesShow.jinja2')
def realistic_topologies(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    dictionary['topologies'] = request.dbsession.query(models.Topology, models.TopologyType).\
        filter(models.Topology.id_topology_type == models.TopologyType.id).\
        filter(func.lower(models.TopologyType.topology_type) == 'caida as-relationship').all()
    downloading = request.dbsession.query(models.DownloadingTopology).first()
    if downloading.downloading == 1:
        dictionary['message'] = 'Warning: there is an update process running in the background. ' \
                  'Wait for it finish to see the new topology installed and access topology detail.'
        dictionary['css_class'] = 'warningMessage'

    dictionary['updating'] = downloading.downloading
    dictionary['realisticTopologies_url'] = request.route_url('realisticTopologies')
    dictionary['topologiesDetail_url'] = request.route_url('topologiesDetail', id_topology='')

    return dictionary


@view_config(route_name='realisticTopologiesAction', match_param='action=updateTopology',
             renderer='minisecbgp:templates/topology/realisticTopologiesUpdateTopology.jinja2')
def update_topology(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    try:
        downloadParameters = request.dbsession.query(models.RealisticTopologyDownloadParameter).first()
        site = requests.get(downloadParameters.url)
        databases = re.findall(r'\d{8}' + downloadParameters.file_search_string, site.text)
        databases = list(dict.fromkeys(databases))
        databases.sort(reverse=True)
        installed_databases = request.dbsession.query(models.Topology). \
            filter(models.Topology.id_topology_type == request.dbsession.query(models.TopologyType.id).
                   filter_by(topology_type='Realistic')).all()
        for database in installed_databases:
            if database.topology in databases:
                databases.remove(database.topology)

        form = TopologyDataForm(request.POST)
        form.topology_list.choices = [(i, database) for i, database in enumerate(databases)]

        downloading = request.dbsession.query(models.DownloadingTopology).first()
        if downloading.downloading == 1:
            dictionary['message'] = 'Warning: there is an update process running in the background. ' \
                      'Wait for it finish to access update topology again.'
            dictionary['css_class'] = 'warningMessage'
            dictionary['updating'] = downloading.downloading
            request.override_renderer = 'minisecbgp:templates/topology/realisticTopologiesUpdateTopology.jinja2'

        if request.method == 'POST' and form.validate():
            file = dict(form.topology_list.choices).get(form.topology_list.data)
            urllib.request.urlretrieve(downloadParameters.url + file + '.txt.bz2', '/tmp/' + file + '.txt.bz2')
            arguments = ['--config-file=minisecbgp.ini',
                         '--file=%s.txt.bz2' % file]
            subprocess.Popen(['./venv/bin/MiniSecBGP_realistic_topology'] + arguments)
            url = request.route_url('realisticTopologies')
            return HTTPFound(location=url)
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = 'Error: MiniSecBGP has no access to the CAIDA AS-Relationship project repository. ' \
                  'Check your internet connection and set download parameters correctly in "Configuration" -> "Parameters" menu if necessary.'
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='realisticTopologiesAction', match_param='action=agreements',
             renderer='minisecbgp:templates/topology/realisticTopologiesLinksAgreements.jinja2')
def agreements(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    dictionary['agreements'] = request.dbsession.query(models.LinkAgreement, models.RealisticTopologyLinkAgreement). \
        filter(models.LinkAgreement.id == models.RealisticTopologyLinkAgreement.id_link_agreement).all()

    return dictionary


@view_config(route_name='realisticTopologiesAction', match_param='action=parameters',
             renderer='minisecbgp:templates/topology/realisticTopologiesParameters.jinja2')
def parameters(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    try:
        parametersDownload = request.dbsession.query(models.RealisticTopologyDownloadParameter).first()
        if request.method == 'GET':
            form = ParametersDataForm(request.POST, obj=parametersDownload)
        else:
            form = ParametersDataForm(request.POST)
            if form.validate():
                parametersDownload.url = form.url.data
                parametersDownload.file_search_string = form.file_search_string.data
                dictionary['message'] = 'Parameters successfully updated.'
                dictionary['css_class'] = 'successMessage'
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='realisticTopologiesAction', match_param='action=schedule',
             renderer='minisecbgp:templates/topology/realisticTopologiesScheduler.jinja2')
def schedule(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    try:
        scheduledDownload = request.dbsession.query(models.RealisticTopologyScheduleDownload).first()
        if request.method == 'GET':
            form = ScheduledDownload(request.POST, obj=scheduledDownload)
        elif request.method == 'POST':
            form = ScheduledDownload(request.POST)
            if form.validate():
                scheduledDownload.loop = form.loop.data
                scheduledDownload.date = form.date.data
                dictionary['message'] = 'Topology download scheduled successfully.'
                dictionary['css_class'] = 'successMessage'
        dictionary['form'] = form

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary
