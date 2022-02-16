import os
import sys
import requests
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pprint import pprint
from jinja2 import Environment, FileSystemLoader

def staking_endpoint(token):
    return f'https://www.binance.com/bapi/earn/v1/friendly/pos/union?pageSize=15&pageIndex=1&status=SUBSCRIBABLE&asset={token}'


def get_watchlist():
    return {
        'locked_savings': {
            'BTC': [90],
            'AXS': [15]
        },
        'locked_staking': {
            'SOL': [90],
            'DOT': [90],
            'ADA': [90],
            'MATIC': [90]
        }
    }

def render_table(name, data):
    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template(name)
    return template.render(data=data)

def send_mail(to_address, subject, body):
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_SERVER = os.environ.get('SMTP_SERVER')

    server_url = SMTP_SERVER
    port = 465
    username = SMTP_USERNAME
    password = SMTP_PASSWORD
    from_address = SMTP_USERNAME

    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = 'adamvorkel2@gmail.com'
    message['To'] = to_address
    part1 = MIMEText(body, 'plain')
    part2 = MIMEText(body, 'html')
    message.attach(part1)
    message.attach(part2)

    
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(server_url, port, context=context) as server:
        server.login(username, password)
        server.sendmail(from_address, to_address, message.as_string())
        server.quit()

def get_locked_savings_options (asset, durations):
    endpoint = f'https://www.binance.com/bapi/earn/v1/friendly/lending/project/customizedFixedProject/list?pageSize=15&pageIndex=1&status=SUBSCRIBABLE&asset={asset}'
    res = requests.get(endpoint)
    payload = res.json()
    data = payload['data']
    
    if not len(data):
        return []
    
    return [{
        'duration': int(p['duration']),
        'annual_interest_rate': float(p['interestRate']),
        'daily_interest_rate': float(p['interestPerLot']),
        'up_limit': float(p['lotsUpLimit']),
        'purchased': float(p['lotsPurchased']),
        'min_purchase': float(p['lotSize']),
        'max_purchase': float(p['maxLotsPerUser'])
    } for p in data[0]['list'] if int(p['duration']) in durations]
        
def get_locked_staking_options(asset, durations):
    endpoint = f'https://www.binance.com/bapi/earn/v1/friendly/pos/union?pageSize=15&pageIndex=1&status=SUBSCRIBABLE&asset={asset}'
    res = requests.get(endpoint)
    payload = res.json()
    data = payload['data']

    if not len(data):
        return []
    
    return [{
        'duration': int(p['duration']),
        'annual_interest_rate': float(p['config']['annualInterestRate']),
        'daily_interest_rate': float(p['config']['dailyInterestRate']),
        'up_limit': float(p['upLimit']),
        'purchased': float(p['purchased']),
        'min_purchase': float(p['config']['minPurchaseAmount']),
        'max_purchase': float(p['config']['maxPurchaseAmountPerUser'])
    } for p in data[0]['projects'] if int(p['duration']) in durations]

def run2():
    watchlist = get_watchlist()
    # data = {
        # 'locked_staking': {key:[] for key in watchlist['locked_staking'].keys()}, 
        # 'locked_savings': {key:[] for key in watchlist['locked_savings'].keys()}
    # }
    data = {'locked_savings': {} ,'locked_staking': {}}

    # Locked Savings
    for asset, durations in watchlist['locked_savings'].items():
        options = get_locked_savings_options(asset, durations)
        if options: data['locked_savings'][asset] = options
        
        
    # Locked Staking
    for asset, durations in watchlist['locked_staking'].items():
        options = get_locked_staking_options(asset, durations)
        if options: data['locked_staking'][asset] = options

    if data['locked_savings'] or data['locked_staking']:
        pprint(data)
        message = render_table('available_projects.html', data)
        subject = 'Binance Earn Options Available'
        send_mail('adamvorkel@gmail.com', subject, message)






def run(event, context):
    print('Running...')
    watchlist = get_watchlist()
    open_projects = {}
    for w in watchlist:
        res = requests.get(staking_endpoint(w['asset']))
        payload = res.json()
        data = payload['data']
        if not len(data):
            break

        projects = [{
                'duration': int(p['duration']),
                'annual_interest_rate': p['config']['annualInterestRate'],
                'daily_interest_rate': p['config']['dailyInterestRate'],
                'up_limit': p['upLimit'],
                'purchased': p['purchased'],
                'min_purchase': p['config']['minPurchaseAmount'],
                'max_purchase': p['config']['maxPurchaseAmountPerUser']
        } for p in data[0]['projects'] if p['asset'] == w['asset'] and int(p['duration']) in w['duration'] and p['sellOut'] == False]

        if len(projects):
            open_projects[w['asset']] = projects

    if open_projects:
        projects = [f"{asset}-{'|'.join([str(d['duration']) for d in projects])}" for asset, projects in open_projects.items()]

        subject = f"Binance stake available - {', '.join(projects)}"
        message = ''

        message += '<html>'
        message += '<head>'
        message += """<style>
        body {
            width: 100%;
        }
        th {
            text-align: left;
        }
        table {
            width: 100%;
            padding: 0.5rem;
        }
        </style>"""
        message += '</head>'
        message += '<body>'

        for asset, options in open_projects.items():
            message += f"<h4>{asset}</h4>"
            message += '<table>'
            message += '<thead>'
            message += '<tr>'
            message += '<th>Duration</th>'
            message += '<th>APY</th>'
            message += '<th>Daily %</th>'
            message += '<th>Range</th>'
            message += '<th>Sold out</th>'
            message += '</tr>'
            message += '</thead>'
            message += '<tbody>'
            
            for o in options:
                message += '<tr>'
                message += f"<td>{o['duration']}</td>" 
                message += f"<td>{round(float(o['annual_interest_rate']) * 100, 4)}%</td>" 
                message += f"<td>{round(float(o['daily_interest_rate']) * 100, 4)}%</td>"
                message += f"<td>{round(float(o['min_purchase']), 2)} - {round(float(o['max_purchase']), 2)}</td>"
                message += f"<td>{round(float(o['purchased']) / float(o['up_limit']) * 100, 2)}%</td>" 
                message += '</tr>'
            message += '</tbody>'
            message += '</table>'

        message += '</body>'
        message += '</head>'
        print(f'sending mail with subject {subject}')
        send_mail('adamvorkel@gmail.com', subject, message)
        # print(f"no availability for {w['asset']} | {'/'.join(str(d) for d in w['duration'])}")
    else:
        print('no availability')
