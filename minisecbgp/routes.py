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
    config.add_route('autonomousSystemAddEdit', '/topology/autonomousSystemAddEdit/{id_topology}')
    config.add_route('autonomousSystemShowAllTxt', '/topology/autonomousSystemShowAllTxt/{id_topology}')
    config.add_route('autonomousSystemShowAllHtml', '/topology/autonomousSystemShowAllHtml/{id_topology}')
    config.add_route('region', '/topology/region/{id_topology}')
    config.add_route('regionShowAllTxt', '/topology/regionShowAllTxt/{id_topology}')
    config.add_route('regionShowAllHtml', '/topology/regionShowAllHtml/{id_topology}')
    config.add_route('typeOfService', '/topology/typeOfService/{id_topology}')
    config.add_route('typeOfServiceShowAllTxt', '/topology/typeOfServiceShowAllTxt/{id_topology}')
    config.add_route('typeOfServiceShowAllHtml', '/topology/typeOfServiceShowAllHtml/{id_topology}')
    config.add_route('typeOfUser', '/topology/typeOfUser/{id_topology}')
    config.add_route('typeOfUserShowAllTxt', '/topology/typeOfUserShowAllTxt/{id_topology}')
    config.add_route('typeOfUserShowAllHtml', '/topology/typeOfUserShowAllHtml/{id_topology}')
    config.add_route('prefix', '/topology/prefix/{id_topology}')
    config.add_route('prefixShowAllTxt', '/topology/autonomousSystem/prefixShowAllTxt/{id_topology}')
    config.add_route('prefixShowAllHtml', '/topology/autonomousSystem/prefixShowAllHtml/{id_topology}')
    config.add_route('prefixAction', '/topology/autonomousSystem/prefix/{action}/{id_topology}')
    config.add_route('link', '/topology/link/{id_topology}')
    config.add_route('linkShowAllTxt', '/topology/autonomousSystem/linkShowAllTxt/{id_topology}')
    config.add_route('linkShowAllHtml', '/topology/autonomousSystem/linkShowAllHtml/{id_topology}')
    config.add_route('linkAction', '/topology/autonomousSystem/link/{action}/{id_topology}')
    config.add_route('internetExchange', '/topology/internetExchange/{id_topology}')
    config.add_route('internetExchangeShowAllTxt', '/topology/internetExchangeShowAllTxt/{id_topology}')
    config.add_route('internetExchangeShowAllHtml', '/topology/internetExchangeShowAllHtml/{id_topology}')
    config.add_route('topologiesAgreement', '/topology/agreement')
    config.add_route('topologiesDetail', '/topology/detail/{id_topology}')
    config.add_route('topologiesAction', '/topology/{action}/{id_topology}')
    config.add_route('realisticTopologies', '/realisticTopologies')
    config.add_route('realisticTopologiesAction', '/realisticTopologies/{action}')
    config.add_route('manualTopologies', '/manualTopologies')
    config.add_route('manualTopologiesAction', '/manualTopologies/{action}')
    config.add_route('hijack', '/hijack')
    config.add_route('hijackAttackScenario', '/hijackAttackScenario')
    config.add_route('hijackAttackScenarioDetail', '/hijackAttackScenarioDetail')
    config.add_route('hijackRealisticAnalysis', '/hijackRealisticAnalysis')
    config.add_route('hijackRealisticAnalysisDetail', '/hijackRealisticAnalysisDetail')
    config.add_route('hijackAttackType', '/hijack/hijackAttackType')
