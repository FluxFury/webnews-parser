from webnews_parser.schedulers.scheduler import (
    schedule_news_spider,
)

if __name__ == "__main__":
    job_id = schedule_news_spider()
    print(job_id)
