import sys
import json
import ipaddress
from datetime import datetime
from datetime import timezone
import time
import pandas as pd


class BGPlay(object):
    def __init__(self, argv):
        self.file_from = argv

    def get_events(self):

        with open(self.file_from) as json_file:
            data = json.load(json_file)
        json_file.close()

        try:

            events = data['data']['events']

            # Prepend
            prepend_events_list_temp = list()
            prepend_events_list = list()

            for observed_event in events:
                if observed_event['type'] == 'A':
                    path = observed_event['attrs']['path']
                    previous_hop = ''
                    for elem in path:
                        if path.count(elem) > 1:

                            # get the AS prepender
                            peer_path = ['']
                            for hop in path:
                                if not previous_hop:
                                    previous_hop = hop
                                else:
                                    if hop == elem:
                                        prepender = previous_hop
                                        break
                                    else:
                                        previous_hop = hop
                                peer_path.append(hop)

                            prepend_events_list_temp.append({
                                'event_datetime': str(observed_event['timestamp']).replace('T', ' '),
                                'in_out': 'in',
                                'prepender': str(prepender),
                                'prepended': str(elem),
                                'peer': str(peer_path[-2]), 
                                'hmt': str(path.count(elem))
                            })

#            prepend_events_list = prepend_events_list_temp

            if prepend_events_list_temp:
                for prepend_event_temp in prepend_events_list_temp:
                    if not prepend_events_list:
                        prepend_events_list.append(prepend_event_temp)
                    else:
                        for i, prepend_event in enumerate(prepend_events_list):
                            if (str(prepend_event['prepender']) == str(prepend_event_temp['prepender'])) and \
                                    (str(prepend_event['prepended'])) == str(prepend_event_temp['prepended']) and \
                                    (str(prepend_event['peer'])) == str(prepend_event_temp['peer']) and \
                                    (str(prepend_event['hmt']) == str(prepend_event_temp['hmt'])):
                                break
                            if i == len(prepend_events_list) - 1:
                                prepend_events_list.append(prepend_event_temp)

            for i in prepend_events_list:
                print(i)

        except Exception as error:
            print(error)


def main(argv=sys.argv[1]):    
    bgplay = BGPlay(argv)
    bgplay.get_events()


if __name__ == '__main__':
    main()



