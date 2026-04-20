#!/usr/bin/env python3
"""
Скрипт для настройки аутентификации VK.

Поддерживает два режима:
  1. Автоматический — локальный HTTP-сервер перехватывает токен из redirect.
     Требуется: в настройках VK-приложения redirect_uri = http://localhost:18181/callback
  2. Ручной — пользователь копирует токен из адресной строки браузера (fallback).

Для Standalone-приложений VK токены живут долго (месяцы).
Для плагин-приложений токены живут ~24 часа.
"""

import os
import sys
import json
import time
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from dotenv import load_dotenv

# ─── Порт локального сервера ────────────────────────────────────────────────
LOCAL_PORT = 18181
LOCAL_CALLBACK = f"http://localhost:{LOCAL_PORT}/callback"

# ─── Права доступа (scope) ──────────────────────────────────────────────────
# Standalone: все права доступны
# Плагин: только video, groups (wall/audio/photos — заблокированы)
SCOPE = "groups,video,wall,audio,photos,offline"

# ─── Глобальная переменная для передачи токена из хэндлера ──────────────────
_captured_token = None


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP-обработчик для перехвата OAuth redirect от VK."""

    def do_GET(self):
        global _captured_token

        parsed = urlparse(self.path)

        # VK Implicit Flow: token передаётся в fragment (#access_token=...)
        # Некоторые браузеры НЕ отправляют fragment на сервер.
        # Поэтому показываем страницу с JS, которая извлечёт token и отправит POST.
        if parsed.path == "/callback":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self._serve_js_extractor()
            return

        # POST /callback — JS-страница отправляет extracted token сюда
        if parsed.path == "/callback" and self.command == "POST":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            params = parse_qs(body)
            token = params.get("access_token", [None])[0]
            user_id = params.get("user_id", [None])[0]
            expires_in = params.get("expires_in", [None])[0]

            if token:
                _captured_token = {
                    "access_token": token,
                    "user_id": user_id,
                    "expires_in": expires_in,
                    "timestamp": time.time(),
                }
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("""
                <html><body style="font-family:sans-serif;text-align:center;padding:50px">
                <h1 style="color:#4CAF50">✅ Токен получен!</h1>
                <p>Можно закрыть эту вкладку и вернуться в терминал.</p>
                <script>window.close();</script>
                </body></html>
                """.encode("utf-8"))
            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"No access_token in request")
            return

        # Корневая страница — informational
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"VK Auth Callback Server is running. Waiting for OAuth redirect...")

    def _serve_js_extractor(self):
        """Отправляет JS-страницу, которая извлекает token из URL fragment
        и отправляет его на сервер через POST."""
        self.wfile.write(f"""
<!DOCTYPE html>
<html>
<head><title>VK Authorization</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px">
<p>🔄 Получение токена...</p>
<script>
(function() {{
    var hash = window.location.hash.substring(1);
    var params = new URLSearchParams(hash);
    var token = params.get('access_token');
    var user_id = params.get('user_id');
    var expires_in = params.get('expires_in');

    if (token) {{
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/callback', true);
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        xhr.send('access_token=' + encodeURIComponent(token) +
                 '&user_id=' + encodeURIComponent(user_id || '') +
                 '&expires_in=' + encodeURIComponent(expires_in || ''));
        xhr.onload = function() {{
            document.body.innerHTML = '<h1 style="color:#4CAF50">✅ Токен получен!</h1>' +
                '<p>Можно закрыть эту вкладку и вернуться в терминал.</p>';
            try {{ window.close(); }} catch(e) {{}}
        }};
    }} else {{
        // Нет токена в fragment — возможно, это ошибка VK
        var error = params.get('error');
        var desc = params.get('error_description');
        document.body.innerHTML = '<h1 style="color:#f44336">❌ Ошибка авторизации</h1>' +
            '<p>' + (error || 'Неизвестная ошибка') + '</p>' +
            '<p>' + (desc || '') + '</p>' +
            '<p>Попробуйте запустить скрипт с параметром <code>--manual</code></p>';
    }}
}})();
</script>
</body>
</html>
""".encode("utf-8"))

    def log_message(self, format, *args):
        """Подавляем стандартные HTTP-логи."""
        pass


def start_local_server(port: int):
    """Запускает HTTP-сервер в фоне."""
    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.timeout = 1
    server.serve_forever()
    return server


def obtain_token_auto(config_file: str, client_id: str) -> dict:
    """
    Автоматический режим: запускает локальный сервер, открывает браузер,
    ждёт пока VK редиректнет на localhost с токеном.

    Требует: redirect_uri в VK-приложении = http://localhost:18181/callback
    """
    global _captured_token

    print(f"\n🌐 Автоматический режим (localhost:{LOCAL_PORT})")
    print(f"   redirect_uri должен быть: {LOCAL_CALLBACK}")
    print()

    # Запускаем сервер в фоне
    server_thread = threading.Thread(
        target=start_local_server, args=(LOCAL_PORT,), daemon=True
    )
    server_thread.start()
    time.sleep(0.3)  # Даём серверу стартовать

    # Формируем OAuth URL с нашим redirect_uri
    auth_url = (
        f"https://oauth.vk.com/authorize?"
        f"client_id={client_id}&"
        f"display=page&"
        f"redirect_uri={LOCAL_CALLBACK}&"
        f"scope={SCOPE}&"
        f"response_type=token&"
        f"v=5.131"
    )

    print("🌐 Открываем браузер для авторизации...")
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"⚠️  Не удалось открыть браузер: {e}")
        print(f"Откройте URL вручную:\n{auth_url}")

    print("\n⏳ Ожидаем токен (нажмите Ctrl+C для отмены)...")
    print("   (после авторизации в VK вкладка закроется автоматически)")

    # Ждём токен с таймаутом
    deadline = time.time() + 120  # 2 минуты
    try:
        while time.time() < deadline:
            if _captured_token:
                return _captured_token
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\n❌ Отменено пользователем.")

    return None


def obtain_token_manual(client_id: str) -> dict:
    """
    Ручной режим: пользователь копирует токен из адресной строки браузера.
    """
    redirect_uri = "https://oauth.vk.com/blank.html"

    auth_url = (
        f"https://oauth.vk.com/authorize?"
        f"client_id={client_id}&"
        f"display=page&"
        f"redirect_uri={redirect_uri}&"
        f"scope={SCOPE}&"
        f"response_type=token&"
        f"v=5.131"
    )

    print("\n🌐 Ручной режим")
    print(f"URL: {auth_url}")
    print()

    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"⚠️  Не удалось открыть браузер: {e}")

    print("📋 Инструкции:")
    print("1. Войдите в свой аккаунт VK")
    print("2. Разрешите доступ приложению")
    print("3. В адресной строке появится URL вида:")
    print("   https://oauth.vk.com/blank.html#access_token=ТОКЕН&...")
    print("4. Скопируйте значение access_token (только сам токен, без # и прочего)")
    print()

    access_token = input("🔑 Введите токен доступа: ").strip()
    if not access_token:
        return None

    return {
        "access_token": access_token,
        "user_id": None,
        "expires_in": None,
        "timestamp": time.time(),
    }


def save_token(token_data: dict, group_id: str, config_file: str):
    """Сохраняет токен в файл и проверяет его."""
    token_data["group_id"] = group_id

    token_file = os.getenv("VK_TOKEN_PATH", "vk_token.json")

    with open(token_file, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Токен сохранён в {token_file}")

    # Проверяем токен
    print("\n🔍 Проверка токена...")
    from publishers.vk_publisher import VKPublisher

    publisher = VKPublisher(config_file)
    if publisher.authenticate():
        print("✅ Аутентификация успешна!")

        # Показываем сколько живёт токен
        expires_in = token_data.get("expires_in")
        if expires_in:
            hours = int(expires_in) // 3600
            print(f"⏰ Токен действителен ~{hours} ч.")

        if group_id:
            group_info = publisher.get_group_info()
            if group_info:
                print(f"📊 Группа: {group_info['name']} (ID: {group_info['id']})")
                print(f"👥 Участников: {group_info['members_count']}")
    else:
        print("❌ Ошибка аутентификации")
        return False

    return True


def main():
    """Основная функция настройки VK аутентификации"""

    manual_mode = "--manual" in sys.argv

    # Загружаем конфигурацию
    config_file = "config.publisher.env"
    if Path(config_file).exists():
        load_dotenv(config_file)

    client_id = os.getenv("VK_CLIENT_ID", "52506614")
    client_secret = os.getenv("VK_CLIENT_SECRET", "")

    print("🔧 Настройка VK аутентификации")
    print("=" * 50)
    print(f"📱 Client ID: {client_id}")
    if client_secret:
        print(f"🔑 Client Secret: {'*' * len(client_secret)}")
        print("   Тип: Standalone-приложение (токен живёт долго)")
    else:
        print("🔑 Client Secret: НЕ УКАЗАН")
        print("   Тип: Плагин-приложение (токен ~24 часа)")
        print()
        print("   💡 Для Standalone-приложения:")
        print("   1. Зайдите в https://vk.com/editapp?id=" + client_id)
        print("   2. В 'Настройках' укажите 'Тип: Standalone'")
        print("   3. Добавьте redirect_uri: " + LOCAL_CALLBACK)
        print("   4. Получите Client Secret")
        print("   5. Добавьте в config.publisher.env:")
        print(f"      VK_CLIENT_SECRET=ваш_секретный_ключ")

    # Получаем токен
    token_data = None

    if manual_mode:
        token_data = obtain_token_manual(client_id)
    else:
        # Пытаемся автоматический режим
        token_data = obtain_token_auto(config_file, client_id)

        if not token_data:
            print("\n⚠️  Автоматический режим не сработал.")
            print("   Возможные причины:")
            print(f"   • redirect_uri в VK-приложении не настроен на {LOCAL_CALLBACK}")
            print("   • VK заблокировал popup")
            print("   • Пользователь отменил авторизацию")
            print()

            fallback = input("Попробовать ручной режим? (Y/n): ").strip()
            if fallback.lower() != "n":
                token_data = obtain_token_manual(client_id)

    if not token_data:
        print("\n❌ Не удалось получить токен")
        return 1

    # Запрашиваем ID группы (опционально)
    group_id = os.getenv("VK_GROUP_ID", "")
    if not group_id:
        group_id = input("\n👥 Введите ID группы для публикации (опционально, Enter для пропуска): ").strip()

    # Сохраняем
    if not save_token(token_data, group_id, config_file):
        return 1

    print("\n🎉 Настройка VK аутентификации завершена!")
    print("\n📝 Примеры использования:")
    print("python publisher.py pipeline_dir --platforms vk")
    print("python publisher.py pipeline_dir --platforms vk --dry-run")
    print("\n💡 Для обновления токена в будущем:")
    print("   python setup_vk_auth.py          # автоматический режим")
    print("   python setup_vk_auth.py --manual  # ручной режим")

    return 0


if __name__ == "__main__":
    exit(main())
