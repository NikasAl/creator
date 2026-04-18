from manim import *
import json
import os
import random
import numpy as np
import textwrap

# Настройка разрешения
config.pixel_height = 768
config.pixel_width = 1366
config.frame_height = 9.0
config.frame_width = 16.0

class PoetryScene(Scene):
    def construct(self):
        # ПЕРЕЗАПИСЬ МЕТОДА CONSTRUCT С ЧИСТОЙ ЛОГИКОЙ
        with open("screenplay.json", "r", encoding="utf-8") as f:
            segments = json.load(f)
        
        self.add_sound("audio.mp3")
        self.particles = VGroup()
        self.particles.set_z_index(10)
        self.add(self.particles)
        
        previous_img = None
        
        for i, seg in enumerate(segments):
            # 1. Синхронизация (Gap Filling)
            target_start = seg["start"]
            now = self.renderer.time
            gap = target_start - now
            
            if gap > 0.1:
                if previous_img:
                    # Динамическое ожидание
                    self.update_particles(seg.get("overlay", "none"), gap)
                    idle = self.get_random_idle_animation(previous_img, gap)
                    self.play(idle, run_time=gap)
                else:
                    self.wait(gap)

            # 2. Подготовка сцены
            duration = seg["end"] - seg["start"]
            if duration < 0.1: duration = 0.1
            
            # Картинка
            img = self.create_image_object(seg["image_path"])
            
            # Текст (должен исчезать в конце фразы)
            txt_obj = self.create_text_object(seg)
            if txt_obj: txt_obj.set_z_index(20)
            
            # Движение камеры (эффект)
            effect_name = seg.get("camera_move", "static")
            movement_anim = self.get_camera_movement_anim(img, effect_name, duration)
            
            # Частицы
            self.update_particles(seg.get("overlay", "none"), duration)

            # 3. Исполнение (CrossFade Transition)
            fade_time = 2
            if fade_time > duration: fade_time = duration / 2
            
            # Группа анимаций для начала (Переход)
            start_anims = [FadeIn(img, run_time=fade_time)]
            if txt_obj: start_anims.append(FadeIn(txt_obj, run_time=fade_time))
            if previous_img: start_anims.append(FadeOut(previous_img, run_time=fade_time))
            
            # Основное движение происходит параллельно с переходом и продолжается после
            # Мы используем AnimationGroup с lag_ratio, но проще разбить на такты
            
            # ТАКТ 1: Переход (одновременно начинается движение)
            # Чтобы движение шло гладко через весь сегмент, мы не можем разрывать MoveToTarget.
            # Поэтому мы применим движение ко всему сегменту, а фейды добавим параллельно.
            
            # В Manim сложно запустить MoveToTarget на 5 сек, а FadeIn на 1 сек внутри одного play.
            # Поэтому сделаем "умный" подход: анимируем свойства вручную или используем Successions.
            
            # ПРОСТОЙ ПОДХОД: FadeIn + Move (параллельно).
            # Previous img исчезает, New img появляется и начинает двигаться.
            
            # Сначала выполняем переход (fade_time)
            self.play(
                *start_anims,
                run_time=fade_time
            )
            
            # Затем продолжаем основное движение на оставшееся время
            if duration > fade_time:
                self.play(
                    movement_anim,
                    run_time=duration - fade_time
                )
            
            # 4. Завершение сцены
            # Текст исчезает. Картинка ОСТАЕТСЯ для следующего гапа.
            if txt_obj:
                self.play(FadeOut(txt_obj, run_time=0.5))
            
            previous_img = img

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---

    def create_image_object(self, path):
        if not os.path.exists(path):
            obj = Rectangle(color=GRAY, fill_opacity=0.5)
        else:
            obj = ImageMobject(path)
            
        # Масштабирование "Cover"
        img_ratio = obj.width / obj.height
        screen_ratio = config.frame_width / config.frame_height
        if img_ratio > screen_ratio:
            obj.height = config.frame_height
        else:
            obj.width = config.frame_width
        obj.scale(1.1) # Запас для зума
        return obj

    def create_text_object(self, seg):
        text_str = seg.get("text", "").strip()
        if not text_str: return None
        
        wrapped = textwrap.fill(text_str, width=60)
        # Используем шрифт по умолчанию или системный
        t = Text(wrapped, font="Sans", font_size=30, color=WHITE, line_spacing=1.2)
        bg = BackgroundRectangle(t, color=BLACK, fill_opacity=0.6, corner_radius=0.3, buff=0.2)
        group = VGroup(bg, t)
        
        pos = seg.get("text_position", "bottom")
        if pos == "bottom": group.to_edge(DOWN, buff=0.5)
        elif pos == "top": group.to_edge(UP, buff=0.5)
        else: group.move_to(ORIGIN)
        
        return group

    def get_camera_movement_anim(self, img, effect, duration):
        # Возвращает объект анимации (MoveToTarget)
        img.save_state()
        if effect == "zoom_in":
            img.generate_target()
            img.target.scale(1.15)
        elif effect == "zoom_out":
            img.scale(1.15)
            img.generate_target()
            img.target.restore()
        elif effect == "pan_right":
            img.shift(LEFT * 1)
            img.generate_target()
            img.target.shift(RIGHT * 2)
        elif effect == "pan_left":
            img.shift(RIGHT * 1)
            img.generate_target()
            img.target.shift(LEFT * 2)
        else: # static
            img.generate_target()
            img.target.scale(1.02) # Легкое дыхание
            
        return MoveToTarget(img, run_time=duration, rate_func=linear)

    def get_random_idle_animation(self, img, duration):
        """Создает случайную ленивую анимацию для заполнения паузы"""
        r = random.random()
        
        # Вариант 1: Медленный дрейф в случайную сторону
        if r < 0.33:
            rand_vect = np.array([random.uniform(-0.5, 0.5), random.uniform(-0.3, 0.3), 0])
            return ApplyMethod(img.shift, rand_vect, run_time=duration, rate_func=linear)
            
        # Вариант 2: Медленное дыхание (scale)
        elif r < 0.66:
            # Если картинка уже большая, уменьшаем, иначе увеличиваем
            return ApplyMethod(img.scale, 1.03, run_time=duration, rate_func=linear)
            
        # Вариант 3: Очень легкий поворот (Wiggle)
        else:
            angle = 0.02 if random.random() > 0.5 else -0.02
            return ApplyMethod(img.rotate, angle, run_time=duration, rate_func=linear)

    def update_particles(self, p_type, duration):
        self.particles.remove(*self.particles)
        
        if p_type == "none": return

        if p_type == "snow" or p_type == "embers":
            colors = [WHITE, GREY_A] if p_type == "snow" else [ORANGE, RED, YELLOW]
            direction = DOWN if p_type == "snow" else UP
            
            for _ in range(40):
                d = Dot(radius=random.random()*0.05, color=random.choice(colors))
                # Разбрасываем по всему экрану
                d.move_to([
                    random.uniform(-config.frame_width/2, config.frame_width/2),
                    random.uniform(-config.frame_height/2, config.frame_height/2),
                    0
                ])
                velocity = direction * (random.random() * 1.5 + 0.5)
                
                # Замыкание для update
                def get_updater(vel, pt):
                    return lambda m, dt: self.particle_move(m, dt, vel, pt)
                
                d.add_updater(get_updater(velocity, p_type))
                self.particles.add(d)

        elif p_type == "stars":
            for _ in range(60):
                d = Dot(radius=random.random()*0.04, color=WHITE)
                d.move_to([
                    random.uniform(-config.frame_width/2, config.frame_width/2),
                    random.uniform(-config.frame_height/2, config.frame_height/2),
                    0
                ])
                d.phase = random.random() * 10
                d.add_updater(lambda m, dt: self.star_flicker(m, dt))
                self.particles.add(d)

    # Методы для updaters (нужны чтобы избежать проблем с лямбдами в цикле)
    def particle_move(self, mob, dt, velocity, p_type):
        mob.shift(velocity * dt)
        if p_type == "snow" and mob.get_y() < -config.frame_height/2:
            mob.set_y(config.frame_height/2)
        elif p_type == "embers" and mob.get_y() > config.frame_height/2:
            mob.set_y(-config.frame_height/2)

    def star_flicker(self, mob, dt):
        mob.phase += dt
        val = 0.5 + 0.5 * np.sin(3 * mob.phase)
        mob.set_opacity(val)
