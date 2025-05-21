from webnews_parser.schedulers.scheduler import (
    schedule_update_matches_spider,
)

if __name__ == "__main__":
    job_id = schedule_update_matches_spider()
    print(job_id)
