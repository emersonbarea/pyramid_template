import os
import re
import shutil
import subprocess
import datetime
import urllib

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from sqlalchemy import func
from wtforms import Form, StringField
from wtforms.fields.html5 import DateTimeField
from wtforms.validators import InputRequired, ValidationError

from minisecbgp import models


class BGPlayDataForm(Form):
    scenario_name = StringField('Scenario name (will be used to name the <strong>topology</strong>)', validators=[InputRequired()])
    query_start_time = DateTimeField('Start time period: ', format='%Y-%m-%d %H:%M:%S', validators=[InputRequired()])
    query_end_time = DateTimeField('End time period: ', format='%Y-%m-%d %H:%M:%S', validators=[InputRequired()])
    resource = StringField('Resource value: (Format: [0..n]<strong>Prefix,</strong>[0..n]<strong>IP,</strong>[0..n]<strong>ASN</strong>)', validators=[InputRequired()])


@view_config(route_name='bgplayTopologies', renderer='minisecbgp:templates/topology/bgplayTopologiesShow.jinja2')
def bgplay_topologies(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    dictionary['topologies'] = request.dbsession.query(models.Topology, models.TopologyType).\
        filter(models.Topology.id_topology_type == models.TopologyType.id).\
        filter(func.lower(models.TopologyType.topology_type) == 'ripe ncc bgplay').all()
    downloading = request.dbsession.query(models.DownloadingTopology).first()
    if downloading.downloading == 1:
        dictionary['message'] = 'Warning: there is an update process running in the background. ' \
                  'Wait for it finish to see the new topology installed and access topology detail.'
        dictionary['css_class'] = 'warningMessage'

    dictionary['updating'] = downloading.downloading
    dictionary['bgplayTopologies_url'] = request.route_url('bgplayTopologies')
    dictionary['topologiesDetail_url'] = request.route_url('topologiesDetail', id_topology='')

    return dictionary


@view_config(route_name='bgplayTopologiesAction', match_param='action=upload_from_file',
             renderer='minisecbgp:templates/topology/bgplayTopologiesUploadFromFile.jinja2')
def upload_from_file(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    dictionary = dict()
    try:
        downloading = request.dbsession.query(models.DownloadingTopology).first()
        if downloading.downloading == 1:
            dictionary['message'] = 'Warning: there is an update process running in the background. ' \
                                    'Wait for it finish to see the new topology installed and access topology detail.'
            dictionary['css_class'] = 'warningMessage'

        dictionary['updating'] = downloading.downloading

        if request.method == 'POST':
            filename = request.POST['topology_file'].filename
            if not filename.endswith('.BGPlay'):
                dictionary['message'] = 'File %s has a invalid file extension name. ' \
                                        'Please verify and upload again.' % filename
                dictionary['css_class'] = 'errorMessage'
                return dictionary

            input_file = request.POST['topology_file'].file
            file_path = os.path.join('/tmp', '%s-%s' % (re.sub(r"[' ':.-]", "", str(datetime.datetime.now())), filename))
            temp_file_path = file_path + '~'
            input_file.seek(0)
            with open(temp_file_path, 'wb') as output_file:
                shutil.copyfileobj(input_file, output_file)
            os.rename(temp_file_path, file_path)

            arguments = ['--config-file=minisecbgp.ini',
                         '--file=%s' % file_path]
            result = subprocess.Popen(['./venv/bin/MiniSecBGP_bgplay_topology'] +
                                      arguments, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
            command_result, command_result_error = result.communicate()
            if command_result:
                dictionary['message'] = command_result
                dictionary['css_class'] = 'errorMessage'
                return dictionary
            url = request.route_url('bgplayTopologies')
            return HTTPFound(location=url)

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    return dictionary


@view_config(route_name='bgplayTopologiesAction', match_param='action=upload_from_site',
             renderer='minisecbgp:templates/topology/bgplayTopologiesUploadFromSite.jinja2')
def upload_from_site(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    form = BGPlayDataForm(request.POST)
    dictionary = dict()
    try:
        downloading = request.dbsession.query(models.DownloadingTopology).first()
        if downloading.downloading == 1:
            dictionary['message'] = 'Warning: there is an update process running in the background. ' \
                                    'Wait for it finish to see the new topology installed and access topology detail.'
            dictionary['css_class'] = 'warningMessage'

        dictionary['updating'] = downloading.downloading

        if request.method == 'POST':
            try:
                if not form.query_start_time.data or \
                        not form.query_start_time.data or \
                        not datetime.datetime.strptime(str(form.query_start_time.data), '%Y-%m-%d %H:%M:%S') or \
                        not datetime.datetime.strptime(str(form.query_start_time.data), '%Y-%m-%d %H:%M:%S'):
                    raise ValidationError("Dates must be in %Y-%m-%d %H:%M:%S format. Ex.: 2008-12-05 21:00:01")
                elif form.query_start_time.data >= form.query_end_time.data:
                    raise ValidationError("End date must not be earlier than start date.")

                bgplay_url = 'https://stat.ripe.net/data/bgplay/data.json?resource=%s&starttime=%s&endtime=%s' % \
                             (form.resource.data, form.query_start_time.data, form.query_end_time.data)

                file_path = '/tmp/' + str(re.sub(r"[' ':.-]", "", str(datetime.datetime.now()))) + '-' + \
                            str(form.scenario_name.data.replace(' ', '_').replace('.', '_')) + '.BGPlay'

                urllib.request.urlretrieve(bgplay_url.replace(' ', 'T'), file_path)

                arguments = ['--config-file=minisecbgp.ini',
                             '--file=%s' % file_path]
                result = subprocess.Popen(['./venv/bin/MiniSecBGP_bgplay_topology'] +
                                          arguments, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)

                command_result, command_result_error = result.communicate()
                if command_result:
                    dictionary['message'] = command_result
                    dictionary['css_class'] = 'errorMessage'
                    #return dictionary
                url = request.route_url('bgplayTopologies')
                return HTTPFound(location=url)

            except Exception as error:
                dictionary['message'] = error
                dictionary['css_class'] = 'errorMessage'

    except Exception as error:
        dictionary['message'] = error
        dictionary['css_class'] = 'errorMessage'

    dictionary['form'] = form

    return dictionary
