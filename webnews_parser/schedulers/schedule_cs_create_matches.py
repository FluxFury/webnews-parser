from webnews_parser.schedulers.scheduler import (
    schedule_create_matches_spider,
)

if __name__ == "__main__":
    job_id = schedule_create_matches_spider()
    print(job_id)
