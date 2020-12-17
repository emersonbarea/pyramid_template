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

            # Announcement
            
            print('\nAnnouncement')

            events = data['data']['events']
            announcement_events_list = list()
            
            for observed_event in events:
                if observed_event['type'] == 'A':
                    observed_event_source = observed_event['attrs']['path'][-1]
                    observed_event_prefix = observed_event['attrs']['target_prefix']
                    if announcement_events_list:
                        for i, event in enumerate(announcement_events_list):
                            if [observed_event_prefix, observed_event_source] == [list(event[1].values())[0], list(event[2].values())[0]]:
                                break
                            if i == len(announcement_events_list) - 1:
                                announcement_events_list.append([
                                    {'event_datetime': observed_event['timestamp']},
                                    {'announced_prefix': observed_event_prefix},
                                    {'announcer': observed_event_source}
                                    ])
                    else:
                        announcement_events_list.append([
                            {'event_datetime': observed_event['timestamp']},
                            {'announced_prefix': observed_event_prefix},
                            {'announcer': observed_event_source}
                            ])
            
            for item in announcement_events_list:
                pass #print(item)


           
            # Withdrawn

            print('\nWithdrawn')

            events = data['data']['events']
            sources = data['data']['sources']
            withdrawn_events_list_temp = list()
            withdrawn_events_list = list()
            
            for observed_event in events:
                if observed_event['type'] == 'W':
                    for source in sources:
                        if str(source['id']) == str(observed_event['attrs']['source_id']):
                            withdrawer = source['as_number']

                    withdrawn_events_list_temp.append({
                        'event_datetime': observed_event['timestamp'], 
                        'withdrawer': withdrawer, 
                        'withdrawn': observed_event['attrs']['target_prefix']
                        })

            for item in withdrawn_events_list_temp:
                print(item)

            if withdrawn_events_list_temp:
                for withdrawn_event_temp in withdrawn_events_list_temp:
                    if not withdrawn_events_list:
                        withdrawn_events_list.append(withdrawn_event_temp)
                    else:
                        for i, withdrawn_event in enumerate(withdrawn_events_list):
                            if (str(withdrawn_event['withdrawer'])) == str(withdrawn_event_temp['withdrawer']) and \
                                    (str(withdrawn_event['withdrawn']) == str(withdrawn_event_temp['withdrawn'])):
                                break
                            if i == len(withdrawn_events_list) - 1:
                                withdrawn_events_list.append(withdrawn_event_temp)

            print('\n')
            for item in withdrawn_events_list:
                print(item)



            # Prepend

            print('\nPrepend')

            events = data['data']['events']
            prepend_events_list = list()

            for observed_event in events:

                if observed_event['type'] == 'A':

                    path = observed_event['attrs']['path']
                    previours_hop = ''

                    for elem in path:

                        if path.count(elem) > 1:
                            
                            # get the AS prepender
                            for hop in path:
                                if not previours_hop:
                                    previours_hop = hop
                                else:
                                    if hop == elem:
                                        prepender = previours_hop
                                        break
                                    else:
                                        previours_hop = hop


                            prepend_events_list.append([
                                observed_event['timestamp'],
                                elem,
                                prepender,
                                path.count(elem)
                                ])





            #for item in prepend_events_list:
            #    print(item)

        except Exception as error:
            print(error)


def main(argv=sys.argv[1]):    
    bgplay = BGPlay(argv)
    bgplay.get_events()


if __name__ == '__main__':
    main()



