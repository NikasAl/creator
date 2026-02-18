#!/usr/bin/env python3
"""
Генератор видео из изображений и аудио с плавными эффектами камеры.
Создает MP4 с синхронизированными изображениями и аудио дорожкой.

Эффекты камеры:
- zoomIn/zoomOut: плавное приближение/отдаление
- pan: плавное смещение камеры по изображению
- fade: плавные переходы между изображениями

Использует ffmpeg с пошаговым подходом для избежания сложных фильтров.
"""

import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import tempfile


class VideoGenerator:
    def __init__(self, pipeline_dir: Path):
        self.pipeline_dir = Path(pipeline_dir)
        self.images_dir = self.pipeline_dir / "images"
        self.audio_file = self.pipeline_dir / "audio.mp3"
        self.json_file = self.pipeline_dir / "illustrations.json"
        
        # Проверяем наличие файлов
        if not self.images_dir.exists():
            raise ValueError(f"Каталог изображений не найден: {self.images_dir}")
        if not self.audio_file.exists():
            raise ValueError(f"Аудио файл не найден: {self.audio_file}")
        if not self.json_file.exists():
            raise ValueError(f"JSON файл не найден: {self.json_file}")
    
    def get_image_dimensions(self, image_path: Path) -> Tuple[int, int]:
        """Получает размеры изображения через ffprobe"""
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "stream=width,height",
            "-of", "csv=p=0", str(image_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            width, height = result.stdout.strip().split(',')
            return int(width), int(height)
        except (subprocess.CalledProcessError, ValueError) as e:
            raise RuntimeError(f"Не удалось получить размеры изображения {image_path}: {e}")
    
    def get_target_resolution(self) -> Tuple[int, int]:
        """Определяет целевое разрешение на основе входных данных"""
        video_clips = self.get_video_clips_list()
        images = self.get_images_list()
        
        if video_clips:
            # Если есть готовые видео клипы, используем размер первого
            first_video = min(video_clips.keys())
            video_path = video_clips[first_video]
            cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "stream=width,height",
                "-of", "csv=p=0", str(video_path)
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                width, height = result.stdout.strip().split(',')
                resolution = (int(width), int(height))
                print(f"📐 Разрешение определено по видео клипу: {resolution[0]}x{resolution[1]}")
                return resolution
            except (subprocess.CalledProcessError, ValueError) as e:
                print(f"⚠️  Не удалось получить размер видео клипа, используем размер изображений")
        
        if images:
            # Если нет видео клипов, используем размер первого изображения
            try:
                resolution = self.get_image_dimensions(images[0])
                print(f"📐 Разрешение определено по изображению: {resolution[0]}x{resolution[1]}")
                return resolution
            except Exception as e:
                print(f"⚠️  Не удалось получить размер изображения, используем стандартный размер")
        
        # Fallback к стандартному размеру
        resolution = (1280, 720)
        print(f"📐 Используется стандартное разрешение: {resolution[0]}x{resolution[1]}")
        return resolution
    
    def get_audio_duration(self) -> float:
        """Получает длительность аудио в секундах через ffprobe"""
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(self.audio_file)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            raise RuntimeError(f"Не удалось получить длительность аудио: {e}")
    
    def get_images_list(self) -> List[Path]:
        """Получает список изображений, сортированный по номеру"""
        images = []
        for img in self.images_dir.glob("illustration_*.png"):
            try:
                # Извлекаем номер из имени файла
                num = int(img.stem.split("_")[1])
                images.append((num, img))
            except (ValueError, IndexError):
                continue
        
        # Сортируем по номеру
        images.sort(key=lambda x: x[0])
        return [img for _, img in images]
    
    def get_video_clips_list(self) -> Dict[int, Path]:
        """Получает список готовых видео клипов, сортированный по номеру"""
        clips = {}
        for clip in self.images_dir.glob("video_*.mp4"):
            try:
                # Извлекаем номер из имени файла
                num = int(clip.stem.split("_")[1])
                clips[num] = clip
            except (ValueError, IndexError):
                continue
        
        return clips
    
    def get_video_duration(self, video_path: Path) -> float:
        """Получает длительность видео в секундах через ffprobe"""
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            raise RuntimeError(f"Не удалось получить длительность видео {video_path}: {e}")
    
    
    def create_static_clip(self, image_path: Path, duration: float, output_path: Path, 
                          fade_in: float = 0.0, fade_out: float = 0.0,
                          target_resolution: Tuple[int, int] = None,
                          zoom_direction: Optional[str] = None) -> bool:
        """Создает клип из изображения с опциональными fade эффектами и мягким зумом (с использованием zoompan)"""
        try:
            # Валидация параметров
            if duration <= 0:
                raise ValueError(f"Длительность должна быть положительной: {duration}")
            if fade_in < 0 or fade_out < 0 or fade_in > duration or fade_out > duration:
                raise ValueError(f"Fade in/out должны быть в пределах 0..{duration}")
            
            # Определяем целевое разрешение
            if target_resolution is None:
                target_resolution = self.get_target_resolution()
            
            width, height = target_resolution
            output_size_str = f"{width}x{height}"
            
            # Настройки рендеринга
            fps = 24  # Используем 24 fps как в готовых клипах

            # Получаем размеры изображения
            img_width, img_height = self.get_image_dimensions(image_path)
            if img_width <= 0 or img_height <= 0:
                raise ValueError(f"Некорректные размеры изображения: {img_width}x{img_height}")

            frame_count = max(1, int(round(duration * fps)))

            filter_parts = ["setsar=1"]
            cmd_base = ["ffmpeg", "-y"]
            cmd_input = []
            
            zoom_dir = (zoom_direction or "").lower()

            #
            # === Новая логика с ZOOMPAN ===
            #
            if zoom_dir in {"in", "out"} and frame_count > 1:
                print(f"   ✨ Применяем плавный zoompan (режим: {zoom_dir})")
                max_zoom = 1.16
                total_frames = frame_count
                
                # 'd' (duration) в zoompan - это количество *выходных* кадров
                # 'fps' задает частоту кадров на выходе
                
                # Выражение для плавного прогресса от 0.0 до 1.0
                progress_den = max(total_frames - 1, 1)
                progress_expr = f"min(on/{progress_den},1)"

                if zoom_dir == "out":
                    # Начинаем с max_zoom, заканчиваем на 1.0
                    zoom_expr = f"{max_zoom:.6f}-({max_zoom - 1.0:.6f})*{progress_expr}"
                else:
                    # Начинаем с 1.0, заканчиваем на max_zoom
                    zoom_expr = f"1+({max_zoom - 1.0:.6f})*{progress_expr}"

                # Центрирование кадра. 'z' - это текущий зум из выражения zoom_expr
                pan_x_expr = "'(iw/2)-(iw/z/2)'"
                pan_y_expr = "'(ih/2)-(ih/z/2)'"

                # :x={pan_x_expr}:y={pan_y_expr}: Убрано, чтобы избежать дрожания при zoom
                zoompan_filter = (
                    f"zoompan=z='{zoom_expr}':"
                    f"d={total_frames}:s={output_size_str}:fps={fps}"
                )
                
                filter_parts.append(zoompan_filter)
                
                # Для zoompan входной файл подается один раз, без -loop
                cmd_input = ["-i", str(image_path)]

            #
            # === Старая логика для статичных кадров ===
            #
            else:
                # Рассчитываем масштаб так, чтобы изображение вписывалось в целевое разрешение без обрезки
                scale_factor = min(width / img_width, height / img_height)
                scaled_w = max(2, int(round(img_width * scale_factor)))
                scaled_h = max(2, int(round(img_height * scale_factor)))

                # Гарантируем четные размеры
                if scaled_w % 2 != 0:
                    if scaled_w < width:
                        scaled_w += 1
                    else:
                        scaled_w -= 1
                if scaled_h % 2 != 0:
                    if scaled_h < height:
                        scaled_h += 1
                    else:
                        scaled_h -= 1

                scaled_w = max(2, min(scaled_w, width))
                scaled_h = max(2, min(scaled_h, height))

                filter_parts.append(f"scale={scaled_w}:{scaled_h}")

                # Добавляем паддинг, если нужно вывести точное целевое разрешение
                if scaled_w != width or scaled_h != height:
                    filter_parts.append(
                        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
                    )
                
                # Для статичного кадра используем -loop 1
                cmd_input = [
                    "-loop", "1",
                    "-framerate", str(fps),
                    "-i", str(image_path),
                ]

            # Добавляем fade эффекты (после всех трансформаций)
            if fade_in and fade_in > 0:
                filter_parts.append(f"fade=t=in:st=0:d={fade_in}")
            if fade_out and fade_out > 0:
                filter_parts.append(f"fade=t=out:st={max(0.0, duration - fade_out)}:d={fade_out}")

            filter_str = ",".join(filter_parts)

            cmd_output = [
                "-vf", filter_str,
                "-r", str(fps),
                "-t", str(duration),  # Точная длительность
                "-c:v", "libx264",
                "-crf", "23",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-avoid_negative_ts", "make_zero",  # Избегаем проблем с временными метками
                str(output_path)
            ]
            
            # Собираем полную команду
            cmd = cmd_base + cmd_input + cmd_output
            
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка создания статичного клипа {image_path.name}: {e}")
            if e.stderr:
                print(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Ошибка создания статичного клипа {image_path.name}: {e}")
            return False


    def extend_video_clip(self, video_path: Path, target_duration: float, output_path: Path, target_resolution: Tuple[int, int] = None) -> bool:
        """Увеличивает длительность видео путем циклического проигрывания"""
        try:
            video_duration = self.get_video_duration(video_path)
            
            # Определяем целевое разрешение
            if target_resolution is None:
                target_resolution = self.get_target_resolution()
            
            width, height = target_resolution
            
            if video_duration >= target_duration:
                # Если видео уже достаточно длинное, обрезаем и нормализуем
                filter_str = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-vf", filter_str,
                    "-t", str(target_duration),
                    "-c:v", "libx264",
                    "-crf", "23",
                    "-preset", "fast",
                    "-pix_fmt", "yuv420p",
                    "-r", "24",  # Стандартизируем fps
                    "-avoid_negative_ts", "make_zero",
                    str(output_path)
                ]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return True
            else:
                # Используем более точный метод с временной директорией
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    
                    # Вычисляем количество повторений
                    repeats = int(target_duration / video_duration) + 2  # +2 для гарантии
                    
                    # Создаем список файлов для конкатенации
                    concat_list = temp_path / "repeat_list.txt"
                    with open(concat_list, "w") as f:
                        abs_video = str(video_path.resolve())
                        safe_abs_video = abs_video.replace("\\", "\\\\").replace("'", "\\'")
                        for _ in range(repeats):
                            f.write(f"file '{safe_abs_video}'\n")
                    
                    # Объединяем повторения
                    repeated_video = temp_path / "repeated.mp4"
                    cmd_concat = [
                        "ffmpeg", "-y",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", str(concat_list),
                        "-c", "copy",
                        "-avoid_negative_ts", "make_zero",
                        str(repeated_video)
                    ]
                    subprocess.run(cmd_concat, capture_output=True, text=True, check=True)
                    
                    # Обрезаем до точной длительности с нормализацией формата
                    filter_str = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
                    cmd_trim = [
                        "ffmpeg", "-y",
                        "-i", str(repeated_video),
                        "-vf", filter_str,
                        "-t", str(target_duration),
                        "-c:v", "libx264",
                        "-crf", "23",
                        "-preset", "fast",
                        "-pix_fmt", "yuv420p",
                        "-r", "24",  # Стандартизируем fps
                        "-avoid_negative_ts", "make_zero",
                        str(output_path)
                    ]
                    subprocess.run(cmd_trim, capture_output=True, text=True, check=True)
                    
                    return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка расширения видео клипа {video_path.name}: {e}")
            if e.stderr:
                print(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Ошибка расширения видео клипа {video_path.name}: {e}")
            return False
    
    def create_single_clip(self, image_path: Path, duration: float,
                          output_path: Path, fade_duration: float = 0.5,
                          target_resolution: Tuple[int, int] = None,
                          zoom_direction: Optional[str] = None) -> bool:
        """Создает клип для одного изображения. Поддерживает готовые видео клипы."""
        try:
            if duration <= 0:
                raise ValueError(f"Длительность должна быть положительной: {duration}")
            if fade_duration < 0 or fade_duration > duration:
                raise ValueError(f"Fade duration должен быть от 0 до {duration}: {fade_duration}")

            # Определяем целевое разрешение
            if target_resolution is None:
                target_resolution = self.get_target_resolution()
            
            width, height = target_resolution

            # Извлекаем номер изображения
            try:
                image_num = int(image_path.stem.split("_")[1])
            except (ValueError, IndexError):
                print(f"❌ Не удалось извлечь номер из имени файла: {image_path.name}")
                return False
            
            # Проверяем наличие готового видео клипа
            video_clips = self.get_video_clips_list()
            if image_num in video_clips:
                video_clip = video_clips[image_num]
                print(f"🎬 Используем готовый видео клип: {video_clip.name}")
                
                # Проверяем длительность видео клипа
                video_duration = self.get_video_duration(video_clip)
                
                if video_duration >= duration:
                    # Видео достаточно длинное, обрезаем его с fade эффектами и нормализацией
                    if fade_duration > 0:
                        # Применяем fade эффекты при обрезке + нормализация формата
                        filter_str = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fade=t=out:st={max(0.0, duration - fade_duration)}:d={fade_duration}"
                        cmd = [
                            "ffmpeg", "-y",
                            "-i", str(video_clip),
                            "-vf", filter_str,
                            "-t", str(duration),
                            "-c:v", "libx264",
                            "-crf", "23",
                            "-preset", "fast",
                            "-pix_fmt", "yuv420p",
                            "-r", "24",  # Стандартизируем fps
                            "-avoid_negative_ts", "make_zero",
                            str(output_path)
                        ]
                    else:
                        # Простая обрезка с нормализацией формата
                        filter_str = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
                        cmd = [
                            "ffmpeg", "-y",
                            "-i", str(video_clip),
                            "-vf", filter_str,
                            "-t", str(duration),
                            "-c:v", "libx264",
                            "-crf", "23",
                            "-preset", "fast",
                            "-pix_fmt", "yuv420p",
                            "-r", "24",  # Стандартизируем fps
                            "-avoid_negative_ts", "make_zero",
                            str(output_path)
                        ]
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                else:
                    # Видео короче, расширяем его циклическим проигрыванием
                    print(f"🔄 Расширяем видео клип с {video_duration:.2f}с до {duration:.2f}с")
                    return self.extend_video_clip(video_clip, duration, output_path, target_resolution)
                
                return True
            else:
                # Создаем статичный клип из изображения
                zoom_desc = {
                    "in": "с мягким приближением",
                    "out": "с мягким отдалением"
                }.get((zoom_direction or "").lower(), "без движения")
                print(f"🖼️  Создаем статичный клип из изображения: {image_path.name} ({zoom_desc})")
                return self.create_static_clip(
                    image_path=image_path,
                    duration=duration,
                    output_path=output_path,
                    fade_in=fade_duration,
                    fade_out=fade_duration,
                    target_resolution=target_resolution,
                    zoom_direction=zoom_direction
                )

        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка создания клипа: {e}")
            if e.stderr:
                print(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Ошибка создания клипа: {e}")
            return False
    
    def create_video(self, output_file: str, fade_duration: float = 0.5, quality: str = "medium", 
                    silence_duration: float = 0.0, ending_duration: float = 0.0,
                    image_motion: bool = False) -> bool:
        """
        Создает видео из изображений и готовых клипов с аудио
        
        Args:
            output_file: Путь к выходному MP4 файлу
            fade_duration: Длительность fade между изображениями
            quality: Качество видео (low, medium, high)
            silence_duration: Время показа первого изображения до начала слов (сек)
            ending_duration: Время показа последнего изображения после слов (сек)
            image_motion: Включить чередующийся мягкий зум для изображений
        """
        try:
            # Получаем длительность аудио и список изображений
            audio_duration = self.get_audio_duration()
            images = self.get_images_list()
            video_clips = self.get_video_clips_list()
            
            if not images:
                raise ValueError("Не найдены изображения для видео")
            
            print(f"🎵 Длительность аудио: {audio_duration:.2f} сек")
            print(f"🖼️  Количество изображений: {len(images)}")
            print(f"🎬 Найдено готовых видео клипов: {len(video_clips)}")
            
            # Определяем целевое разрешение один раз
            target_resolution = self.get_target_resolution()
            
            # Проверяем параметры
            if silence_duration < 0:
                raise ValueError(f"silence_duration не может быть отрицательным: {silence_duration}")
            if ending_duration < 0:
                raise ValueError(f"ending_duration не может быть отрицательным: {ending_duration}")
            if silence_duration + ending_duration >= audio_duration:
                raise ValueError(
                    f"Сумма silence_duration ({silence_duration:.2f}) и ending_duration ({ending_duration:.2f}) "
                    f"не может быть больше или равна длительности аудио ({audio_duration:.2f})"
                )
            
            # Рассчитываем время показа изображений
            # Распределяем длительности показа изображений
            durations_per_image: List[float] = []
            if len(images) == 1:
                # Единственное изображение показывает все аудио
                durations_per_image = [audio_duration]
                print(f"⏱️  Единственное изображение: {audio_duration:.2f} сек")
            else:
                # Если без специальных длительностей - равномерно по всем
                if silence_duration == 0 and ending_duration == 0:
                    per = audio_duration / len(images)
                    durations_per_image = [per for _ in images]
                    print(f"⏱️  Время на изображение (равномерно): {per:.2f} сек")
                else:
                    fixed_indices = set()
                    if silence_duration > 0:
                        fixed_indices.add(0)
                    if ending_duration > 0:
                        fixed_indices.add(len(images) - 1)

                    remaining_time = audio_duration - silence_duration - ending_duration
                    middle_count = len(images) - len(fixed_indices)
                    per_middle = remaining_time / middle_count if middle_count > 0 else 0.0

                    durations_per_image = []
                    for idx in range(len(images)):
                        if idx == 0 and silence_duration > 0:
                            durations_per_image.append(silence_duration)
                        elif idx == len(images) - 1 and ending_duration > 0:
                            durations_per_image.append(ending_duration)
                        else:
                            durations_per_image.append(per_middle)

                    if silence_duration > 0:
                        print(f"🔇 Время до начала слов (1-е изображение): {silence_duration:.2f} сек")
                    if ending_duration > 0:
                        print(f"🔕 Время завершения (последнее изображение): {ending_duration:.2f} сек")
                    print(f"⏱️  Время на остальные изображения: {per_middle:.2f} сек")
            
            # Ограничиваем fade duration для очень коротких клипов
            # Для ограничения fade нам нужна минимальная длительность клипа
            min_clip_duration = min(durations_per_image) if durations_per_image else 0.0
            if min_clip_duration > 0 and fade_duration > min_clip_duration * 0.4:
                fade_duration = min_clip_duration * 0.4
                print(f"⚠️  Fade duration скорректирован до {fade_duration:.2f} сек (на основе минимальной длительности клипа)")
            
            # Создаем временную директорию для клипов
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                clip_files = []
                clip_durations = []
                
                print("🎬 Создание отдельных клипов...")
                
                # Создаем клип для каждого изображения
                for i, img in enumerate(images):
                    clip_file = temp_path / f"clip_{i:02d}.mp4"
                    current_duration = durations_per_image[i]
                    current_img = img
                    if i == 0 and silence_duration > 0:
                        print(f"🔄 Создание клипа {i+1}/{len(images)}: первое изображение ({current_duration:.2f}с)...")
                    elif i == len(images) - 1 and ending_duration > 0:
                        print(f"🔄 Создание клипа {i+1}/{len(images)}: последнее изображение ({current_duration:.2f}с)...")
                    else:
                        print(f"🔄 Создание клипа {i+1}/{len(images)}: изображение ({current_duration:.2f}с)...")
                    
                    # Проверяем наличие готового видео клипа
                    try:
                        image_num = int(current_img.stem.split("_")[1])
                        has_video = image_num in video_clips
                        if has_video:
                            print(f"   📹 Используем готовый видео клип")
                        else:
                            print(f"   🖼️  Создаем статичный клип")
                    except (ValueError, IndexError):
                        print(f"   🖼️  Создаем статичный клип")
                        has_video = False
                    
                    zoom_direction = None
                    if image_motion:
                        zoom_direction = "in" if (i % 2 == 0) else "out"
                    success = self.create_single_clip(
                        current_img,
                        current_duration,
                        clip_file,
                        fade_duration,
                        target_resolution,
                        zoom_direction=zoom_direction
                    )
                    
                    if not success:
                        print(f"❌ Не удалось создать клип для {current_img.name}")
                        return False
                    
                    # Проверяем фактическую длительность созданного клипа
                    try:
                        actual_duration = self.get_video_duration(clip_file)
                        duration_diff = abs(actual_duration - current_duration)
                        if duration_diff > 0.1:  # Если разница больше 0.1 секунды
                            print(f"⚠️  Клип {i+1}: ожидалось {current_duration:.2f}с, получилось {actual_duration:.2f}с (разница: {duration_diff:.2f}с)")
                        else:
                            print(f"✅ Клип {i+1} создан: {clip_file.name} ({actual_duration:.2f}с)")
                    except Exception as e:
                        print(f"⚠️  Не удалось проверить длительность клипа {i+1}: {e}")
                        print(f"✅ Клип {i+1} создан: {clip_file.name}")
                    
                    clip_files.append(clip_file)
                    clip_durations.append(current_duration)
                
                # Создаем список файлов для конкатенации (используем абсолютные и экранированные пути)
                concat_list = temp_path / "concat_list.txt"
                with open(concat_list, 'w') as f:
                    for clip in clip_files:
                        abs_clip = str(clip.resolve())
                        safe_abs_clip = abs_clip.replace("\\", "\\\\").replace("'", "\\'")
                        f.write(f"file '{safe_abs_clip}'\n")
                
                # Проверяем фактическую длительность каждого клипа перед конкатенацией
                print("🔍 Проверка длительности клипов перед конкатенацией...")
                actual_durations = []
                for i, clip_file in enumerate(clip_files):
                    try:
                        actual_duration = self.get_video_duration(clip_file)
                        actual_durations.append(actual_duration)
                        expected_duration = clip_durations[i]
                        diff = abs(actual_duration - expected_duration)
                        if diff > 0.1:
                            print(f"⚠️  Клип {i+1}: ожидалось {expected_duration:.2f}с, фактически {actual_duration:.2f}с (разница: {diff:.2f}с)")
                        else:
                            print(f"✅ Клип {i+1}: {actual_duration:.2f}с (ожидалось {expected_duration:.2f}с)")
                    except Exception as e:
                        print(f"❌ Ошибка проверки клипа {i+1}: {e}")
                        actual_durations.append(clip_durations[i])
                
                # Проверяем общую длительность видео клипов
                total_actual_duration = sum(actual_durations)
                total_expected_duration = sum(clip_durations)
                print(f"📊 Общая фактическая длительность видео: {total_actual_duration:.2f} сек")
                print(f"📊 Общая ожидаемая длительность видео: {total_expected_duration:.2f} сек")
                print(f"📊 Длительность аудио: {audio_duration:.2f} сек")
                duration_diff = abs(total_actual_duration - audio_duration)
                if duration_diff > 0.5:  # Если разница больше 0.5 секунды
                    print(f"⚠️  Предупреждение: разница между видео и аудио составляет {duration_diff:.2f} сек")
                else:
                    print(f"✅ Длительности видео и аудио синхронизированы (разница: {duration_diff:.2f} сек)")
                
                print("🎬 Объединение клипов в финальное видео...")
                
                # Объединяем все клипы
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_list),
                    "-i", str(self.audio_file),
                    "-c:v", "copy",  # Копируем видео без перекодирования
                    "-c:a", "aac",    # Перекодируем аудио в AAC
                    "-map", "0:v:0",  # Берем видео из первого потока (concat)
                    "-map", "1:a:0",  # Берем аудио из второго потока (audio.mp3)
                    "-avoid_negative_ts", "make_zero",
                    "-fflags", "+genpts",  # Генерируем временные метки
                    "-movflags", "+faststart",
                    output_file
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                print(f"✅ Видео создано: {output_file}")
                return True
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка ffmpeg: {e}")
            if e.stderr:
                print(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Ошибка создания видео: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Генерация видео из изображений и аудио с поддержкой готовых клипов")
    parser.add_argument("--pipeline-dir", help="Каталог пайплайна с images/ и audio.mp3")
    parser.add_argument("--output", "-o", help="Выходной MP4 файл (по умолчанию: <pipeline-dir>/video.mp4)")
    parser.add_argument("--fade-duration", type=float, default=0.5, help="Длительность fade между изображениями (сек)")
    parser.add_argument("--quality", choices=["low", "medium", "high"], default="medium", help="Качество видео")
    parser.add_argument("--silence-duration", type=float, default=0.0, help="Время показа первого изображения до начала слов (сек)")
    parser.add_argument("--ending-duration", type=float, default=0.0, help="Время показа последнего изображения после слов (сек)")
    parser.add_argument("--enable-photo-motion", action="store_true", help="Включить мягкий зум/отдаление для изображений")
    
    args = parser.parse_args()
    
    # Проверяем обязательные параметры
    if not args.pipeline_dir:
        parser.error("--pipeline-dir обязателен для создания видео")
    
    try:
        # Создаем генератор
        generator = VideoGenerator(args.pipeline_dir)
        
        # Определяем выходной файл
        if args.output:
            output_file = args.output
        else:
            output_file = str(Path(args.pipeline_dir) / "video.mp4")
        
        # Создаем видео
        success = generator.create_video(
            output_file=output_file,
            fade_duration=args.fade_duration,
            quality=args.quality,
            silence_duration=args.silence_duration,
            ending_duration=args.ending_duration,
            image_motion=args.enable_photo_motion
        )
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
