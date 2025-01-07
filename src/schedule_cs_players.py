import pathlib

from dotenv import load_dotenv

path_to_env = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=path_to_env / ".env.local", override=True)

from webnews_parser.__main__ import scrapyd, settings

job_id = scrapyd.schedule(
    "webnews_parser",
    "CSPlayersSpider",
    setting=settings,
)

print(job_id)
