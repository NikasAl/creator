import asyncio
import uuid
import argparse
import requests
import os
import subprocess
import sys
from dotenv import load_dotenv

# === Загрузка переменных окружения ===
load_dotenv('config.env')

AUTHORIZATION_KEY = os.getenv("SBER_SPEECH_KEY")

if not AUTHORIZATION_KEY:
    raise ValueError("❌ Не найден SBER_SPEECH_KEY в config.env")

# === Аргументы командной строки ===
def parse_args():
    parser = argparse.ArgumentParser(description="Асинхронный синтез речи через SaluteSpeech API")
    parser.add_argument("text_file", help="Путь к текстовому файлу для синтеза")
    parser.add_argument("--voice", default="Bys_24000", help="Голос для синтеза (по умолчанию: Bys_24000)")
    parser.add_argument("--output", default="audio.mp3", help="Имя выходного аудиофайла (по умолчанию: audio.mp3)")
    return parser.parse_args()

# === 1. Получение Access Token ===
def get_access_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {AUTHORIZATION_KEY}"
    }
    data = {"scope": "SALUTE_SPEECH_PERS"}
    
    try:
        response = requests.post(
            url,
            headers=headers,
            data=data,
            verify="/etc/ssl/certs/ca-certificates.crt"
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        print("✅ Access token получен.")
        return token
    except Exception as e:
        print("❌ Ошибка получения токена:", e)
        if 'response' in locals():
            print("Ответ сервера:", response.text)
        return None

# === 2. Загрузка текста через data:upload ===
def upload_text_data(token, text):
    url = "https://smartspeech.sber.ru/rest/v1/data:upload"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    files = {"file": ("text.txt", text.encode("utf-8"), "text/plain")}
    
    try:
        response = requests.post(
            url,
            headers=headers,
            files=files,
            verify="/etc/ssl/certs/ca-certificates.crt"
        )
        response.raise_for_status()
        result = response.json()["result"]
        request_file_id = result["request_file_id"]
        print(f"✅ Текст загружен. request_file_id: {request_file_id}")
        return request_file_id
    except Exception as e:
        print("❌ Ошибка загрузки текста:", e)
        if 'response' in locals():
            print("Ответ сервера:", response.text)
        return None

# === 3. Запуск асинхронной задачи синтеза ===
def start_synthesis_task(token, request_file_id, voice):
    url = "https://smartspeech.sber.ru/rest/v1/text:async_synthesize"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Request-ID": str(uuid.uuid4())
    }
    payload = {
        "request_file_id": request_file_id,
        "audio_encoding": "Opus",
        "voice": voice
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            verify="/etc/ssl/certs/ca-certificates.crt"
        )
        response.raise_for_status()
        result = response.json()["result"]
        task_id = result["id"]
        print(f"🚀 Асинхронная задача на синтез создана. ID задачи: {task_id}")
        return task_id
    except Exception as e:
        print("❌ Ошибка запуска задачи синтеза:", e)
        if 'response' in locals():
            print("Ответ сервера:", response.text)
        return None

# === 4. Проверка статуса задачи ===
def get_task_status(token, task_id):
    url = "https://smartspeech.sber.ru/rest/v1/task:get"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": str(uuid.uuid4()),
        "Accept": "application/octet-stream"
    }
    params = {"id": task_id}
    
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            verify="/etc/ssl/certs/ca-certificates.crt"
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Проверяем HTTP-статус в теле
        if data.get("status") != 200:
            print(f"❌ Ошибка в ответе: статус {data.get('status')}")
            return "ERROR", data

        result = data.get("result")
        if not result:
            print("❌ Поле 'result' отсутствует в ответе")
            return "ERROR", data

        task_status = result.get("status")
        valid_statuses = ["NEW", "RUNNING", "DONE", "CANCELED", "ERROR"]
        
        if task_status in valid_statuses:
            print(f"📊 Статус задачи: {task_status}")
            return task_status, data
        else:
            print(f"⚠️ Неизвестный статус задачи: {task_status}")
            return "ERROR", data
            
    except Exception as e:
        print("❌ Ошибка проверки статуса задачи:", e)
        if 'response' in locals():
            print("Код ответа:", response.status_code)
            print("Ответ сервера:", response.text)
        return "ERROR", {}

# === 5. Скачивание результата ===
def download_result(token, result_id, output_file):
    url = "https://smartspeech.sber.ru/rest/v1/data:download"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": str(uuid.uuid4())
    }
    params = {"response_file_id": result_id}
    
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            stream=True,
            verify="/etc/ssl/certs/ca-certificates.crt"
        )
        response.raise_for_status()
        
        temp_file = output_file + ".temp.opus"
        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Результат загружен как временный Opus: {temp_file}")

        # Конвертируем в нужный формат
        if output_file.endswith(".wav"):
            convert_opus_to_wav(temp_file, output_file)
            os.remove(temp_file)
            print(f"✅ Аудио сохранено как WAV: {output_file}")
        elif output_file.endswith(".mp3"):
            convert_opus_to_mp3(temp_file, output_file)
            os.remove(temp_file)
            print(f"✅ Аудио сохранено как MP3: {output_file}")
        else:
            os.rename(temp_file, output_file)
            print(f"✅ Аудио сохранено как Opus: {output_file}")

        return True
    except Exception as e:
        print("❌ Ошибка загрузки результата:", e)
        return False

# === Конвертация Opus → WAV ===
def convert_opus_to_wav(opus_path, wav_path):
    try:
        subprocess.run([
            "ffmpeg", "-i", opus_path,
            "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1", "-y",
            wav_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Конвертировано в WAV: {wav_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения ffmpeg (WAV): {e}")
        raise
    except FileNotFoundError:
        print("❌ Не найден ffmpeg. Установите его: https://ffmpeg.org/")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка конвертации Opus → WAV: {e}")
        raise

# === Конвертация Opus → MP3 ===
def convert_opus_to_mp3(opus_path, mp3_path):
    try:
        subprocess.run([
            "ffmpeg", "-i", opus_path,
            "-vn", "-ar", "24000", "-ac", "1", "-b:a", "128k", "-y",
            mp3_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Конвертировано в MP3: {mp3_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения ffmpeg (MP3): {e}")
        raise
    except FileNotFoundError:
        print("❌ Не найден ffmpeg. Установите его: https://ffmpeg.org/")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка конвертации Opus → MP3: {e}")
        raise

# === Основная логика ===
async def main():
    args = parse_args()

    # Проверка, существует ли ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("❌ ffmpeg не установлен. Требуется для конвертации аудио.")
        print("👉 Установите: https://ffmpeg.org/")
        sys.exit(1)

    # Чтение текста из файла
    try:
        with open(args.text_file, "r", encoding="utf-8") as f:
            text = f.read().strip()
        print(f"📄 Текст загружен из '{args.text_file}' ({len(text)} символов)")
        if len(text) == 0:
            print("❌ Текст пустой!")
            return
    except FileNotFoundError:
        print(f"❌ Файл '{args.text_file}' не найден.")
        return
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return

    # Шаг 1: Получение токена
    token = get_access_token()
    if not token:
        return

    # Шаг 2: Загрузка текста
    request_file_id = upload_text_data(token, text)
    if not request_file_id:
        return

    # Шаг 3: Запуск асинхронной задачи
    task_id = start_synthesis_task(token, request_file_id, args.voice)
    if not task_id:
        return

    # Шаг 4: Ожидание завершения задачи
    max_retries = 120
    result_id = None

    for _ in range(max_retries):
        status, task_info = get_task_status(token, task_id)
        
        if status == "DONE":
            # Извлекаем response_file_id — это ID аудиофайла
            response_file_id = task_info["result"].get("response_file_id")
            if response_file_id:
                result_id = response_file_id
                print(f"🎉 Задача завершена успешно. ID аудио: {result_id}")
                break  # ✅ Выходим из цикла
            else:
                print("❌ Поле 'response_file_id' отсутствует в ответе")
                return
        elif status == "ERROR":
            print("❌ Задача завершилась с ошибкой.")
            error_desc = task_info["result"].get("error", "Неизвестная ошибка")
            print(f"Описание: {error_desc}")
            return
        elif status == "CANCELED":
            print("❌ Задача отменена.")
            return
        else:
            await asyncio.sleep(3)
    else:
        print("⏰ Превышено время ожидания выполнения задачи.")
        return

    if not result_id:
        print("❌ Не удалось получить ID аудиофайла.")
        return

    # Шаг 5: Скачивание и конвертация
    download_result(token, result_id, args.output)

if __name__ == "__main__":
    asyncio.run(main())
