# functions to parse mlbgameday xml data
# The design of this could(should) definitely be improved,
# but I'm just looking to scrape data
# Created: 12/14/17
from urllib2 import urlopen
from sets import Set
from datetime import date, timedelta, datetime
from time import time
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
        for a, b in enumerate(list(i)):
            if i.tag == 'batting':
                batting.append(b.attrib)
            elif i.tag == 'pitching':
                if a == 0:
                    # flag starting pitcher
                    b.attrib['SP'] = 1
                else:
                    # not a starting pitcher
                    b.attrib['SP'] = 0
                pitching.append(b.attrib)

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


def appendQS(pitchers):
    """ Append quality start to pitching stats
        Input: Pitchers data frame
        Output: Same dataframe with a quality start column"""
    pitchers['Quality_Start'] = (pitchers.er <= 3) & (pitchers.out >= 18) & (pitchers.SP)
     
    return pitchers


def getPlayerInfo(game_url, gameDF, unique, isHitter):
    """ Pull some player info, populates a unique table, if its been seen before it won't pull that player
        Input: URL containing the base gameday directory
               Single game data frame containing players from that game
               Hash set containing previously seen players
               Hitter/Pitcher flag 
        Output: DataFrame containing bios of (only) the new unique players seen
                Updated HashSet """

    playerInfo = pd.DataFrame()

    players = gameDF.id
    newPlayers = [i for i in players if i not in unique]
    for player in newPlayers:
        unique.add(player)
        if isHitter:
            f = urlopen(game_url + '/batters/' + str(player) + '.xml')
        else:
            f = urlopen(game_url + '/pitchers/' + str(player) + '.xml')
        data = f.read()
        f.close()
        
        root = ET.fromstring(data)

        newInfo = pd.DataFrame(root.attrib, index=[0])

        playerInfo = pd.concat([playerInfo, newInfo])
    
    playerInfo.reset_index(inplace=True)

    return playerInfo, unique


def parseDate(x):
    """Pandas map function to convert birthday from string to datetime object"""
    return datetime.strptime(x, '%m/%d/%Y')


def toNumeric(x):
    """ Helper function to catch 'null' values in xml data"""
    try:
        ret = pd.to_numeric(x)
    except ValueError:
        ret = x
    return ret


def enrichBoxScore(box, events):
    """Pull data from events DF and add to box score DF """
        
    return None


### pandas map functions to cast strings to int/floats where appropriate
### Test Script ### - Eventually just functions

t0_2017 = date(2017, 4, 2)
tf_2017 = date(2017, 4, 9)
tDelta = tf_2017 - t0_2017

#get all days in a season as a list of URL directories
all_days = getSeasonDays(t0_2017, tf_2017)

#get a list of lists representing all gameday directories
all_games = [getGameIDs(i) for i in all_days]

#flatten list
flat_all_games = [item for sublist in all_games for item in sublist]

#get all stats for a single day

summary, hitters, pitchers, events, bio = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
unique_plyr = set()
t0 = time()
for i in flat_all_games:
    print i
    s, h, p = parseBoxScore(i)
    # if there was an issue pulling data, skip to next game
    if (s is None) or (h is None) or (p is None):
        continue

    ev = parseEvents(i)
    # pull player info without duplicates, this can be used as a map b/w id and names
    hitter_info, unique_plyr = getPlayerInfo(i, h, unique_plyr, True)
    pitcher_info, unique_plyr = getPlayerInfo(i, p, unique_plyr, False)

    summary = pd.concat([summary, s])
    hitters = pd.concat([hitters, h])
    pitchers = pd.concat([pitchers, p])
    events = pd.concat([events, ev])
    bio = pd.concat([bio, hitter_info, pitcher_info])
    print time() - t0
    t0 = time()

#reset index     
summary.reset_index(inplace=True)
hitters.reset_index(inplace=True)
pitchers.reset_index(inplace=True)
events.reset_index(inplace=True)
bio.reset_index(inplace=True)

#convert strings to numeric
toNum_pitchers = ['bb', 'bf', 'bs', 'er', 'era', 'game_score', 'h', 'hld', 'hr', 'id', 'l', 'np', 'out',
                  'r', 's', 's_bb', 's_er', 's_h', 's_ip', 's_r', 's_so', 'so', 'sv', 'w' ]
toNum_hitters = ['a', 'ab', 'ao', 'avg', 'bb', 'bo','cs', 'd', 'e','fldg', 'gidp', 'go', 'h', 'hbp', 'hr', 'id',
                 'lob', 'obp', 'ops', 'po', 'r', 'rbi', 's_bb', 's_h', 's_hr', 's_r', 's_rbi', 's_so', 'sac', 'sb',
                 'sf', 'slg', 'so', 't']
toNum_summary = ['away_id', 'away_loss', 'away_wins', 'game_pk', 'home_id', 'home_loss', 'home_wins', 'venue_id']
toNum_events = ['ab_num', 'b', 's', 'batter', 'event_num', 'o', 'pitch_speed', 'pitcher']
toNum_bio = ['id', 'jersey_number', 'weight']

hitters[toNum_hitters] = hitters[toNum_hitters].apply(toNumeric)
summary[toNum_summary] = summary[toNum_summary].apply(toNumeric)
pitchers[toNum_pitchers] = pitchers[toNum_pitchers].apply(toNumeric)
events[toNum_events] = events[toNum_events].apply(toNumeric)
bio[toNum_bio] = bio[toNum_bio].apply(toNumeric)
bio['dob_reformat'] = bio['dob'].apply(parseDate)

#add quality start label
pitchers = appendQS(pitchers)




















