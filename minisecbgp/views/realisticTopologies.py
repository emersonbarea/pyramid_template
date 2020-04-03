import os
import re
import subprocess
import urllib

import requests

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from wtforms import Form, SelectField, StringField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class AgreementsDataForm(Form):
    agreement = StringField('Agreement identification',
                            validators=[InputRequired(),
                                        Length(min=1, max=50,
                                               message='Agreement identificator must be between 1 and 50 characters long.')])
    value = StringField('Value',
                        validators=[InputRequired(),
                                    Length(min=1, max=50,
                                           message='Agreement value must be between 1 and 50 characters long.')])


class ParametersDataForm(Form):
    url = StringField('URL',
                      validators=[InputRequired(),
                                  Length(min=1, max=100, message='URL must be between 1 and 100 characters long.')])
    file_search_string = StringField('String used for file search',
                                     validators=[InputRequired(),
                                                 Length(min=1, max=100,
                                                        message='String must be between 1 and 100 characters long.')])


class ScheduledDownload(Form):
    loop = SelectField('Repeat period',
                       choices=[('0', 'Execute only one time'),
                                ('1', 'update daily'),
                                ('7', 'update weekly'),
                                ('30', 'update monthly')])
    date = DateField('Date of the next scheduled download', format='%Y-%m-%d')


class TopologyDataForm(Form):
    topology_list = SelectField('Choose topology to download', coerce=int, validators=[InputRequired()])


@view_config(route_name='realisticTopologies', renderer='minisecbgp:templates/topology/realisticTopologiesShow.jinja2')
def realisticTopologies(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    all_topologies = request.dbsession.query(models.Topology). \
        filter(models.Topology.id_topology_type == request.dbsession.query(models.TopologyType.id).
               filter_by(topology_type='Realistic')). \
        all()
    downloading = request.dbsession.query(models.RealisticTopologyDownloadingCaidaDatabase).first()
    if downloading.downloading == 1:
        message = 'Warning: there is an update process running in the background. ' \
                  'Wait for it finish to see the new topology installed and access topology detail.'
        css_class = 'warningMessage'
        dictionary['message'] = message
        dictionary['css_class'] = css_class

    dictionary['updating'] = downloading.downloading
    dictionary['topologies'] = all_topologies
    dictionary['realisticTopologies_url'] = request.route_url('realisticTopologies')
    dictionary['topologiesDetail_url'] = request.route_url('topologiesDetail', id_topology='')

    return dictionary


@view_config(route_name='realisticTopologiesAction', match_param='action=manualUpdate',
             renderer='minisecbgp:templates/topology/realisticTopologiesManualUpdate.jinja2')
def manualUpdate(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        downloadParameters = request.dbsession.query(models.RealisticTopologyDownloadParameters).first()
        site = requests.get(downloadParameters.url)
        databases = re.findall(r'\d{8}' + downloadParameters.file_search_string, site.text)
        databases = list(dict.fromkeys(databases))
        databases.sort(reverse=True)
        installed_databases = request.dbsession.query(models.Topology). \
            filter(models.Topology.id_topology_type == request.dbsession.query(models.TopologyType.id).
                   filter_by(topology_type='Realistic')). \
            all()
        for database in installed_databases:
            if database.topology in databases:
                databases.remove(database.topology)

        form = TopologyDataForm(request.POST)
        form.topology_list.choices = [(i, database) for i, database in enumerate(databases)]

        dictionary = dict()

        downloading = request.dbsession.query(models.RealisticTopologyDownloadingCaidaDatabase).first()
        if downloading.downloading == 1:
            message = 'Warning: there is an update process running in the background. ' \
                      'Wait for it finish to access Manual Update again.'
            css_class = 'warningMessage'
            dictionary['message'] = message
            dictionary['css_class'] = css_class
            dictionary['updating'] = downloading.downloading
            request.override_renderer = 'minisecbgp:templates/topology/realisticTopologiesManualUpdate.jinja2'

        if request.method == 'POST' and form.validate():
            file = dict(form.topology_list.choices).get(form.topology_list.data)
            urllib.request.urlretrieve(downloadParameters.url + file + '.txt.bz2', '/tmp/' + file + '.txt.bz2')
            arguments = ['--config-file=minisecbgp.ini',
                         '--topology-type=realistic',
                         '--file=%s.txt.bz2' % file]
            subprocess.Popen(['./venv/bin/topology'] + arguments)
            url = request.route_url('realisticTopologies')

            return HTTPFound(location=url)

        dictionary['form'] = form
        return dictionary
    except Exception as error:
        message = 'Error: MiniSecBGP has no access to the CAIDA AS-Relationship project repository. ' \
                  'Check your internet connection and set download parameters correctly in "Configuration" -> "Parameters" menu if necessary.'
        css_class = 'errorMessage'
        return {'message': message, 'css_class': css_class}


@view_config(route_name='realisticTopologiesAction', match_param='action=agreements',
             renderer='minisecbgp:templates/topology/realisticTopologiesAgreements.jinja2')
def agreements(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        dictionary = dict()
        form = AgreementsDataForm(request.POST)
        if request.method == 'POST':
            agreement = models.RealisticTopologyAgreements(agreement=form.agreement.data,
                                                           value=form.value.data)
            request.dbsession.add(agreement)
            request.dbsession.flush()

            form = AgreementsDataForm()
            message = ('CAIDA AS-Relationship AS\'s agreement "%s" successfully registered.' % form.agreement.data)
            css_class = 'successMessage'

            dictionary['message'] = message
            dictionary['css_class'] = css_class

        agreementsBetweenASs = request.dbsession.query(models.RealisticTopologyAgreements).all()

        dictionary['agreements'] = agreementsBetweenASs
        dictionary['form'] = form

        return dictionary

    except Exception as error:
        dictionary['form'] = form
        message = 'Error in agreements configuration.'
        css_class = 'errorMessage'
        dictionary['message'] = message
        dictionary['css_class'] = css_class

        return dictionary


@view_config(route_name='realisticTopologiesAction', match_param='action=parameters',
             renderer='minisecbgp:templates/topology/realisticTopologiesParameters.jinja2')
def parameters(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        parametersDownload = request.dbsession.query(models.RealisticTopologyDownloadParameters).first()
        dictionary = dict()
        if request.method == 'GET':
            form = ParametersDataForm(request.POST, obj=parametersDownload)
        else:
            form = ParametersDataForm(request.POST)
            if form.validate():
                parametersDownload.url = form.url.data
                parametersDownload.file_search_string = form.file_search_string.data
                message = 'Parameters successfully updated.'
                css_class = 'successMessage'
                dictionary['message'] = message
                dictionary['css_class'] = css_class

        dictionary['form'] = form

        return dictionary

    except Exception as error:
        message = 'Error in download parameters update.'
        css_class = 'errorMessage'
        dictionary['message'] = message
        dictionary['css_class'] = css_class

        return dictionary


@view_config(route_name='realisticTopologiesAction', match_param='action=schedule',
             renderer='minisecbgp:templates/topology/realisticTopologiesScheduler.jinja2')
def schedule(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        scheduledDownload = request.dbsession.query(models.RealisticTopologyScheduleDownloads).first()
        dictionary = dict()
        if request.method == 'GET':
            form = ScheduledDownload(request.POST, obj=scheduledDownload)
        elif request.method == 'POST':
            form = ScheduledDownload(request.POST)
            if form.validate():
                scheduledDownload.loop = form.loop.data
                scheduledDownload.date = form.date.data
                message = 'Topology download scheduled successfully.'
                css_class = 'successMessage'
                dictionary['message'] = message
                dictionary['css_class'] = css_class

        dictionary['form'] = form

        return dictionary

    except Exception as error:
        message = 'Error in topology download schedule configuration.'
        css_class = 'errorMessage'
        dictionary['message'] = message
        dictionary['css_class'] = css_class

        return dictionary
