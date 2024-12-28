playwright parsers

chmod +x /home/bobok/.virtualenvs/webnews-parser/lib/python3.12/site-packages/undetected_playwright/driver/node
chmod +x /home/bobok/.virtualenvs/webnews-parser/lib/python3.12/site-packages/undetected_playwright/driver/playwright.sh
playwright install chromium



source /home/bobok/.virtualenvs/webnews-parser/bin/activate
export DB_URL=postgres://postgres:postgres@172.22.144.1:5433/fluxbackend
export DB_URL=postgres://postgres:postgres@localhost:5432/fluxbackendwsl
