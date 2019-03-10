#!/usr/bin/env python
import threading
import time
from datetime import datetime

import requests
import tweepy
from credentials import *
from pytz import timezone
from requests.auth import HTTPBasicAuth

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
agencyids = ["57035"]
TWEET_SLEEP_TIME = 10
PP_API_SLEEP = 30
MINUTES_REMOVE = 5
incidents = []


def grab_pulsepoint(agencyid):
    url = "https://api.pulsepoint.org/v1/incidents"
    pp_json = None
    while pp_json is None:
        try:
            pp_json = requests.get(url,
                                   auth=HTTPBasicAuth(username, password),
                                   params=(
                                       ('apikey', apikey),
                                       ('agencyid', agencyid),
                                       ('active', '1'),
                                   ),
                                   timeout=5
                                   ).json()
            return pp_json
        except:
            continue


def get_print_units(units):
    unitlist = []
    for unit in units:
        unitlist.append(unit[0] + " [" + unit[1] + "]")
    text = ', '.join(unitlist)
    return text


def check_if_cleared(agencyid):
    threading.Timer(MINUTES_REMOVE * 60, check_if_cleared, args=[agencyid]).start()
    json = grab_pulsepoint(agencyid)
    if json == "" or json['incidents'] is None:
        return
    for incident in incidents:
        if not any(incidentid["ID"] in incident[0] for incidentid in json['incidents']):
            print "Removing incident: %s" % incident
            incidents.remove(incident)



def status_update_pulsepoint(incidentid, calltype, units):
    print('status_update_pulsepoint()')
    for incident in incidents:
        if incident[0] == incidentid:
            if units != incident[2]:
                try:
                    incident[2] = units
                    text = "Units Updated:\n" + get_print_units(units)
                    time.sleep(TWEET_SLEEP_TIME)
                    print text
                    tweet = api.update_status(text, in_reply_to_status_id=incident[3])
                    incident[3] = tweet.id_str
                except Exception as e:
                    print e
            if calltype != incident[1]:
                try:
                    incident[1] = calltype
                    text = "Call Updated to:\n" + calltype
                    time.sleep(TWEET_SLEEP_TIME)
                    print text
                    tweet = api.update_status(text, in_reply_to_status_id=incident[3])
                    incident[3] = tweet.id_str
                except Exception as e:
                    print e


def loop_update_pulsepoint(agencyid):
    threading.Timer(PP_API_SLEEP, loop_update_pulsepoint, args=[agencyid]).start()
    unit_types = [
        ('DP', 'DISP'),
        ('AK', 'ACK'),
        ('ER', 'ENRT'),
        ('OS', 'ONSCN'),
        ('TR', 'TRNSPT'),
        ('TA', 'TRANSPT-A'),
        ('AQ', 'AVAIL'),
        ('AR', 'AVAIL'),
        ('AE', 'AVAIL-OS')
    ]
    json = grab_pulsepoint(agencyid)
    if json == "" or json['incidents'] is None:
        return
    for incident in json['incidents']:
        units = []
        if 'Unit' not in incident:
            return
        for unit in incident['Unit']:
            units.append([unit['UnitID'], next(
                fullstatus for (name, fullstatus) in unit_types if name == unit['PulsePointDispatchStatus'])])
        calltype = incident['AgencyIncidentCallTypeDescription']
        if not any(incident['ID'] in incident[0] for incident[0] in incidents):
            print "if not any %s in incidents: %s " % (incident['ID'], incidents)
            try:
                address = incident['MedicalEmergencyDisplayAddress']
                dt_obj = datetime.strptime(incident['CallReceivedDateTime'][:-1], "%Y-%m-%dT%H:%M:%S")
                dt = dt_obj.replace(tzinfo=timezone("UTC")).astimezone(timezone("US/Pacific")).strftime(
                    "%m/%d/%y @ %H:%M:%S %Z")
                call = "New Incident: " + calltype + "\nD/T: " + dt + "\nUNITS: " + get_print_units(
                    units) + "\nADDR: " + address
                print call
                print "DEBUG: Tweet is next"
                tweet = api.update_status(call)
                time.sleep(TWEET_SLEEP_TIME)
                incidents.append([incident['ID'], calltype, units, tweet.id_str,
                                  dt_obj.replace(tzinfo=timezone("UTC")).astimezone(timezone("US/Pacific")).replace(
                                      tzinfo=None)])
                print "incidents appended"
            except:
                pass
        else:
            status_update_pulsepoint(incident['ID'], calltype, units)


print('Starting PulsePoint-Twitter-Bot')
for agencyid in agencyids:
    loop_update_pulsepoint(agencyid)
    check_if_cleared(agencyid)
