from webnews_parser.scheduler import load_environment, schedule_players_spider

if __name__ == "__main__":
    load_environment()
    job_id = schedule_players_spider()
    print(job_id)
