from webnews_parser.schedulers.scheduler import (
    load_environment,
    schedule_news_spider,
)

if __name__ == "__main__":
    load_environment()
    job_id = schedule_news_spider()
    print(job_id)
