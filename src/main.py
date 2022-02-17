import os
import requests
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader

def staking_endpoint(token):
    return f'https://www.binance.com/bapi/earn/v1/friendly/pos/union?pageSize=15&pageIndex=1&status=SUBSCRIBABLE&asset={token}'

def parse_watchlist_string(watchlist_string):
    watchlist_items = [p.strip().split('-') for p in watchlist_string.split(',')]
    return {p[0]: [int(i) for i in p[1:]] for p in watchlist_items }

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

def run(event, context):
    locked_savings_watchlist_string = os.environ.get('LOCKED_SAVINGS_WATCHLIST')
    locked_staking_watchlist_string = os.environ.get('LOCKED_STAKING_WATCHLIST')
    locked_savings_watchlist = parse_watchlist_string(locked_savings_watchlist_string)
    locked_staking_watchlist = parse_watchlist_string(locked_staking_watchlist_string)

    watchlist = {
        'locked_staking': locked_staking_watchlist,
        'locked_savings': locked_savings_watchlist,
    }

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
        message = render_table('available_projects.html', data)
        subject = 'Binance Earn Options Available'
        send_mail('adamvorkel@gmail.com', subject, message)
    else: print(f'no availability for savings({locked_savings_watchlist}) or staking ({locked_staking_watchlist})')