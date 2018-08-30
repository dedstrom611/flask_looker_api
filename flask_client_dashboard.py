from flask import Flask, render_template, request, json, jsonify, redirect, url_for, make_response
import pandas as pd
import numpy as np
import os
import types
import requests
import jwt
import json
import code
import datetime as dt
from lookerapi import LookerApi
from functools import wraps

def login_required(function_to_protect):
    @wraps(function_to_protect)
    def wrapper(*args, **kwargs):
        authorized = False
        session_jwt = request.cookies.get('client_dashboard_session')
        if session_jwt:
            #code.interact(local=dict(globals(), **locals()))
            user = jwt.decode(session_jwt, secret, algorithms=['HS256'], options={'verify_exp': False})
            if is_authorized(user):
                authorized = True
        elif DASHBOARD_COOKIE_NAME in request.cookies:
            cookie_in = request.cookies.get(DASHBOARD_COOKIE_NAME)
            cookie_out = {DASHBOARD_COOKIE_NAME: cookie_in}
            hdr = {'accept': 'application/json'}

            s = requests.Session()

            r = s.get(DASHBOARD_URL+"/session/token", headers=hdr, cookies=cookie_out)
            if r.status_code == 200:
                t = json.loads(r.text)
                # code.interact(local=dict(globals(), **locals()))

                session_jwt = t['token']
                user_info = jwt.decode(session_jwt, secret, algorithms=['HS256'], options={'verify_exp': False})

                authorized = is_authorized(user_info)

            s.close()
        if authorized:
            resp = make_response(function_to_protect(*args, **kwargs))
            resp.set_cookie('client_dashboard_session', session_jwt)
            return resp
        else:
            return render_template('/authorization_instructions.html')

    return wrapper

def is_authorized(user):
    authorized = False
    for role in user['roles']:
        if role['name'] == 'admin':
            authorized = True
    return authorized

def get_markets_list(obj):
    #query JSON body
    body = {'model': 'dispatch', 'view': 'visit_facts', 'fields': ['market_dimensions.market_name']}
    m = obj.run_inline_query(body)
    mkts = [d['market_dimensions.market_name'] for d in m]
    return mkts

def get_channel_subtype_list(obj):
    #query JSON body
    body = {'model': 'dispatch', 'view': 'visit_facts', 'fields': ['channel_dimensions.sub_type']}
    s = obj.run_inline_query(body)
    subtypes = [d['channel_dimensions.sub_type'] for d in s]
    return subtypes

def get_channels_list(obj):
    #body = {'model': 'dispatch', 'view': 'visit_facts', 'fields': ['channel_dimensions.organization']}
    c = obj.get_look(528)
    channels = [d['channel_dimensions.organization'] for d in c]
    return channels

def make_channel_dict(icds):
    desclist=[]
    pctlist=[]
    icd_10=dict()
    for i in icds:
        icd_10['desc'] = desclist.append(i['icd_code_dimensions.diagnosis_group'])
        pct = int(round(i['pct_of_total']*100), 0)
        icd_10['pct'] = pctlist.append(int(round(i['pct_of_total']*100, 0)))

app = Flask(__name__)

DASHBOARD_COOKIE_NAME = '_station_session'
DASHBOARD_URL = 'https://admin.dispatchhealth.com' # consider setting this in an ENV var

api_endpoint = 'https://dispatchhealth.looker.com:19999/api/3.0/'
client_id = os.environ['LOOKER_API_KEY']
client_secret = os.environ['LOOKER_API_SECRET']

key = ['DASHBOARD_ADMIN_KEY']
secret = os.environ['DH_ADMIN_SECRET']

@app.route('/', methods=['POST', 'GET'])
@login_required
def submit():
    looker = LookerApi(client_id, client_secret, api_endpoint)
    c = looker.get_look(528)
    channel_list = [d['channel_dimensions.organization'] for d in c]
    market_list = get_markets_list(looker)
    subtype_list = get_channel_subtype_list(looker)

    return render_template('submit.html', channel_list=channel_list, market_list=market_list, subtype_list=subtype_list)

@app.route('/get_channels_list', methods=['POST','GET'])
@login_required
def get_channels_list():
    #code.interact(local=dict(globals(), **locals()))
    markets = request.args.get("market")

    body = {'model': 'dispatch', 'view': 'visit_facts', 'fields': ['channel_dimensions.organization'],
    'filters': {'channel_dimensions.organization': '',
    'market_dimensions.market_name': ','.join(markets)}}

    c = obj.run_inline_query(body)
    channels = [{'name': d['channel_dimensions.organization'] for d in c}]
    return jsonify(channels)

@app.route('/report', methods=['POST', 'GET'])
@login_required
def index():
    looker = LookerApi(client_id, client_secret, api_endpoint)

    markets = request.form.getlist('market')
    channels = request.form.getlist('channel')
    subtypes = request.form.getlist('subtype')
    start_date = request.form.getlist('start_date')
    end_date = request.form.getlist('end_date')

    r = looker.get_look_query(500)
    i = looker.get_look_query(532)

    r = r['query']
    i = i['query']

    # Format the date query the way Looker expects it
    if start_date[0] != '' and end_date[0] != '':
        date_query = dt.datetime.strptime(start_date[0], '%Y-%m-%d').strftime('%Y/%m/%d') + ' to '\
                     + dt.datetime.strptime(end_date[0], '%Y-%m-%d').strftime('%Y/%m/%d')
    else:
        date_query = r['filters']['visit_dimensions.local_visit_date']

    print(date_query)

    # Get only necessary fields to run an inline query
    t = {k: r[k] for k in ('model', 'view', 'fields', 'limit', 'dynamic_fields', 'filters')}
    m = {n: i[n] for n in ('model', 'view', 'fields', 'limit', 'dynamic_fields', 'filters')}
    # Replace existing filters with new filters
    t['filters']['market_dimensions.market_name'] = ','.join(markets)
    t['filters']['channel_dimensions.organization'] = ','.join(channels)
    t['filters']['channel_dimensions.sub_type'] = ','.join(subtypes)
    t['filters']['visit_dimensions.local_visit_date'] = date_query
    r2 = looker.run_inline_query(t)

    m['filters']['market_dimensions.market_name'] = ','.join(markets)
    m['filters']['channel_dimensions.organization'] = ','.join(channels)
    m['filters']['channel_dimensions.sub_type'] = ','.join(subtypes)
    m['filters']['visit_dimensions.local_visit_date'] = date_query
    m2 = looker.run_inline_query(m)

    #code.interact(local=dict(globals(), **locals()))

    r2 = r2[0]

    try:
        on_route_time = int(round(r2['avg_on_route_time'], 0))
        on_scene_time = int(round(r2['avg_on_scene_time'], 0))
        bb_rate = int(round(r2['bb_rate'] * 100, 0))
        ed_escalation = int(round(r2['ed_escalation_rate'] * 100, 0))
        nps = int(round(r2['nps'], 0))
        num_requests = "{:,}".format(r2['visit_facts.visits'])
        cost_svg = "{:,}".format(int(round(r2['cost_savings'], 0)))
        avg_age = int(round(r2['patient_dimensions.average_age'], 0))
        pct_female = int(round(r2['pct_female'], 0))
        pct_male = int(round(r2['pct_male'], 0))
        pct_web = int(round(r2['pct_web'] * 100, 0))
        pct_mobile = int(round(r2['pct_mobile'] * 100, 0))
        pct_phone = int(round(r2['pct_phone'] * 100, 0))
    except Exception as e:
        on_route_time = 0
        on_scene_time = 0
        bb_rate = 0
        ed_escalation = 0
        nps = 0
        num_requests = "{:,}".format(r2['visit_facts.visits'])
        cost_svg = 0
        avg_age = 0
        pct_female = 0
        pct_male = 0
        pct_web = 0
        pct_mobile = 0
        pct_phone = 0

    icds = m2[0:5]
    icd_codes = [i['icd_code_dimensions.diagnosis_group'] for i in icds]
    icd_pcts = [int(round(p['pct_of_total']*100,0)) for p in icds]

    """Render the client overview report."""
    return render_template('client_overview_report.html', on_route_time=on_route_time,cost_svg=cost_svg,\
    on_scene_time=on_scene_time, bb_rate=bb_rate, ed_escalation=ed_escalation, nps=nps, num_requests=num_requests,\
    avg_age=avg_age, pct_female=pct_female, pct_male=pct_male, pct_web=pct_web, pct_mobile=pct_mobile,\
    pct_phone=pct_phone, icd_codes=icd_codes, icd_pcts=icd_pcts, markets=markets, channels=channels,\
    subtypes=subtypes, start_date=start_date, end_date=end_date)

if __name__ == '__main__':
    app.run()
