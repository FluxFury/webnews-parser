from webnews_parser.schedulers.scheduler import (
    load_environment,
    schedule_update_tournaments_spider,
)

if __name__ == "__main__":
    load_environment()
    job_id = schedule_update_tournaments_spider()
    print(job_id)
