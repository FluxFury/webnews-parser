import random
from urllib.parse import urljoin

from scrapy import Request, Spider

from webnews_parser.settings import PLAYWRIGHT_ARGS, PLAYWRIGHT_USER_AGENTS
from webnews_parser.utils.db_utils import poll_cs2_matches

from ..utils.spider_utils import css_mutator, extract_teams, xpath_mutator


class CSUpdateLiveScheduledMatchesSpider(Spider):
    name = "CSUpdateLiveScheduledMatchesSpider"
    custom_settings = {  # noqa: RUF012
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "webnews_parser.middlewares.PatchrightMiddleware": 542,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSUpdateLiveScheduledMatchesPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 0.5,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
    }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocked_resources = ["image", "font", "stylesheet"]
        self.browser_args = PLAYWRIGHT_ARGS
        self.user_agent = random.choice(PLAYWRIGHT_USER_AGENTS)


    def start_requests(self):
        matches = poll_cs2_matches()
        for match in matches:
            if match.match_url:
                yield Request(
                    url=match.match_url,
                    callback=self.parse_match,
                    cb_kwargs={"match_id": match.match_id},
                    meta={"delay": 4}
                )

    def parse_match(self, response, match_id, retry_times=0):
        """Parse match details for updating."""
        match_status = self._get_match_status(response)
        retry_times = response.meta.get("retry_times", 0)
        team_scores = response.xpath('//div[contains(@class, "score")]/span[contains(@class, "live")]/text()').getall()
        if (not team_scores or not match_status) and retry_times < 3:
            yield Request(url=response.url,
                    callback=self.parse_match,
                    cb_kwargs={"match_id": match_id, "retry_times": retry_times + 1},
                    meta={"delay": 4},
                    dont_filter=True)
            return
        pretty_team_names = response.xpath('//div[contains(@class, "teams-on-live")]//h2/text()').getall()
        team_names = extract_teams(response.url)
        pretty_match_name = " - ".join([team.strip() for team in pretty_team_names])
        
        # Fix match format extraction
        match_format = xpath_mutator('//div[contains(@class, "score")]/h3/text()', response)
        clean_match_format = match_format.replace(",", "").strip() if match_format else "Best of 1"

        team1_score = team_scores[0]
        team2_score = team_scores[1]
        tournament_url = urljoin(base="https://escorenews.com", url=response.xpath("//h1//a/@href").get())
        team_urls = response.xpath('//div[contains(@class, "teams-on-live")]/span/a/@href').getall()
        team1_url = urljoin(base="https://escorenews.com", url=team_urls[0]) if team_urls else None
        team2_url = urljoin(base="https://escorenews.com", url=team_urls[1]) if len(team_urls) > 1 else None
        match_data = {
            "match_id": match_id,
            "pretty_match_name": pretty_match_name,
            "match_status": match_status,
            "pretty_team1_name": pretty_team_names[0],
            "pretty_team2_name": pretty_team_names[1],
            "team1_name": team_names[0],
            "team2_name": team_names[1],
            "team1_score": team1_score,
            "team2_score": team2_score,
            "team1_url": team1_url,
            "team2_url": team2_url,
            "match_format": clean_match_format,
            "match_streams": self._parse_streams(response),
            "tournament_url": tournament_url
        }
        yield match_data

    def _get_match_status(self, response):
        status = response.xpath('//div[contains(@class, "score")]//b/text()').get()
        if status in {"Match did not start", "Is the 3rd round"}:
            return "scheduled"
        if status == "Match started":
            return "live"
        if status == "Match ends":
            return "finished"
        return status

    def _parse_streams(self, response):
        streams = {}
        for stream_info in response.css("div.os-padding div.si"):
            stream_name = css_mutator("b::text", stream_info).strip()
            stream_author = stream_info.css("u::text").get().strip().split()[-1]
            stream_language = stream_info.css("u::text").get().strip().split()[-2]
            stream_viewers = stream_info.css("u i::text").get()
            streamer_twitch_name = stream_info.css("::attr(data-eng)").get()
            stream_link = f"https://www.twitch.tv/{streamer_twitch_name}" if streamer_twitch_name else ""
            
            streams[stream_name] = (stream_author, stream_language, stream_viewers, stream_link)
        return streams
