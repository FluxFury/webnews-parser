from webnews_parser.main import scrapyd


def schedule_spider(spider_name: str, project_name: str = "webnews_parser", **kwargs) -> str:
    """
    Schedule a spider to run.
    
    Args:
        spider_name: Name of the spider to schedule.
        project_name: Name of the project (default: "webnews_parser").
        **kwargs: Additional keyword arguments to pass to the spider.
    
    Returns:
        str: Job ID of the scheduled spider.

    """
    job_id = scrapyd.schedule(
        project_name,
        spider_name,
        **kwargs
    )
    return job_id




def schedule_news_spider() -> str:
    """Schedule the CS News spider."""
    return schedule_spider("CSNewsSpider")


def schedule_teams_spider() -> str:
    """Schedule the CS Teams spider."""
    return schedule_spider("CSTeamsSpider")


def schedule_players_spider() -> str:
    """Schedule the CS Players spider."""
    return schedule_spider("CSPlayersSpider")


def schedule_past_matches_spider() -> str:
    """Schedule the CS Past Matches spider."""
    return schedule_spider("CSpMatchesSpider")


def schedule_create_matches_spider() -> str:
    """Schedule the CS Create Matches spider."""
    return schedule_spider("CSCreateLiveScheduledMatchesSpider")


def schedule_update_tournaments_spider() -> str:
    """Schedule the CS Update Tournaments spider."""
    return schedule_spider("CSUpdateTournamentsSpider")


def schedule_update_matches_spider() -> str:
    """Schedule the CS Update Matches spider."""
    return schedule_spider("CSUpdateLiveScheduledMatchesSpider")

