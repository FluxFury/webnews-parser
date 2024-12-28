from datetime import datetime

from itemloaders.processors import Identity, MapCompose, TakeFirst
from scrapy.loader import ItemLoader


def parse_datetime(datetime_str: str) -> datetime:
    """Convert datetime string to datetime object without timezone."""
    try:
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # For dates without time
        return datetime.strptime(datetime_str.split()[0], "%Y-%m-%d")


def process_age(value: str) -> str | None:
    """Process age value, handling special characters."""
    if not value or value == "–" or value == "-":
        return None
    return value


def parse_unix_timestamp(timestamp_str: str) -> datetime:
    """Convert unix timestamp string to datetime object."""
    try:
        return datetime.fromtimestamp(int(timestamp_str) / 1000)  # Convert milliseconds to seconds
    except (ValueError, TypeError):
        return None


class CSCreateLiveScheduledMatchesLoader(ItemLoader):
    default_output_processor = TakeFirst()
    
    planned_start_datetime_in = MapCompose(parse_datetime)
    match_name_in = MapCompose(str.strip)
    match_url_in = MapCompose(str.strip)
    external_id_in = MapCompose(str.strip)


class CSUpdateTournamentsLoader(ItemLoader):
    default_output_processor = TakeFirst()
    
    tournament_name_in = MapCompose(str.strip)
    tournament_location_in = MapCompose(str.strip)
    tournament_logo_link_in = MapCompose(str.strip)
    tournament_description_in = MapCompose(str.strip)
    tournament_start_date_in = MapCompose(parse_datetime)
    tournament_prize_pool_in = MapCompose(str.strip)


class CSTeamsItemLoader(ItemLoader):
    default_output_processor = TakeFirst()
    
    team_pretty_name_in = MapCompose(str.strip)
    team_name_in = MapCompose(str.strip)
    team_page_link_in = MapCompose(str.strip)
    team_logo_link_in = MapCompose(str.strip)
    team_region_in = MapCompose(str.strip)


class CSPlayersItemLoader(ItemLoader):
    default_output_processor = TakeFirst()
    
    player_nickname_in = MapCompose(str.strip)
    player_name_in = MapCompose(str.strip)
    player_team_in = MapCompose(str.strip)
    player_age_in = MapCompose(str.strip, process_age)
    player_country_in = MapCompose(str.strip)
    player_played_games_last_year_in = MapCompose(str.strip)
    player_played_games_overall_in = MapCompose(str.strip)


class CSNewsItemLoader(ItemLoader):
    default_output_processor = TakeFirst()
    
    header_in = MapCompose(str.strip)
    text_out = Identity()
    url_in = MapCompose(str.strip)
    news_creation_time_in = MapCompose(str.strip, parse_unix_timestamp)


class CSPMatchesItemLoader(ItemLoader):
    default_output_processor = TakeFirst()
    
    date_in = MapCompose(str.strip, parse_datetime)
    team1_in = MapCompose(str.strip)
    team1_score_in = MapCompose(str.strip)
    team2_score_in = MapCompose(str.strip)
    team2_in = MapCompose(str.strip)
