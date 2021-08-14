#!/usr/bin/python3

import sys
import json
import ipaddress

import pandas as pd


class Parser(object):
    def __init__(self, argv0):

        self.file_from = argv0
        self.resources = list()

        # read json file and parse it
        try:
            with open(self.file_from) as file:
                self.data = json.load(file)
        except Exception as error:
            print(error)
        finally:
            file.close()

    def create_withdrawn_event_commands(self):
        def validIPv4(ip_address):
            try:
                return True if type(ipaddress.ip_network(ip_address)) is ipaddress.IPv4Network else False
            except ValueError:
                return False

        resources = self.data['data']['resource']

        for resource in resources:
            if validIPv4(resource):
                self.resources.append(resource)

        # para cada "source"
        #   bloqueia o anúncio dos prefixos


        # create releases route-maps


def main(argv=sys.argv[1:]):
    try:
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)

        parser = Parser(argv[0])
        parser.create_withdrawn_event_commands()

    except Exception as error:
        print(error)
        print('Usage: ./create_withdrawn_event_commands.py <ripe_json_file.MiniSecBGP>')


if __name__ == '__main__':
    main()
