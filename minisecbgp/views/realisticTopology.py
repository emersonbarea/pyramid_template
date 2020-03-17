import re
import subprocess
import urllib

import requests

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPForbidden
from sqlalchemy import select
from wtforms import Form, SelectField, StringField
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length

from minisecbgp import models


class ParametersDataForm(Form):
    url = StringField('URL',
                      validators=[InputRequired(),
                                  Length(min=1, max=100, message='URL must be between 1 and 100 characters long.')])
    string_file_search = StringField('String used for file search',
                                     validators=[InputRequired(),
                                                 Length(min=1, max=100,
                                                        message='String must be between 1 and 100 characters long.')])
    c2p = StringField('Customer to Provider link parameter',
                      validators=[InputRequired(),
                                  Length(min=1, max=50, message='Customer to Provider link identification parameter '
                                                                'must be between 1 and 50 characters long.')])
    p2p = StringField('Customer to Provider link parameter',
                      validators=[InputRequired(),
                                  Length(min=1, max=50, message='Peer to Peer link identification parameter must be '
                                                                'between 1 and 50 characters long.')])


class ScheduledDownload(Form):
    loop = SelectField('Repeat period',
                       choices=[('0', 'Execute only one time'),
                                ('1', 'update daily'),
                                ('7', 'update weekly'),
                                ('30', 'update monthly')])
    date = DateField('Date of the next scheduled download', format='%Y-%m-%d')


class TopologyDataForm(Form):
    topology_list = SelectField('Choose topology to download', coerce=int, validators=[InputRequired()])


@view_config(route_name='realisticTopology', renderer='minisecbgp:templates/topology/showRealisticTopology.jinja2')
def realisticTopology(request):
    user = request.user
    if user is None:
        raise HTTPForbidden

    dictionary = dict()
    topologies = request.dbsession.query(models.Topology).filter(models.Topology.type == 0).all()
    updating = request.dbsession.query(models.TempCaidaDatabases).first()
    if updating.updating == 1:
        message = 'Warning: there is an update process running in the background. Wait for it finish to see the new topology installed.'
        css_class = 'warningMessage'
        dictionary['message'] = message
        dictionary['css_class'] = css_class

    dictionary['topologies'] = topologies
    dictionary['realisticTopology_url'] = request.route_url('realisticTopology')
    dictionary['realisticTopologyDetail_url'] = request.route_url('realisticTopologyDetail', id_topology='')

    return dictionary


@view_config(route_name='realisticTopologyAction', match_param='action=manualUpdate',
             renderer='minisecbgp:templates/topology/manualUpdate.jinja2')
def manualUpdate(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        parametersDownload = request.dbsession.query(models.ParametersDownload).first()
        site = requests.get(parametersDownload.url)
        databases = re.findall(r'\d{8}' + parametersDownload.string_file_search, site.text)
        databases = list(dict.fromkeys(databases))
        databases.sort(reverse=True)
        installed_databases = request.dbsession.query(models.Topology).filter_by(type=0).all()
        for database in installed_databases:
            databases.remove(database.topology)
        form = TopologyDataForm(request.POST)
        form.topology_list.choices = [(i, database) for i, database in enumerate(databases)]

        dictionary = dict()

        updating = request.dbsession.query(models.TempCaidaDatabases).first()
        if updating.updating == 1:
            message = 'Warning: there is an update process running in the background. Wait for it finish to access Manual Update again.'
            css_class = 'warningMessage'
            dictionary['message'] = message
            dictionary['css_class'] = css_class
            dictionary['updating'] = updating.updating
            request.override_renderer = 'minisecbgp:templates/topology/manualUpdate.jinja2'

        if request.method == 'POST' and form.validate():
            updating.updating = 1
            file = dict(form.topology_list.choices).get(form.topology_list.data)
            urllib.request.urlretrieve(parametersDownload.url + file + '.txt.bz2',
                                       './CAIDA_AS_Relationship/' + file + '.txt.bz2')
            arguments = ['--config_file=minisecbgp.ini',
                         '--path=./CAIDA_AS_Relationship/',
                         '--file=%s.txt' % file,
                         '--zip_file=%s.txt.bz2' % file]
            subprocess.Popen(['initialize_CAIDA_AS_Relationship'] + arguments)
            url = request.route_url('realisticTopology')
            return HTTPFound(location=url)

        dictionary['form'] = form

        return dictionary

    except Exception as error:
        message = 'Error: MiniSecBGP has no access to the CAIDA AS-Relationship project repository. ' \
                  'Check your internet connection and set download parameters correctly in "Configuration" -> "Parameters" menu if necessary.'
        css_class = 'errorMessage'
        return {'message': message, 'css_class': css_class}


@view_config(route_name='realisticTopologyAction', match_param='action=parameters',
             renderer='minisecbgp:templates/topology/parameters.jinja2')
def parameters(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        parametersDownload = request.dbsession.query(models.ParametersDownload).first()
        dictionary = dict()
        if request.method == 'GET':
            form = ParametersDataForm(request.POST, obj=parametersDownload)
        else:
            form = ParametersDataForm(request.POST)
            if form.validate():
                parametersDownload.url = form.url.data
                parametersDownload.string_file_search = form.string_file_search.data
                parametersDownload.c2p = form.c2p.data
                parametersDownload.p2p = form.p2p.data
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


@view_config(route_name='realisticTopologyAction', match_param='action=schedule',
             renderer='minisecbgp:templates/topology/schedule.jinja2')
def schedule(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        scheduledDownload = request.dbsession.query(models.ScheduledDownload).first()
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


@view_config(route_name='realisticTopologyDetail',
             renderer='minisecbgp:templates/topology/realisticTopologyDetail.jinja2')
def realisticTopologyDetail(request):
    topology = request.dbsession.query(models.Topology) \
        .filter_by(id=request.matchdict["id_topology"]).first()

    # Full Topology

    as_count = request.dbsession.query(
        select([models.RealisticTopology.as1]).where(
            models.RealisticTopology.id_topology == request.matchdict["id_topology"])
            .union_all(
            select([models.RealisticTopology.as2]).where(
                models.RealisticTopology.id_topology == request.matchdict["id_topology"]))
            .alias('as_union_all')
    ).distinct().count()

    p2c = request.dbsession.query(models.RealisticTopology) \
        .filter_by(id_topology=request.matchdict["id_topology"],
                   agreement=request.dbsession.query(models.ParametersDownload.c2p).first()).count()
    p2p = request.dbsession.query(models.RealisticTopology) \
        .filter_by(id_topology=request.matchdict["id_topology"],
                   agreement=request.dbsession.query(models.ParametersDownload.p2p).first()).count()

    # Non Stub Topology

    # as_stub_count = request.dbsession.execute('select count(xpto) from (select z from (select as1 from realistic_topology where id_topology = 2 union all select as2 from realistic_topology where id_topology = 2) as z group by z having count(*) = 1) as xpto').fetchall()
    # as_stub_count = request.dbsession.query(as_union_all).distinct().count()

    # bla = request.dbsession.query(as_union_all, func.count(as_union_all)).group_by(as_union_all).all()
    # bla = request.dbsession.query(models.RealisticTopology.as1).group_by(models.RealisticTopology.as1).having(func.count(models.RealisticTopology.as1) == 1).count()
    # print(bla)




    #query = 'select count(non_stub_as) from (' \
    #        'select union_all_as from (' \
    #        'select as1 from realistic_topology where id_topology = %s ' \
    #        'union all ' \
    #        'select as2 from realistic_topology where id_topology = %s' \
    #        ') as union_all_as ' \
    #        'group by union_all_as having count(*) = 1' \
    #        ') as non_stub_as' % (2, 2)
    #as_stub_count = request.dbsession.execute(query).first()
    #print('stub ASs: ', as_stub_count)

    return {'topology': topology, 'as_count': as_count, 'p2c': p2c, 'p2p': p2p}


@view_config(route_name='realisticTopologyAction', match_param='action=delete',
             renderer='minisecbgp:templates/topology/showRealisticTopology.jinja2')
def delete(request):
    user = request.user
    if user is None or (user.role != 'admin'):
        raise HTTPForbidden

    try:
        dictionary = dict()
        if request.method == 'POST':
            id_topology = request.params['id_topology']
            topology = request.params['topology']

            request.dbsession.query(models.RealisticTopology).filter(
                models.RealisticTopology.id_topology == id_topology).delete()
            request.dbsession.query(models.Topology).filter(
                models.Topology.id == id_topology).delete()

            topologies = request.dbsession.query(models.Topology).filter(models.Topology.type == 0).all()
            dictionary['topologies'] = topologies

            message = ('Topology "%s" successfully deleted.' % topology)
            css_class = 'successMessage'
            dictionary['message'] = message
            dictionary['css_class'] = css_class
    except Exception as error:
        message = ('Topology "%s" does not exist.' % topology)
        css_class = 'errorMessage'
        dictionary['message'] = message
        dictionary['css_class'] = css_class

    return dictionary
