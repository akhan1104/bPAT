# Player Stat Scrape Class
# Created 05/17/17
import bs4 as bs
import requests
import pandas as pd
import numpy as np


class Scraper:
	# class designed to rip career matchup stats from www.retrosheet.org
    def __init__(self, player, isPitcher):
    	self.pitcher = isPitcher
        self.matchups = []
        self.player = player
        # player list: first, last
        assert(len(player) == 2)
        self.player_id = self.get_player_id()
    

    def get_player_id(self):
        # Find player ID from retrosheet
        site = requests.get('http://www.retrosheet.org/retroID.htm')
        src = site.content
        soup = bs.BeautifulSoup(src, 'lxml')
        all_players = soup.pre.get_text().splitlines()

        found = [s for s in all_players if self.player[-1].lower() in s.lower() and self.player[0].lower() in s.lower()]
        player_id = found[0].split(',')[-2].encode('ascii','replace')

        return player_id


    def get_matchups(self):
    	import re
    	# function to return matchups as pandas DF
    	# setup beautifulsoup
    	url = 'http://www.retrosheet.org/boxesetc/' + self.player_id[0] + '/MU1_' + self.player_id + '.htm'
    	site = requests.get(url)
    	src = site.content
    	soup = bs.BeautifulSoup(src, 'lxml')

    	# parse tags
    	pre_tag = soup.find_all('pre')[-1]
    	stats = pre_tag.get_text().splitlines()

    	# convert to strings
    	stats = [s.encode('ascii', 'replace') for s in stats] 

    	# extract column names for pandas
    	cols = [s for s in stats[0].split(' ') if s != '']
    	cols = ['First', 'Last'] + cols[1:]

    	# edit lists to make parsing easier
    	strip = [t.split(' ') for t in stats]
        st = [[s for s in t1 if s != ''] for t1 in strip]
        
        # remove extra column IDs
        st = [s for s in st if s[0] != 'Batter']

		# convert to floats
        st = [t1[:3] + [float(s) for s in t1 if check_float(s) ] for t1 in st]

        df = pd.DataFrame(st)
        df.columns = cols
        
        return df
        

def check_float(s):
    try:
        float(s)
    except ValueError:
        return False
    return True





    
