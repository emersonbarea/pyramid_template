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
    config.add_route('autonomousSystem', '/topology/autonomousSystem/{id_topology}')
    config.add_route('autonomousSystemShowAll', '/topology/autonomousSystemShowAll/{id_topology}')
    config.add_route('region', '/topology/region/{id_topology}')
    config.add_route('regionShowAll', '/topology/regionShowAll/{id_topology}')
    config.add_route('typeOfService', '/topology/typeOfService/{id_topology}')
    config.add_route('typeOfServiceShowAll', '/topology/typeOfServiceShowAll/{id_topology}')
    config.add_route('typeOfUser', '/topology/typeOfUser/{id_topology}')
    config.add_route('typeOfUserShowAll', '/topology/typeOfUserShowAll/{id_topology}')
    config.add_route('prefix', '/topology/prefix/{id_topology}')
    config.add_route('prefixShowAll', '/topology/autonomousSystem/prefixShowAll/{id_topology}')
    config.add_route('prefixAction', '/topology/autonomousSystem/prefix/{action}/{id_topology}')
    config.add_route('link', '/topology/link/{id_topology}')
    config.add_route('linkShowAll', '/topology/autonomousSystem/linkShowAll/{id_topology}')
    config.add_route('linkAction', '/topology/autonomousSystem/link/{action}/{id_topology}')
    config.add_route('internetExchange', '/topology/internetExchange/{id_topology}')
    config.add_route('internetExchangeShowAll', '/topology/internetExchangeShowAll/{id_topology}')
    config.add_route('topologiesAgreement', '/topology/agreement')
    config.add_route('topologiesDetail', '/topology/detail/{id_topology}')
    config.add_route('topologiesAction', '/topology/{action}/{id_topology}')
    config.add_route('realisticTopologies', '/realisticTopologies')
    config.add_route('realisticTopologiesAction', '/realisticTopologies/{action}')
    config.add_route('manualTopologies', '/manualTopologies')
    config.add_route('manualTopologiesAction', '/manualTopologies/{action}')

