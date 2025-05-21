import pathlib

from dotenv import load_dotenv

from os import getenv

from scrapyd_api import ScrapydAPI  # type: ignore

def load_environment(env_file: str = ".env") -> None:
    """
    Load environment variables from the specified file.
    
    Args:
        env_file: Name of the environment file to load.
        
    """
    path_to_env = pathlib.Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=path_to_env / env_file, override=True)



load_environment()


scrapyd = ScrapydAPI(getenv("SCRAPYD_URL"))