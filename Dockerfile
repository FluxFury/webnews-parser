FROM scrapinghub/splash

COPY adblock_rules.txt /etc/splash/adblock_rules.txt

CMD ["--filters-path=/etc/splash/adblock_rules.txt"]
