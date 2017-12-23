# functions to parse mlbgameday xml data
# Created: 12/14/17
from urllib2 import urlopen
import xml.etree.ElementTree as ET
import pandas as pd


def getGameIDs(url):
    """ Given a single day base url return a list of urls to individual games that will be parsed """
    f = urlopen(url + '/master_scoreboard.xml')
    data = f.read()
    f.close()

    root = ET.fromstring(data)

    base = 'http://gd2.mlb.com'
    
    return [base + c.attrib['game_data_directory'] for c in root]
   

def parseBoxScore(url):
    """ Given a gameday url parse out desired stats from boxscore.xml"""
    f = urlopen(url + '/boxscore.xml')
    data = f.read()
    f.close()
    game_id = url[url.find('gid') : url.find('/box')]

    root = ET.fromstring(data)
    
    # store linescores as a string
    linescore = root.find('linescore')
    innings = list(linescore)
    LS = ''
    for i in innings:
        LS += i.attrib['away'] + i.attrib['home']
    
    # store overall game summary as dataframe
    game_summary = pd.DataFrame(root.attrib, index=[0])
    game_summary['game_id'].loc[0] = game_id
    
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
    """ Returns a base url for a given year, month, date combination"""

    base_url = 'http://gd2.mlb.com'
    return base_url + '/components/game/mlb/' + 'year_' + str(year) + '/month_' + str(month) + '/day_' + str(day)

year = 2017
month = '08'
day = 21



games_url = urlCombiner(year, month, day)
#get all games for a single day
all_games = getGameIDs(games_url)

#get all stats for a single day

summary, hitters, pitchers = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

for i in all_games:
    s, h, p = parseBoxScore(i)
    summary = pd.concat([summary, s])
    hitters = pd.concat([hitters, b])
    pitchers = pd.concat([pitchers, p])



