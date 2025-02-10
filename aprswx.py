#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import requests
import datetime
import time
import importlib.util
from requests.auth import HTTPBasicAuth


# Moderne Art, Konfigurationsdateien zu importieren
def load_config(filename):
    spec = importlib.util.spec_from_file_location("config", filename)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    return config

# Konfigurationsdateien laden
credentials = load_config("credentials.py")
stations = load_config("stations.py")
rubrics = load_config("rubrics.py")

# Split array into smaller portions
def chunks(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]

# check response from DAPNET
def check_response(resp):
    if resp.status_code != 201:
        error = json.loads(resp.text)
        print(error)
        print(f"Error at {station[0]}")
        print(f'POST /news/ {resp.status_code}')

# Send data from wx station to dapnet
def send_DAPNET(entry, station):
    # This function is for creating and sending messages to DAPNET

    # attention: Timestamp in aprs.fi is epoch!
    ts_epoch = float(entry["time"])
    # so lets calculate and format in hhmm-format
    msgtime = datetime.datetime.fromtimestamp(ts_epoch).strftime('%H%M')

    # now it's time for building up the message itself
    msg = f"{msgtime}z {station['callsign']}/{station['qth']}: "

    # Dictionary für optionale WX-Daten
    wx_data = {
        'temp': lambda: f"{entry['temp']}C ",
        'wind': lambda: f"w: {entry['wind_speed']}m/s at {entry['wind_direction']}deg ",
        'humidity': lambda: f"h: {entry['humidity']}% ",
        'rain': lambda: f"rain: {entry['rain_1h']}mm/h"
    }

    # Elegantere Behandlung der optionalen Daten
    for key, formatter in wx_data.items():
        try:
            msg += formatter()
        except (KeyError, TypeError):
            continue

    # preparing the post-message
    post = {
        "rubricName": station["rubric"],
        "text": msg,
        "number": station["slot"]
    }
    print(post)

    # and sending it to DAPNET
    resp = requests.post(
        'https://hampager.de/api/news/',
        json=post,
        auth=HTTPBasicAuth(credentials.dapnetuser, credentials.dapnetpasswd)
    )
    check_response(resp)

    # this is a work-around for mirroring messages into another rubric 
    if station["rubric"] == "aprswx-dl-bw":
        post["rubricName"] = "hochrhein"
        print(post)
        resp = requests.post(
            'https://hampager.de/api/news/',
            json=post,
            auth=HTTPBasicAuth(credentials.dapnetuser, credentials.dapnetpasswd)
        )
        check_response(resp)

# let the party begin!
def main():
    selected_stations = []
    
    # Stationen nach Rubriken filtern
    selected_stations = [
        station["callsign"]
        for station in stations
        if any(rubric['rubric'] == station['rubric'] for rubric in rubrics)
    ]
    
    # In Chunks verarbeiten
    for station_chunk in chunks(selected_stations, 20):
        querystring = ",".join(station_chunk)
        response = requests.get(
            f"https://api.aprs.fi/api/get?name={querystring}&what=wx&apikey={credentials.aprsapikey}&format=json"
        )
        wx = response.json()
        
        for entry in wx["entries"]:
            station = next(
                item for item in stations 
                if item["callsign"] == entry["name"]
            )
            send_DAPNET(entry, station)

if __name__ == "__main__":
    main()
