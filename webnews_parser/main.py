from scrapyd_api import ScrapydAPI  # type: ignore
from os import getenv

scrapyd = ScrapydAPI(getenv("SCRAPYD_URL"))