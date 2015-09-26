import fitbit
from flask import render_template, flash, redirect, session, url_for, request, jsonify, send_from_directory
from application import app, db
from models import User
from random import choice
from highcharts import Chart
from flask_oauthlib.client import OAuth
import os
import json
import humanize
import dateutil.parser
from numpy import average

try:
    from secrets import keys as SECRETS
except ImportError:
    SECRETS = {}

MY_CONSUMER_KEY = SECRETS.get("CONSUMER_KEY", False) or os.environ.get('CONSUMER_KEY')
MY_CONSUMER_SECRET = SECRETS.get("CONSUMER_SECRET", False) or os.environ.get('CONSUMER_SECRET')
MY_EMAIL_ADDRESS = SECRETS.get("EMAIL_USER", False) or os.environ.get('EMAIL_USER')

CONVERSION = {
    "en_US": "Pounds"
}

# Setup
# ----------------------------
oauth = OAuth()
fitbit_app = oauth.remote_app(
    'fitbit',
    base_url='https://api.fitbit.com',
    request_token_url='https://api.fitbit.com/oauth/request_token',
    access_token_url='https://api.fitbit.com/oauth/access_token',
    authorize_url='https://www.fitbit.com/oauth/authorize',
    consumer_key=MY_CONSUMER_KEY,
    consumer_secret=MY_CONSUMER_SECRET
)


# Routes
# ----------------------------

@app.errorhandler(404)
def page_not_found(e):
    app.logger.info('404')
    return render_template('404.html'), 404


@app.errorhandler(500)
def page_not_found(e):
    app.logger.info('404')
    return render_template('500.html'), 404


@app.route('/')
def index():
    if not session.get('fitbit_keys', False):
        return redirect(url_for('intro'))
    user_id = session['user_profile']['user']['encodedId']
    steps = get_activity(user_id, 'steps', period='1d', return_as='raw')[0]['value']
    calories = get_activity(user_id, 'calories', period='1d', return_as='raw')[0]['value']
    weights = get_activity(user_id, 'weight', period='1w', return_as='raw')
    weight0 = weights[0]['value']
    weightn = weights[-1]['value']
    diff = (float(weight0) - float(weightn))
    if diff > 0:
        diff = "+" + str(diff)
    else:
        diff = str(diff)
    sleep = get_activity(user_id, 'timeInBed', period='1d', return_as='raw')[0]['value']
    chartdata = get_activity(user_id, 'steps', period='1w', return_as='raw')
    weight_unit = CONVERSION[session['user_profile']['user']['weightUnit']]
    return render_template('home.html', steps=steps, calories=calories, weight=diff, sleep=sleep, chartdata=chartdata,
                           weights=weights, weight_unit=weight_unit)


@app.route('/profile')
def profile():
    if not session.get('fitbit_keys', False):
        return redirect(url_for('intro'))
    return render_template('profile.html')


@app.route('/steps')
def steps():
    if not session.get('fitbit_keys', False):
        return redirect(url_for('intro'))
    user_id = session['user_profile']['user']['encodedId']
    all_steps = get_activity(user_id, 'steps', period='max', return_as="raw")
    year_steps = get_activity(user_id, 'steps', period='1y', return_as="raw")
    month_steps = get_activity(user_id, 'steps', period='1m', return_as="raw")
    week_steps = get_activity(user_id, 'steps', period='1w', return_as="raw")
    day_steps = get_activity(user_id, 'steps', period='1d', return_as="raw")
    statsbar = [
        {
            'icon': "fa-step-forward fa-rotate-270",
            'title': "All Time Max Steps",
            'value': max([int(d.get('value')) for d in all_steps])
        },
        {
            'icon': "fa-step-forward fa-rotate-90",
            'title': "Average Daily Steps",
            'value': int(average([int(d.get('value')) for d in all_steps]))
        },
        {
            'icon': "fa-calendar",
            'title': "Month Max Steps",
            'value': max([int(d.get('value')) for d in month_steps])
        },
        {
            'icon': "fa-balance-scale",
            'title': "Steps Today",
            'value': max([int(d.get('value')) for d in day_steps])
        }
    ]
    boxplot_data = group_by_month(clean_max(all_steps))
    charts = [
        {
            "title": "Steps for Past Month",
            "id": "month-steps",
            "chart": Chart("Steps for Past Month",
                           xType="datetime",
                           xCategories=[d.get('dateTime') for d in month_steps]
                           ).add_series("Steps",
                                        data=[d.get('value') for d in month_steps],
                                        type="column")

        },
        {
            "title": "Average Steps per Month",
            "id": "month-average",
            "chart": Chart(
                "Average Steps Per Month",
                xtype="datetime",
                xCategories=[d.get('month') for d in boxplot_data]
            ).add_series(
                "Steps",
                data=[d.get('plot') for d in boxplot_data],
                type="boxplot"
            ).add_series(
                "Outliers",
                data=[[d.get('index'), ] + d.get('outliers') for d in boxplot_data if d.get('outliers', False)],
                type="scatter"
            )
        },
        {
            "title": "Monthly Average Yearcycle",
            "id": "yearcycle",
            "chart": Chart(
                "Monthly Average Yearcycle",
                xCategories=['Jan', 'Feb', 'Mar', "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            ).add_raw_series(get_yearcycle(clean_max(all_steps), return_as="raw"))
        },
        {
            "title": "Average for Time Period",
            "id": "time-period",
            "chart": Chart(
                "Average Steps For Different Time Periods",
                xCategories=["All Time", "Year", "Month", "Week"]
            ).add_raw_series(get_periods(clean_max(all_steps), year_steps, month_steps, week_steps))
        }

    ]
    print get_yearcycle(clean_max(all_steps))

    return render_template('statpage.html', title="Steps", statsbar=statsbar, charts=charts)


@app.route('/calories')
def calories():
    if not session.get('fitbit_keys', False):
        return redirect(url_for('intro'))
    return render_template('calories.html')


@app.route('/weight')
def weight():
    if not session.get('fitbit_keys', False):
        return redirect(url_for('intro'))
    # Fetches
    user_id = session['user_profile']['user']['encodedId']
    weight_unit = CONVERSION[session['user_profile']['user']['weightUnit']]
    weights = get_connector(user_id).get_bodyweight(user_id=user_id, period='1m')['weight']
    all_weight = clean_max(get_activity(user_id, 'weight', period='max', return_as='raw'))
    year_weight = get_activity(user_id, 'weight', period='1y', return_as='raw')
    month_weight = get_activity(user_id, 'weight', period='1m', return_as='raw')
    week_weight = get_activity(user_id, 'weight', period='1w', return_as='raw')
    # series setup
    chartdata = group_by_day(weights, 'weight')
    boxplot = group_by_month(all_weight)
    yearcycle = get_yearcycle(all_weight)
    periods = get_periods(all_weight, year_weight, month_weight, week_weight)
    weight_max = max([d.get('value') for d in all_weight])
    weight_min = min([d.get('value') for d in all_weight])
    weight_last = weights[-1]['weight']
    month_max = max([d.get('value') for d in month_weight])
    statsbar = [
        {
            'icon': "fa-step-forward fa-rotate-270",
            'title': "All Time Max Weight",
            'value': weight_max
        },
        {
            'icon': "fa-step-forward fa-rotate-90",
            'title': "All Time Min Weight",
            'value': weight_min
        },
        {
            'icon': "fa-calendar",
            'title': "Month Max Weight",
            'value': month_max
        },
        {
            'icon': "fa-balance-scale",
            'title': "Last Weight",
            'value': weight_last
        }
    ]
    charts = [
        {
            "title": "Weight Fluctuations for Past Month",
            "id": "weight",
        },
        {
            "title": "Average Weight All Time",
            "id": "allweight",
        },
        {
            "title": "Monthly Boxplot",
            "id": "boxplot",
        },
        {
            "title": "Yearly Cycle",
            "id": "yearcycle",
        },
        {
            "title": "Averages for Periods",
            "id": "period",
        },

    ]
    return render_template('weight.html', weights=weights, weight_unit=weight_unit, chartdata=chartdata,
                           all_weight=all_weight, boxplot=boxplot, yearcycle=yearcycle, periods=periods,
                           statsbar=statsbar, charts=charts)


@app.route('/sleep')
def sleep():
    if not session.get('fitbit_keys', False):
        return redirect(url_for('intro'))
    return render_template('sleep.html')


@app.route('/settings')
def settings():
    if not session.get('fitbit_keys', False):
        return redirect(url_for('intro'))
    return render_template('settings.html')


@app.route('/intro')
def intro():
    if session.get("fitbit_keys", False):
        return redirect(url_for('index'))
    return render_template('intro.html')


@fitbit_app.tokengetter
def get_fitbit_app_token(token=None):
    return session.get('fitbit_app_token')


@app.route('/login')
def login():
    """ Start login process
    """
    return fitbit_app.authorize(
        callback=url_for('oauth_authorized', next=request.args.get('next') or request.referrer or None))


@app.route('/oauth_authorized')
@fitbit_app.authorized_handler
def oauth_authorized(resp):
    """ Authorize using OAUTH """
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)
    print request
    print resp

    user_id = resp['encoded_user_id']
    user_key = resp['oauth_token']
    user_secret = resp['oauth_token_secret']

    session['fitbit_keys'] = (
        user_id, user_key, user_secret)  # add session cookie
    active_user = User(user_id, user_key, user_secret)
    check_user = User.query.filter_by(user_id=user_id).first()

    if check_user is None:
        db.session.add(active_user)
        db.session.commit()

    session['user_profile'] = get_user_profile(user_id)
    session['device_info'] = get_device_info(user_id)

    return redirect(url_for('index'))


#

@app.route('/user/<user_id>/drop')
def drop_user(user_id):
    """ Drop user from databaase """
    app.logger.info('delete,request to delete %r' % user_id)

    user = User.query.filter_by(user_id=user_id).first_or_404()
    db.session.delete(user)
    db.session.commit()
    check_user = User.query.filter_by(user_id=user_id).first()

    if check_user is None:
        flash('Successfully Deleted Account')
        session.pop('fitbit_keys', None)
        session.pop('user_profile', None)
        session.pop('device_info', None)

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """ Logout pops session cookie """
    session.pop('fitbit_keys', None)
    session.pop('user_profile', None)
    return redirect(url_for('index'))


# API
# ----------------------------

@app.route('/u/<user_id>/<resource>/<period>')
def get_activity(user_id, resource, period='1w', return_as='json'):
    """ Function to pull data from Fitbit API and return as json or raw specific to activities """
    global dash_resource
    app.logger.info('resource, %s, %s, %s, %s, %s' %
                    (user_id, resource, period, return_as, request.remote_addr))

    ''' Use  API to return resource data '''

    slash_resource = 'activities/' + resource

    colors = (
        'yellow',
        'green',
        'red',
        'blue',
        'mediumGray',
        'aqua',
        'orange',
        'lightGray')

    datasequence_color = choice(colors)

    if period in ('1d', '1w', '1m'):
        graph_type = 'bar'
    else:
        graph_type = 'line'

    # Activity Data
    if resource in ('distance',
                    'steps',
                    'floors',
                    'calories',
                    'elevation',
                    'minutesSedentary',
                    'minutesLightlyActive',
                    'minutesFairlyActive',
                    'minutesVeryActive',
                    'activeScore',
                    'activityCalories'):
        slash_resource = 'activities/' + resource
        dash_resource = 'activities-' + resource

    # Sleep Data
    if resource in ('startTime',
                    'startTime',
                    'timeInBed',
                    'minutesAsleep',
                    'awakeningsCount',
                    'minutesAwake',
                    'minutesToFallAsleep',
                    'minutesAfterWakeup',
                    'efficiency'):
        slash_resource = 'sleep/' + resource
        dash_resource = 'sleep-' + resource

    if resource in ('weight',
                    'bmi',
                    'fat'):
        slash_resource = 'body/' + resource
        dash_resource = 'body-' + resource

    the_data = get_connector(user_id).time_series(
        slash_resource, base_date='today', period=period)[dash_resource]

    if return_as == 'raw':
        return the_data
    if return_as == 'json':
        return jsonify(output_json(the_data, resource, datasequence_color, graph_type))


# Filters
# ----------------------------

@app.template_filter()
def natural_time(datetime):
    """Filter used to convert Fitbit API's iso formatted text into
    an easy to read humanized format"""
    a = humanize.naturaltime(dateutil.parser.parse(datetime))
    return a


@app.template_filter()
def natural_number(number):
    """ Filter used to present integers cleanly """
    a = humanize.intcomma(number)
    return a


# Building Blocks
# ----------------------------

def get_creds(user_id):
    """Function takes user_id in and returns user_id, user_key, user_secret from db"""
    creds = User.query.filter_by(user_id=user_id).first_or_404()
    return creds


def get_connector(user_id):
    """Function takes user_id and returns variable to connect to fitbit from db"""
    x = get_creds(user_id)

    connector = fitbit.Fitbit(
        MY_CONSUMER_KEY,
        MY_CONSUMER_SECRET,
        resource_owner_key=x.user_key,
        resource_owner_secret=x.user_secret)
    return connector


def get_device_info(user_id):
    """ Function used to return device info
        https://wiki.fitbit.com/display/API/API-Get-Devices """
    device_info = get_connector(user_id).get_devices()
    return device_info


def get_user_profile(user_id):
    """ Function to return user profile
        https://wiki.fitbit.com/display/API/API-Get-User-Info """
    user_profile = get_connector(user_id).user_profile_get()
    return user_profile


def output_json(dp, resource, datasequence_color, graph_type):
    """ Return a properly formatted JSON file for Statusboard """
    graph_title = ''
    datapoints = list()
    print dp
    for x in dp:
        datapoints.append(
            {'title': x['dateTime'], 'value': float(x['value'])})
    datasequences = []
    datasequences.append({
        "title": resource,
        # "color":        datasequence_color,
        "datapoints": datapoints,
    })

    graph = dict(graph={
        'title': graph_title,
        'yAxis': {'hide': False},
        'xAxis': {'hide': False},
        'refreshEveryNSeconds': 600,
        'type': graph_type,
        'datasequences': datasequences,
    })

    return graph


# Graph Helpers
# ------------------------

def group_by_day(data, attr):
    grouped = []
    days = {}
    for point in data:
        days.setdefault(point['date'], []).append(point[attr])
    for key in sorted(days):
        min_val = min(days[key])
        max_val = max(days[key])
        avg_val = sum(days[key]) / len(days[key])
        grouped.append({"day": key, attr: avg_val, "error": [min_val, max_val]})
    return grouped


def group_by_month(data):
    i = 0
    grouped = []
    months = {}
    for point in data:
        year, month, day = point['dateTime'].split('-')
        yearmonth = "{0}-{1}".format(year, month)
        months.setdefault(yearmonth, []).append(point['value'])
    for key in sorted(months):
        outliers = []
        weights = sorted(months[key])
        plot = calculate_boxplot(weights)
        low, _, _, _, upr = plot
        for w in weights:
            if float(w) > upr or float(w) < low:
                outliers.append(w)
        grouped.append({"month": key, "plot": plot, "outliers": outliers, "index": i})
        i += 1
    return grouped


def get_yearcycle(data, return_as="json"):
    years = {}
    output = []
    for point in data:
        year, month, day = point['dateTime'].split('-')
        if int(year) not in years:
            years[int(year)] = {}
        if int(month) not in years[int(year)]:
            years[int(year)][int(month)] = []
        years[int(year)][int(month)].append(flt(point['value']))
    for y in years:
        months = []
        for m in range(1, 13):
            if years[y].get(m, False):
                months.append(flt(sum(years[y][m]) / len(years[y][m])))
            else:
                months.append(None)
        output.append({
            "name": y,
            "data": months
        })
    if return_as is "json":
        return json.dumps(output)
    elif return_as is "raw":
        return output
    else:
        return output


def calculate_median(numbers):
    nums = sorted(numbers)
    if len(nums) % 2 == 0:
        median = (flt(nums[len(nums) / 2]) + flt(nums[(len(nums) / 2) - 1])) / 2
    else:
        median = nums[len(nums) / 2]
    return flt(median)


def calculate_quartiles(numbers):
    nums = sorted(numbers)
    if len(nums) % 2 == 0:
        low_qtr = calculate_median(nums[:(len(nums) / 2)])
        upr_qtr = calculate_median(nums[len(nums) / 2:])
    else:
        low_qtr = calculate_median(nums[:(len(nums) / 2)])
        upr_qtr = calculate_median(nums[(len(nums) / 2) + 1:])
    return (flt(low_qtr), flt(upr_qtr))


def calculate_boxplot(numbers):
    nums = sorted(numbers)
    median = calculate_median(nums)
    low_qtr, upr_qtr = calculate_quartiles(nums)
    iqr = upr_qtr - low_qtr
    upr_wsk = flt(upr_qtr + (1.5 * iqr))
    low_wsk = flt(low_qtr - (1.5 * iqr))
    if low_wsk < 0:
        low_wsk = 0
    return [low_wsk, low_qtr, median, upr_qtr, upr_wsk]


def get_periods(all, year, month, week, day=None):
    all_list = [flt(d.get('value')) for d in all]
    year_list = [flt(d.get('value')) for d in year]
    month_list = [flt(d.get('value')) for d in month]
    week_list = [flt(d.get('value')) for d in week]
    series = []
    series.append({
        "name": "Averages",
        "type": "line",
        "data": [flt(average(all_list)), flt(average(year_list)), flt(average(month_list)), flt(average(week_list))]
    })
    series.append({
        "name": "Stats",
        "type": "boxplot",
        "data": [calculate_boxplot(all_list), calculate_boxplot(year_list), calculate_boxplot(month_list),
                 calculate_boxplot(week_list)]
    })
    return series


def flt(arg):
    """
    return single digit float
    :param arg:
    :return:
    """
    return float("{0:.1f}".format(float(arg)))


def clean_max(data):
    """
    Removes the filled dates that fitbit adds when max is selected
    :param data:
    :return:
    """
    while data[0]['value'] == data[1]['value']:
        data.pop(0)
    return data
