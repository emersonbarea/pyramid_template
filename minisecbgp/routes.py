def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('dashboard', '/dashboard')
    config.add_route('user', '/user')
    config.add_route('userAction', '/user/{action}')
    config.add_route('cluster', '/cluster')
    config.add_route('clusterAction', '/cluster/{action}')
    config.add_route('clusterDetail', '/cluster/detail/{id}')
    config.add_route('topologies', '/topologies')
    config.add_route('topologiesDetail', '/topology/detail/{id_topology}')
    config.add_route('topologiesAction', '/topology/{action}/{id_topology}')
    config.add_route('realisticTopologies', '/realisticTopologies')
    config.add_route('realisticTopologiesAction', '/realisticTopologies/{action}')
