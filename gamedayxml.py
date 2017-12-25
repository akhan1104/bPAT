# functions to parse mlbgameday xml data
# Created: 12/14/17
from urllib2 import urlopen
from datetime import date, timedelta
import xml.etree.ElementTree as ET
import pandas as pd


def getGameIDs(url):
    """ Given a single day base url return a list of urls to individual games that will be parsed """
    f = urlopen(url + '/master_scoreboard.xml')
    data = f.read()
    f.close()

    root = ET.fromstring(data)
    
    
    base = 'http://gd2.mlb.com'
    
    ret = []
    for c in root:
        # remove PPD games
        a = c.find('status')
        if a.attrib['status'] != 'Postponed':
            ret.append(base + c.attrib['game_data_directory'])

    return ret
   

def parseEvents(url):
    """ Given a gameday url parse out events from game_events.xml
        Input: Single base gameday URL as a string
        Output: Single DataFrame with event info """

    f = urlopen(url + '/game_events.xml')
    data = f.read()
    f.close()

    root = ET.fromstring(data)
    game_id = url[url.find('gid') : url.find('/box')]

    gameEvents = pd.DataFrame()

    # traverse tree pull out desired info
        # gameid, ab_num, b, s, o, batter, pitcher, event_num, event, b1(baserunner1)
        # b2, b3, final pitch type, final pitch speed 
    for inning in root.findall('inning'):
        for half in list(inning):
            for ab in half.findall('atbat'):
                #some xml errors found on mlb side
                try:
                    info = ab.attrib
                    last_pitch = ab.findall('pitch')[-1]
                except IndexError:
                    continue
               
                d = {'game_id' : game_id, 'ab_num' : info['num'],
                     'b' : info['b'], 's' : info['s'], 'o' : info['o'],
                     'batter' : info['batter'], 'pitcher' : info['pitcher'] ,
                     'event_num' : info['event_num'] , 'event' : info['event'],
                     'b1' : info['b1'], 'b2' : info['b2'], 'b3' : info['b3'],
                     'pitch_type' : last_pitch.attrib['pitch_type'],
                     'pitch_speed' : last_pitch.attrib['start_speed']}
                gameEvents = pd.concat([gameEvents, pd.DataFrame(d, index=[int(info['num'])])])
                
    return gameEvents



def parseBoxScore(url):
    """ Given a gameday url parse out desired stats from boxscore.xml
        Input: Single base gameday URL as a string
        Output: Tuple of size 3, None if game wasn't played, 3 data frames if it was"""

    f = urlopen(url + '/boxscore.xml')
    data = f.read()
    f.close()
    game_id = url[url.find('gid') : url.find('/box')]

    root = ET.fromstring(data)
    
    # If game was ppd or not final, throw it out
    if root.attrib['status_ind'] != 'F':
        return None, None, None

    # store linescores as a string
    linescore = root.find('linescore')
    innings = list(linescore)
    LS = ''
    for i in innings:
        LS += i.attrib['away'] + i.attrib['home']
    
    # store overall game summary as dataframe
    game_summary = pd.DataFrame(root.attrib, index=[0])
    game_summary['game_id'].loc[0] = game_id
    game_summary['linecore'] = LS
    
    # go through tags and find batting/pitching stats
    batting, pitching = list(), list()

    for i in list(root):
        for j in list(i):
            if i.tag == 'batting':
                batting.append(j.attrib)
            elif i.tag == 'pitching':
                pitching.append(j.attrib)

    # to data frame then drop empty rows
    b, p = pd.DataFrame(batting), pd.DataFrame(pitching)
    b.dropna(how='all', inplace=True)
    p.dropna(how='all', inplace=True)
    
    # add game_day id for database linking
    b['game_id'] = game_id
    p['game_id'] = game_id
    # return tuple of dataframes
    return game_summary, b, p


def urlCombiner(year, month, day):
    """ Returns a base url for a given year, month, date combination
        Input: Three values (string or int) as year, month, day
        Output: A string representing the URL of a gameday directory """

    base_url = 'http://gd2.mlb.com'
    # directories require 0 in front of single digits
    if int(month) < 10:
        month = '0' + str(month)
    if int(day) < 10:
        day = '0' + str(day)

    return base_url + '/components/game/mlb/' + 'year_' + str(year) + '/month_' + str(month) + '/day_' + str(day)


def getSeasonDays(start, end):
    """ Get a list of gameday directories given an inseason date range """
    delta = end - start
    urls = []
    for i in range(delta.days + 1):
        currDay = start+ timedelta(days=i)
        urls.append(urlCombiner(currDay.year, currDay.month, currDay.day))
    return urls


### Test Script ### - Eventually just functions
year = 2017
month = '08'
day = 11

time = (year, month, day)
t0_2017 = date(2017, 4, 02)
tf_2017 = date(2017, 5, 01)
tDelta = tf_2017 - t0_2017

#get all days in a season as a list of URL directories
all_days = getSeasonDays(t0_2017, tf_2017)

#get a list of lists representing all gameday directories
all_games = [getGameIDs(i) for i in all_days]

#flatten list
flat_all_games = [item for sublist in all_games for item in sublist]

games_url = urlCombiner(year, month, day)

#get all stats for a single day

summary, hitters, pitchers, events = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

for i in flat_all_games:
    print i
    s, h, p = parseBoxScore(i)
    ev = parseEvents(i)
    summary = pd.concat([summary, s])
    hitters = pd.concat([hitters, h])
    pitchers = pd.concat([pitchers, p])
    events = pd.concat([events, ev])
    events.reset_index(inplace=True)




