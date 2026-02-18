#!/usr/bin/env python3
"""
Генератор изображений через Together API (black-forest-labs/FLUX.1-schnell-Free)

- Читает ключ из переменной окружения TOGETHER_API_KEY (поддерживается загрузка через config.env/.env)
"""

import os
import base64
import json
import time
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv


@dataclass
class ImageParams:
    width: int = 1024
    height: int = 1024
    steps: int = 4
    seed: Optional[int] = None
    n: int = 1


class TogetherImageGenerator:
    def __init__(self, config_file: Optional[str] = None, model: str = "HiDream-ai/HiDream-I1-Dev"):
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            for env_name in [".env", "config.env", "settings.env"]:
                if Path(env_name).exists():
                    load_dotenv(env_name)
                    break

        self.api_key = os.getenv("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("Не найден TOGETHER_API_KEY в окружении/конфигурации")

        self.base_url = "https://api.together.xyz"
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # для троттлинга под 6 запросов в минуту: увеличим интервал и добавим джиттер
        self._last_request_ts: float = 0.0
        self._min_spacing_sec: float = 12.5  # базовый интервал между запросами
        self._timeout_sec: float = 180.0     # таймаут запроса

    def generate_image(self, prompt: str, negative_prompt: Optional[str] = None, params: Optional[ImageParams] = None) -> Dict[str, Any]:
        if params is None:
            params = ImageParams()

        # подгоняем размеры к кратности 16 (требование Together/модели)
        def m16(v: int) -> int:
            if v <= 0:
                return 16
            return max(16, (v // 16) * 16)

        # подгоняем размеры к кратности 64 (требование некоторых моделей Together/модели)
        def m64(v: int) -> int:
            if v <= 0:
                return 64
            return max(64, (v // 64) * 64)


#         adj_width = m16(params.width)
#         adj_height = m16(params.height)
        adj_width = m64(params.width)
        adj_height = m64(params.height)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "width": adj_width,
            "height": adj_height,
            "disable_safety_checker": True,
#             "steps": params.steps,
#             "n": params.n,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if params.seed is not None:
            payload["seed"] = params.seed

        # Эндпоинт генерации изображений для Together
        url = f"{self.base_url}/v1/images/generations"

        # Троттлинг: первый запрос — короткая пауза, далее — не чаще self._min_spacing_sec + джиттер
        now = time.time()
        if self._last_request_ts > 0:
            elapsed_since_last = now - self._last_request_ts
            jitter = random.uniform(0.5, 2.0)
            delay_needed = (self._min_spacing_sec + jitter) - elapsed_since_last
            if delay_needed > 0:
                time.sleep(delay_needed)
        else:
            time.sleep(2.0)

        # Ретраи с экспоненциальной паузой на 429
        attempts = 5
        backoff = 6.0  # секунд при 429, затем увеличиваем
        last_error_text = None
        for attempt in range(1, attempts + 1):
            start = time.time()
            try:
                resp = requests.post(url, headers=self.headers, json=payload, timeout=self._timeout_sec)
            except requests.exceptions.Timeout as e:
                self._last_request_ts = time.time()
                last_error_text = f"Timeout after {self._timeout_sec}s: {e}"
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 36.0)
                continue
            except requests.exceptions.RequestException as e:
                self._last_request_ts = time.time()
                last_error_text = f"Request error: {e}"
                time.sleep(3.0)
                continue

            self._last_request_ts = time.time()
            elapsed = self._last_request_ts - start

            if resp.status_code == 200:
                data = resp.json()
                # Возможные ключи: OpenAI-совместимые
                # data: [ { b64_json | url | image_base64 | base64 | image } ]
                images = data.get("data") or []
                if not images:
                    raise RuntimeError("Together API: пустой ответ (нет изображений)")

                img0 = images[0]
                b64_val = (
                    img0.get("b64_json")
                    or img0.get("image_base64")
                    or img0.get("base64")
                    or img0.get("image")
                )
                if not b64_val and img0.get("url"):
                    # Скачиваем по URL
                    url_img = img0["url"]
                    try:
                        rimg = requests.get(url_img, timeout=self._timeout_sec)
                        if rimg.status_code == 200:
                            return {
                                "bytes": rimg.content,
                                "raw": data,
                                "elapsed": elapsed,
                                "used_width": adj_width,
                                "used_height": adj_height,
                            }
                        else:
                            last_error_text = f"Image URL fetch error {rimg.status_code}: {rimg.text}"
                    except requests.exceptions.Timeout as e:
                        last_error_text = f"Image URL timeout after {self._timeout_sec}s: {e}"
                    except requests.exceptions.RequestException as e:
                        last_error_text = f"Image URL request error: {e}"
                    else:
                        last_error_text = "Ответ не содержит base64 или url"
                if not b64_val and not img0.get("url"):
                    last_error_text = "Ответ не содержит base64 или url"
                if b64_val:
                    return {
                        "b64": b64_val,
                        "raw": data,
                        "elapsed": elapsed,
                        "used_width": adj_width,
                        "used_height": adj_height,
                    }

            elif resp.status_code == 429:
                # Лимит — ждём и пробуем снова
                last_error_text = resp.text
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 36.0)
                continue
            else:
                last_error_text = f"Together API error {resp.status_code}: {resp.text}"
                # на иные ошибки — небольшая пауза и повтор
                time.sleep(3.0)
                continue

        raise RuntimeError(last_error_text or "Together API: не удалось сгенерировать изображение")

    def generate_and_save(self, prompt: str, out_path: str, negative_prompt: Optional[str] = None,
                          params: Optional[ImageParams] = None) -> Dict[str, Any]:
        result = self.generate_image(prompt=prompt, negative_prompt=negative_prompt, params=params)
        # может прийти либо base64, либо готовые байты (если по URL скачали)
        if "b64" in result:
            img_bytes = base64.b64decode(result["b64"])
        elif "bytes" in result:
            img_bytes = result["bytes"]
        else:
            raise RuntimeError("Не удалось получить изображение из ответа Together")
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            f.write(img_bytes)

        meta = {
            "model": self.model,
            # фактически использованные размеры (уже кратные 16)
            "width": result.get("used_width"),
            "height": result.get("used_height"),
            "steps": (params.steps if params else 4),
            "seed": (params.seed if params else None),
            "elapsed": result.get("elapsed"),
            "output_path": str(out.resolve()),
        }
        return meta


__all__ = ["TogetherImageGenerator", "ImageParams"]


