from webnews_parser.schedulers.scheduler import (
    schedule_teams_spider,
)

if __name__ == "__main__":
    job_id = schedule_teams_spider()
    print(job_id)
