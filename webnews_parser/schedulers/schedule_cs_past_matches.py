from webnews_parser.schedulers.scheduler import (
    schedule_past_matches_spider,
)

if __name__ == "__main__":
    job_id = schedule_past_matches_spider()
    print(job_id)
