import datetime
import os
import re
import shutil
import subprocess

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from sqlalchemy import func
from wtforms import Form, SelectField
from wtforms.validators import InputRequired

from minisecbgp import models


class TopologyDataForm(Form):
    topology_list = SelectField('Choose topology to download: ', coerce=int, validators=[InputRequired()])


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


@view_config(route_name='bgplayTopologiesAction', match_param='action=upload',
             renderer='minisecbgp:templates/topology/bgplayTopologiesUpload.jinja2')
def upload(request):
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
            result = subprocess.Popen(['./venv/bin/MiniSecBGP_bgplay_topology'] + arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
