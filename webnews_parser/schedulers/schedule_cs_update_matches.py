from webnews_parser.scheduler import load_environment, schedule_update_matches_spider

if __name__ == "__main__":
    load_environment()
    job_id = schedule_update_matches_spider()
    print(job_id)
