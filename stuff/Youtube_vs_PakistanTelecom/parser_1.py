import sys
import json
import ipaddress
from datetime import datetime
from datetime import timezone


class BGPlay(object):
    def __init__(self, argv):
        self.file_from = argv

    def autonomous_systems(self):
        data_autonomous_systems = {}
        data_autonomous_systems['autonomous_systems'] = []

        # read BGPlay json file and parse it
        with open(self.file_from) as file:
            data_from = json.load(file)

        origin_autonomous_system = []
        events = data_from['data']['events']
        for event in events:
            if event['type'] == 'A':
                origin_autonomous_system.append(event['attrs']['path'][-1])
        origin_autonomous_system = set(origin_autonomous_system)

        sources = data_from['data']['sources']
            
        lista_final = list()
        for source1 in sources:
            lista_temp = list()
            for source2 in sources:
                if source1['as_number'] == source2['as_number']:
                    lista_temp.append(source2['ip'])
            lista_final.append(str(source1['as_number']) + ' - ' + str(lista_temp))


        for item in lista_final:
            print(item)

def main(argv=sys.argv[1]):    
    bgplay = BGPlay(argv)
    autonomous_systems = bgplay.autonomous_systems()


if __name__ == '__main__':
    main()