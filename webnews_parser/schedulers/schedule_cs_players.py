from webnews_parser.schedulers.scheduler import (
    schedule_players_spider,
)

if __name__ == "__main__":
    job_id = schedule_players_spider()
    print(job_id)
