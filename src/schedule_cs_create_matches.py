
import pathlib

from dotenv import load_dotenv

from webnews_parser import settings

path_to_env = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=path_to_env / ".env.local", override=True)

from main import scrapyd

job_id = scrapyd.schedule(
    "webnews_parser",
    "CSCreateLiveScheduledMatchesSpider",
)

print(job_id)
