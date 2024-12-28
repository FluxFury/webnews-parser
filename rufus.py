import random
import signal
import sys
import time

from patchright.sync_api import sync_playwright

PLAYWRIGHT_USER_AGENT = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"]


def main():
    # Инициализация Playwright
    with sync_playwright() as p:
        # Запуск браузера Chromium
        browser = p.chromium.launch(
            headless=False,  # Установите в False, если хотите видеть браузер
            channel="chromium"
        )
        context = browser.new_context(user_agent=random.choice(PLAYWRIGHT_USER_AGENT),
                                            locale="en-US",
                                            no_viewport=True,
                                            )
        page = context.new_page()
        print("Браузер запущен. Нажмите Ctrl+C для выхода.")

        # Обработчик сигналов для корректного завершения
        def shutdown_handler(sig, frame):
            print("\nПолучен сигнал завершения. Закрытие браузера...")
            browser.close()
            print("Браузер закрыт.")
            sys.exit(0)

        # Регистрация обработчиков сигналов SIGINT и SIGTERM
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        try:
            # Бесконечный цикл с паузой, ожидающий сигнала завершения
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # Дополнительная обработка на случай, если сигнал не был пойман
            shutdown_handler(None, None)

if __name__ == "__main__":
    main()
