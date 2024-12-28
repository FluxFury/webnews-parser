# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Field, Item


class CSNewsItem(scrapy.Item):
    header = scrapy.Field()
    text = scrapy.Field()
    url = scrapy.Field()
    news_creation_time = scrapy.Field()


class CSLSMatchesTournamentsItem(scrapy.Item):
    tournament_format = scrapy.Field()
    tournament_stage = scrapy.Field()
    match_format = scrapy.Field()
    match_status = scrapy.Field()
    team1_page_link = scrapy.Field()
    team1_logo_link = scrapy.Field()
    team1 = scrapy.Field()
    team1_score = scrapy.Field()
    team2_score = scrapy.Field()
    team2 = scrapy.Field()
    team2_logo_link = scrapy.Field()
    team2_page_link = scrapy.Field()
    match_begin_time = scrapy.Field()
    match_streams = scrapy.Field()
    pretty_match_name = scrapy.Field()
    external_id = scrapy.Field()

    has_tournament_info = scrapy.Field()

    tournament_name = scrapy.Field()
    tournament_logo_link = scrapy.Field()
    tournament_start_date = scrapy.Field()
    tournament_prize_pool = scrapy.Field()
    tournament_location = scrapy.Field()
    tournament_description = scrapy.Field()


class CSPMatchesItem(scrapy.Item):
    date = scrapy.Field()
    team1 = scrapy.Field()
    team1_score = scrapy.Field()
    team2_score = scrapy.Field()
    team2 = scrapy.Field()
    match_name = scrapy.Field()
    external_id = scrapy.Field()


class CSPlayersItem(scrapy.Item):
    player_nickname = scrapy.Field()
    player_name = scrapy.Field()
    player_team = scrapy.Field()
    player_age = scrapy.Field()
    player_country = scrapy.Field()
    player_played_games_last_year = scrapy.Field()
    player_played_games_overall = scrapy.Field()
    player_status = scrapy.Field()
    team_member_url = scrapy.Field()
    image_url = scrapy.Field()


class CSTeamsItem(scrapy.Item):
    team_pretty_name = scrapy.Field()
    team_name = scrapy.Field()
    team_page_link = scrapy.Field()
    team_logo_link = scrapy.Field()
    team_region = scrapy.Field()
    stats = scrapy.Field()
    players = scrapy.Field()
    regalia = scrapy.Field()


class CSCreateLiveScheduledMatchesItem(Item):
    planned_start_datetime = Field()
    match_url = Field()
    match_name = Field()
    external_id = Field()
    match_status = Field()


class CSUpdateTournamentsItem(Item):
    match_id = Field()
    tournament_name = Field()
    tournament_location = Field()
    tournament_logo_link = Field()
    tournament_description = Field()
    tournament_start_date = Field()
    tournament_prize_pool = Field()

