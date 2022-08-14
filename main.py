
from itertools import count
import json
from datetime import datetime
import sys
import os
from time import sleep
import requests


LOC_BLACKLIST = [
    'Rio Grande',
    'Vineland',
    'Salem',
    'Cardiff',
    'Camden',
    'Delanco',
    'West Deptford',
    'Freehold'
]

MVC_URL = 'https://telegov.njportal.com/njmvc/AppointmentWizard/7'

def parse_time_data(time_list: json, location_ids: dict) -> list:
    result: list = []
    for appt in time_list:
        loc_id = appt['LocationId']
        name = location_ids[loc_id]
        time_str = appt['FirstOpenSlot'].split('Next Available: ')[1]
        time = datetime.strptime(time_str, '%m/%d/%Y %H:%M %p')
        delta = (time - datetime.today()).days
        url = f'https://telegov.njportal.com/njmvc/AppointmentWizard/7/{loc_id}'


        result.append({
            'name': name,
            'time': time,
            'delta': delta,
            'url': url
        })
    return result


def parse_location_data(location_list: json) -> dict:
    location_ids = {}
    for location in location_list:
        name = location['Name'].split(' - ')[0]
        loc_id = location['Id']
        location_ids[loc_id] = name
    return location_ids


def parse_html(html: str) -> tuple:
    counter: int = 0
    loc_data_prefix = 'var locationData = '
    time_data_prefix = 'var timeData = '
    loc_data = None
    time_data = None
    for line in html.splitlines():
        if loc_data_prefix in line:
            loc_data_str = line.split(loc_data_prefix)[1][:-1]
            loc_data = json.loads(loc_data_str)
        if time_data_prefix in line:
            time_data_str = line.split(time_data_prefix)[1]
            time_data = json.loads(time_data_str)
            break
        counter = counter + 1
    return (loc_data, time_data)


def print_appts(title: str, appts: list, show_url: bool=False) -> None:
    print(f':: {title}:')
    for appt in appts:
        print(f'\t(within {appt["delta"]} days) Time: {appt["time"]} Location: {appt["name"]}')
        if show_url:
            print(f'\t{appt["url"]}\n')



def grab() -> list:
    req = requests.get(MVC_URL)
    loc_data, time_data = parse_html(req.text)
    location_ids        = parse_location_data(loc_data)
    loc_time_list       = parse_time_data(time_data, location_ids)

    # sort in time order
    loc_time_list.sort(key=lambda x: x['time'])
    # blacklist filter
    loc_filtered = list(filter(lambda x: x['name'] not in LOC_BLACKLIST, loc_time_list))
    # time range filter
    loc_filtered = list(filter(lambda x: x['delta'] <= 30, loc_filtered))
    loc_alert = list(filter(lambda x: x['delta'] <= 7, loc_filtered))


    print_appts('All appointments', loc_time_list)
    print_appts('In radar appointments', loc_filtered, True)
    print_appts('Alert appointments', loc_alert, True)

    return loc_alert


alert_appt = None
while True:
    sleep(5)
    print(f'==========={datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}===========')
    loc_alert = grab()
    if not loc_alert:
        continue
    if alert_appt == None:
        os.system(f'xdg-open "{loc_alert[0]["url"]}"')
    alert_appt = loc_alert[0]
    name = alert_appt['name']
    delta = alert_appt['delta']
    say_str = f'Appointment found in {delta} day at {name}'
    os.system(f'espeak-ng "{say_str}"')
    
    # break
