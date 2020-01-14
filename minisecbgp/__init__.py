from pyramid.config import Configurator


def main(global_config, **settings):

	with Configurator(settings=settings) as config:
		config.include('pyramid_jinja2')
		config.include('.models')
		config.include('.routes')
		config.include('.security')
		config.scan('.views')
	return config.make_wsgi_app()
