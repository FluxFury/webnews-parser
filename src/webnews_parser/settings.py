BOT_NAME = "CSSpider"

SPIDER_MODULES = ["webnews_parser.spiders"]
NEWSPIDER_MODULE = "webnews_parser.spiders"

CLOSESPIDER_TIMEOUT_NO_ITEM = 360


PLAYWRIGHT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
]

PLAYWRIGHT_ARGS = [
    "--window-size=1920,1080",
    "--disable-popup-blocking"
]

CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 8

DOWNLOAD_TIMEOUT = 180
RETRY_TIMES = 4
RETRY_WAIT_TIME = 20
RETRY_HTTP_CODES = [429, 400, 504, 500, 502, 503]

TELNETCONSOLE_ENABLED = False


AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 1
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 100
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = True


HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 429, 400]

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"


FEED_EXPORT_ENCODING = "utf-8"
