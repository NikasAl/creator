from manim import *
import numpy as np

# Настройка LaTeX для кириллицы
config.tex_template = TexTemplate(
    documentclass=r"\documentclass[preview]{standalone}",
    preamble=r"""
    \usepackage{amsmath}
    \usepackage{amsfonts}
    \usepackage{amssymb}
    \usepackage{mathtools}
    \usepackage{fontspec}
    \usepackage{babel}
    \babelprovide[import=ru, main]{russian}
    \babelfont{rm}{DejaVu Serif}
    \babelfont{sf}{DejaVu Sans}
    \babelfont{tt}{DejaVu Sans Mono}
    """,
    tex_compiler="lualatex",
    output_format=".dvi"
)

class AlgebraicDetectiveImproved(Scene):
    SHORT_PAUSE = 1.5 
    
    def fit_to_screen(self, mobject, buffer=0.5):
        """Автоматически масштабирует объект"""
        frame_width = config.frame_width - buffer
        frame_height = config.frame_height - buffer
        width = mobject.width
        height = mobject.height
        if width == 0 or height == 0: return mobject
        scale_factor = min(frame_width / width, frame_height / height)
        if scale_factor < 1: return mobject.scale(scale_factor)
        return mobject
    
    def sync_to(self, target_time):
        """
        Умная задержка: ждет, пока время видео не достигнет target_time.
        Это позволяет синхронизировать анимацию с аудио-дорожкой.
        """
        current_time = self.renderer.time
        wait_time = target_time - current_time
        
        if wait_time > 0:
            self.wait(wait_time)
        else:
            # Если анимация не успевает за голосом, выводим предупреждение
            print(f"Warning: Animation lagging behind audio by {abs(wait_time):.2f}s at {target_time}")

    def show_step_by_step(self, expressions, scale_factor=1.2):
        """
        Показывает выражения по одному.
        Использует FadeTransform для плавности.
        """
        current_obj = None
        for expr in expressions:
            obj = MathTex(expr).scale(scale_factor)
            obj = self.fit_to_screen(obj)
            
            if current_obj is None:
                self.play(Write(obj))
            else:
                self.play(FadeTransform(current_obj, obj))
            
            self.wait(self.SHORT_PAUSE)
            current_obj = obj
        return current_obj

    def construct(self):
        # === СЦЕНА 1: ВСТУПЛЕНИЕ ===
        # Аудио: "Добро пожаловать... доказать" (0.0 - 6.56)
        title = Text("Алгебраический детектив", font_size=48, weight=BOLD).to_edge(UP)
        
        equation = MathTex(
            r"\left(\frac{4}{3 - \sqrt{5}}\right)^2", 
            r"-", 
            r"\left(\frac{6 - 5\sqrt{6}}{5 - \sqrt{6}}\right)^2",
            r" = ",
            r"2\sqrt{61 + 24\sqrt{5}}"
        ).scale(1.0)
        
        equation[0].set_color(BLUE_B)
        equation[2].set_color(TEAL_B)
        equation[4].set_color(GOLD)
        
        equation = self.fit_to_screen(equation)
        comment = Text("Задача: Доказать равенство", font_size=36, color=GREY_A).next_to(equation, DOWN, buff=1)
        
        self.play(Write(title))
        self.sync_to(6.56) 

        # Аудио: "Вот это пугающее... красивая головоломка" (6.56 - 21.14)
        self.play(FadeIn(equation, shift=UP))
        self.play(Write(comment))
        self.sync_to(21.14) 
        
        # === СЦЕНА 2: ГИПОТЕЗА 0 (ТУПИК) ===
        # Аудио: "Первое желание... в квадрат" (21.14 - 29.48)
        self.clear()
        hypothesis_title = Text("Путь 1: Лобовая атака", font_size=42, color=RED).to_edge(UP)
        hypothesis_text = Text("Возвести дроби в квадрат сразу?", font_size=32).next_to(hypothesis_title, DOWN)
        
        self.play(Write(hypothesis_title), Write(hypothesis_text))
        self.sync_to(29.48)

        # Аудио: "Но посмотрите... никуда не делись" (29.48 - 36.98)
        bad_math = MathTex(
            r"\frac{16}{14 - 6\sqrt{5}} - \frac{186 - 60\sqrt{6}}{31 - 10\sqrt{6}}"
        ).scale(1.2)
        self.play(Write(bad_math))
        self.sync_to(36.98)
        
        # Аудио: "Это математическое болото... не подходит" (36.98 - 43.82)
        cross = Cross(bad_math).set_color(RED)
        warning = Text("Слишком сложные вычисления!", font_size=36, color=RED).next_to(cross, DOWN)
        
        self.play(Create(cross))
        self.play(Write(warning))
        self.sync_to(43.82)
        
        # === СЦЕНА 3: ПЛАН ===
        # Аудио: "Умный математик... будет таким" (43.82 - 48.68)
        self.clear()
        plan_title = Text("Путь 2: Стратегия упрощения", font_size=42, color=GREEN).to_edge(UP)
        self.play(Write(plan_title))
        self.sync_to(48.68)

        steps = VGroup(
            Text("1. Упростить знаменатели (избавиться от корней)", font_size=32),
            Text("2. Возвести упрощенные дроби в квадрат", font_size=32),
            Text("3. Преобразовать правую часть (выделить полный квадрат)", font_size=32)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        
        # Аудио: "Во-первых... иррациональности" (до 54.14)
        self.play(Write(steps[0]))
        self.sync_to(54.14)

        # Аудио: "Во-вторых... в квадрат" (до 58.92)
        self.play(Write(steps[1]))
        self.sync_to(58.92)

        # Аудио: "И в-третьих... сложный корень" (до 64.54)
        self.play(Write(steps[2]))
        self.sync_to(64.54)

        # Аудио: "Разделяй и властвуй" (до 66.06)
        self.sync_to(66.06)
        
        # === СЦЕНА 4: ДРОБЬ 1 ===
        # Аудио: "Начнем с первой дроби... корень из пяти внизу" (66.06 - 70.36)
        self.clear()
        step_title = Text("Шаг 1: Первая дробь", font_size=42, color=BLUE).to_edge(UP)
        self.play(Write(step_title))
        
        frac1 = MathTex(r"\frac{4}{3 - \sqrt{5}}").scale(1.5)
        self.play(Write(frac1))
        self.sync_to(70.36)
        
        # Аудио: "В математике... дурным тоном" (до 72.78)
        problem_arrow = Arrow(start=frac1.get_bottom(), end=frac1.get_bottom() + DOWN, color=RED)
        problem_text = Text("Иррациональность внизу", font_size=24, color=RED).next_to(problem_arrow, DOWN)
        self.play(GrowArrow(problem_arrow), FadeIn(problem_text))
        self.sync_to(72.78)
        self.play(FadeOut(problem_arrow), FadeOut(problem_text))
        
        # Аудио: "Чтобы его убрать... классический трюк... Домножим" (до 76.86)
        self.play(frac1.animate.shift(LEFT * 2))
        
        conjugate_fraction = MathTex(r"\cdot \frac{3 + \sqrt{5}}{3 + \sqrt{5}}").scale(1.5)
        conjugate_fraction.next_to(frac1, RIGHT)
        conjugate_fraction[0][1:].set_color(YELLOW) 
        
        conj_label = Text("Сопряженное выражение", font_size=24, color=YELLOW).next_to(conjugate_fraction, UP)
        conj_desc = Text("(меняем минус на плюс)", font_size=20, color=GREY).next_to(conjugate_fraction, DOWN)
        
        self.play(Write(conjugate_fraction))
        self.play(FadeIn(conj_label), FadeIn(conj_desc))
        
        # Аудио: "Смотрите... но с плюсом" (до 84.9)
        self.sync_to(84.9)
        self.play(FadeOut(conj_label), FadeOut(conj_desc))
        
        # Аудио: "Это позволяет... разности квадратов" (до 89.08)
        long_frac = MathTex(r"\frac{4(3 + \sqrt{5})}{(3)^2 - (\sqrt{5})^2}").scale(1.5)
        long_frac[0][2:7].set_color(YELLOW) 
        
        self.play(FadeTransform(VGroup(frac1, conjugate_fraction), long_frac))
        self.sync_to(89.08)
        self.play(FadeOut(long_frac))

        # --- ИСПРАВЛЕННЫЙ БЛОК (Анимация упрощения) ---
        # Аудио: "Корни исчезают... остается четверка" (до 93.4)
        step_simplify_1 = MathTex(r"\frac{4(3 + \sqrt{5})}{9 - 5}").scale(1.5)
        self.play(Write(step_simplify_1))
        self.sync_to(92.0) # "в знаменателе остается"
        
        step_simplify_2 = MathTex(r"\frac{4(3 + \sqrt{5})}{4}").scale(1.5)
        # Используем ReplacementTransform, чтобы избежать ошибок интерполяции цвета в FadeTransform
        self.play(ReplacementTransform(step_simplify_1, step_simplify_2))
        self.sync_to(93.4) # "четверка"

        # Аудио: "которая сокращается... 3 плюс корень из пяти" (до 98.72)
        step_simplify_3 = MathTex(r"3 + \sqrt{5}").scale(1.5)
        self.play(ReplacementTransform(step_simplify_2, step_simplify_3))
        self.sync_to(98.72)
        # ---------------------------------------------

        # === СЦЕНА 5: ДРОБЬ 2 ===
        # Аудио: "Теперь вторая дробь... схеме" (98.72 - 101.98)
        self.clear()
        step2_title = Text("Шаг 2: Вторая дробь", font_size=42, color=TEAL).to_edge(UP)
        self.play(Write(step2_title))
        
        frac2 = MathTex(r"\frac{6 - 5\sqrt{6}}{5 - \sqrt{6}}").scale(1.5).shift(LEFT * 2)
        self.play(Write(frac2))
        self.sync_to(101.98)
        
        # Аудио: "Видим 5 минус... на 5 плюс" (до 106.94)
        conjugate_fraction2 = MathTex(r"\cdot \frac{5 + \sqrt{6}}{5 + \sqrt{6}}").scale(1.5).next_to(frac2, RIGHT)
        conjugate_fraction2[0][1:].set_color(TEAL)
        
        conj_label2 = Text("Домножаем на сопряженное", font_size=24, color=TEAL).next_to(conjugate_fraction2, UP)
        
        self.play(Write(conjugate_fraction2), FadeIn(conj_label2))
        self.sync_to(106.94)
        self.play(FadeOut(conj_label2))
        
        # Аудио: "Сверху... разность квадратов" (до 113.6)
        long_frac2 = MathTex(r"\frac{(6 - 5\sqrt{6})(5 + \sqrt{6})}{25 - 6}").scale(1.3)
        long_frac2[0][8:14].set_color(TEAL)
        
        self.play(FadeTransform(VGroup(frac2, conjugate_fraction2), long_frac2))
        self.sync_to(113.6)
        self.play(FadeOut(long_frac2))

        # Аудио: "25 минус 6 это 19... элегантный ответ - корень из шести" (до 125.5)
        step_val1 = MathTex(r"\frac{30 + 6\sqrt{6} - 25\sqrt{6} - 30}{19}").scale(1.5)
        self.play(Write(step_val1))
        self.sync_to(116.46) # "это 19"

        step_val2 = MathTex(r"\frac{-19\sqrt{6}}{19}").scale(1.5)
        self.play(ReplacementTransform(step_val1, step_val2)) # Changed to ReplacementTransform
        self.sync_to(120.8) # "сокращаются"
        
        step_val3 = MathTex(r"-\sqrt{6}").scale(1.5)
        self.play(ReplacementTransform(step_val2, step_val3)) # Changed to ReplacementTransform
        self.sync_to(125.5)

        # === СЦЕНА 6: СБОРКА ЛЕВОЙ ЧАСТИ ===
        # Аудио: "Самая сложная... Вернемся к исходному" (125.5 - 130.54)
        self.clear()
        step3 = Text("Шаг 3: Подставляем в левую часть", font_size=36).to_edge(UP)
        self.play(Write(step3))
        self.sync_to(130.54)
        
        # Аудио: "Вместо страшных дробей... квадрат" (до 136.46)
        expr_step1 = MathTex(r"(3 + \sqrt{5})^2 - (-\sqrt{6})^2").scale(1.5)
        self.play(Write(expr_step1))
        self.sync_to(136.46)
        
        # Аудио: "раскрываем... результат 8 + 6 корней из 5" (до 144.82)
        expr_step2 = MathTex(r"(9 + 6\sqrt{5} + 5) - 6").scale(1.5)
        self.play(FadeTransform(expr_step1, expr_step2))
        self.sync_to(139.5) 
        
        expr_step3 = MathTex(r"8 + 6\sqrt{5}").scale(1.5)
        self.play(FadeTransform(expr_step2, expr_step3))
        self.sync_to(144.82)
        
        # Аудио: "Запомним это число" (до 146.64)
        left_res_keeper = MathTex(r"\text{Левая часть} = 8 + 6\sqrt{5}").to_edge(UP).set_color(BLUE)
        self.play(Transform(self.mobjects[0], left_res_keeper))
        self.sync_to(146.64)
        self.clear()

        # === СЦЕНА 7: АНАЛИЗ ПРАВОЙ ЧАСТИ ===
        # Аудио: "А теперь... Правая часть уравнения" (146.64 - 150.66)
        step_title = Text("Шаг 4: Анализ правой части", font_size=42, color=BLUE).to_edge(UP)
        self.play(Write(step_title))
        self.sync_to(150.66)
        
        # Аудио: "2 умножить... избавиться" (до 155.0)
        big_root = MathTex(r"\sqrt{61 + 24\sqrt{5}}").scale(1.5)
        self.play(Write(big_root))
        question = Text("Как избавиться от внешнего корня?", font_size=32, color=YELLOW).next_to(big_root, DOWN, buff=1)
        self.play(Write(question))
        self.sync_to(155.0)
        
        # Аудио: "Логика проста... полным квадратом" (до 162.98)
        logic_group = VGroup()
        rule = MathTex(r"\sqrt{X^2} = X").scale(1.2)
        rule.set_color(GREEN)
        explanation = Text("Корень уходит, только если внутри — полный квадрат!", font_size=28).next_to(rule, DOWN)
        logic_box = VGroup(rule, explanation).arrange(DOWN).next_to(question, DOWN, buff=0.5)
        
        self.play(FadeIn(logic_box))
        self.sync_to(162.98)
        
        self.play(
            FadeOut(question), 
            FadeOut(logic_box),
            big_root.animate.move_to(UP * 2)
        )
        
        # Аудио: "Давайте предположим... а плюс б корней из 5" (до 170.36)
        hypothesis_text = Text("Значит, под корнем скрыт квадрат суммы:", font_size=32).next_to(big_root, DOWN)
        hypothesis_math = MathTex(r"61 + 24\sqrt{5}", r"=", r"(a + b\sqrt{5})^2").scale(1.4).next_to(hypothesis_text, DOWN)
        hypothesis_math[2].set_color(GOLD)
        
        self.play(Write(hypothesis_text))
        self.play(Write(hypothesis_math))
        self.sync_to(170.36)
        
        # Аудио: "Раскроем... уравнения" (до 176.86)
        expanded = MathTex(r"=", r"a^2 + 5b^2", r"+", r"2ab\sqrt{5}").scale(1.4).next_to(hypothesis_math[0], RIGHT)
        expanded.align_to(hypothesis_math[1], LEFT) 
        
        self.play(TransformMatchingShapes(hypothesis_math[2], expanded))
        self.sync_to(176.86)
        
        # === СОПОСТАВЛЕНИЕ КОЭФФИЦИЕНТОВ ===
        self.clear()
        self.add(step_title) 
        
        source_expr = MathTex(r"61", r" + ", r"24\sqrt{5}").scale(1.5).shift(UP*1.5)
        source_expr[0].set_color(YELLOW) 
        source_expr[2].set_color(ORANGE) 
        
        template_expr = MathTex(r"(a^2 + 5b^2)", r" + ", r"(2ab)\sqrt{5}").scale(1.5).next_to(source_expr, DOWN, buff=0.8)
        template_expr[0].set_color(YELLOW)
        template_expr[2].set_color(ORANGE)
        
        # Аудио: "Целая часть... сумма квадратов" (до 183.62)
        self.play(Write(source_expr))
        self.play(Write(template_expr))
        arrow1 = Arrow(start=source_expr[0].get_bottom(), end=template_expr[0].get_top(), color=YELLOW)
        self.play(GrowArrow(arrow1))
        self.sync_to(183.62)
        
        # Аудио: "А иррациональная... произведение" (до 189.54)
        arrow2 = Arrow(start=source_expr[2].get_bottom(), end=template_expr[2].get_top(), color=ORANGE)
        self.play(GrowArrow(arrow2))
        self.sync_to(189.54)
        
        # Аудио: "Мы получаем... Из второго... 12" (до 196.36)
        system = MathTex(
            r"\begin{cases} "
            r"a^2 + 5b^2 = 61 \\ "
            r"2ab = 24 "
            r"\end{cases}"
        ).scale(1.3).next_to(template_expr, DOWN, buff=1)
        
        system[0][1:10].set_color(YELLOW)
        system[0][10:19].set_color(ORANGE)
        
        self.play(Write(system))
        self.sync_to(196.36)
        
        # === СЦЕНА 8: РЕШЕНИЕ СИСТЕМЫ ===
        # Аудио: "Какие целые числа... Один и двенадцать... 3,4... Не подходит" (до 213.46)
        self.clear()
        solve_title = Text("Подбор целых чисел", font_size=36).to_edge(UP)
        self.play(Write(solve_title))
        
        logic_steps = VGroup(
            MathTex(r"2ab = 24 \Rightarrow ab = 12"),
            Text("Возможные пары (a, b):", font_size=28),
            MathTex(r"(1, 12) \rightarrow 1^2 + 5(12)^2 \neq 61"),
            MathTex(r"(2, 6) \rightarrow 2^2 + 5(6)^2 \neq 61"),
            MathTex(r"(3, 4) \rightarrow 3^2 + 5(4)^2 = 89 \neq 61"),
            MathTex(r"(4, 3) \rightarrow 4^2 + 5(3)^2 = 16 + 45 = 61 \quad \checkmark").set_color(GREEN)
        ).arrange(DOWN, buff=0.4)
        
        self.play(Write(logic_steps[0]))
        self.play(FadeIn(logic_steps[1]))
        self.play(Write(logic_steps[2]), Write(logic_steps[3]), Write(logic_steps[4]))
        self.sync_to(213.46)
        
        # Аудио: "А вот 4,3... Бинго" (до 219.2)
        self.play(Write(logic_steps[5]))
        self.sync_to(219.2)
        
        # Аудио: "Значит... 4 плюс 3 корня из пяти" (до 223.54)
        final_extract = MathTex(r"\sqrt{61 + 24\sqrt{5}} = 4 + 3\sqrt{5}").scale(1.3).set_color(GOLD)
        self.play(ReplacementTransform(logic_steps, final_extract))
        self.sync_to(223.54)
        
        # Аудио: "Умножаем на двойку... 8 плюс 6 корней" (до 231.12)
        final_right = MathTex(r"2(4 + 3\sqrt{5}) = 8 + 6\sqrt{5}").scale(1.3).next_to(final_extract, DOWN)
        self.play(Write(final_right))
        self.sync_to(231.12)

        # === СЦЕНА 9: ФИНАЛ ===
        # Аудио: "Момент истины... то же самое" (до 238.38)
        self.clear()
        
        left_part = MathTex(r"\text{Левая часть: } 8 + 6\sqrt{5}")
        right_part = MathTex(r"\text{Правая часть: } 8 + 6\sqrt{5}")
        
        comparison_group = VGroup(left_part, right_part).arrange(RIGHT, buff=2)
        comparison_group.to_edge(UP, buff=2)
        
        line = Line(LEFT, RIGHT).match_width(comparison_group).scale(1.2)
        line.next_to(comparison_group, DOWN, buff=1)
        
        check_mark = Text("✔", color=GREEN, font_size=96).next_to(line, DOWN, buff=0.5)
        qed = Text(r"Что требовалось доказать").next_to(check_mark, DOWN, buff=0.3)
        
        self.play(Write(left_part), Write(right_part))
        self.sync_to(238.38)
        
        # Аудио: "Равенство доказано... строго" (до 243.56)
        self.play(Create(line))
        self.play(SpinInFromNothing(check_mark))
        self.sync_to(243.56)

        # Аудио: "Что и требовалось доказать" (до 245.48)
        self.play(Write(qed))
        self.sync_to(245.48)

        # === СЦЕНА 10: ВЫВОДЫ ===
        # Аудио: "Чему нас научил этот пример?" (до 247.28)
        self.clear()
        skills_header = Text("Чему учит эта задача?", font_size=42, weight=BOLD).to_edge(UP)
        self.play(Write(skills_header))
        self.sync_to(247.28)
        
        def create_skill_row(title, desc, color=WHITE):
            t = Text(title, font_size=32, color=color, weight=BOLD)
            d = Text(desc, font_size=24, color=GREY_A)
            grp = VGroup(t, d).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
            return grp

        s1 = create_skill_row("1. Стратегическое планирование", "Не бросайся в вычисления сразу. Оцени сложность.", BLUE)
        s2 = create_skill_row("2. Рационализация", "Корни в знаменателе — зло. Убирай их сопряжением.", TEAL)
        s3 = create_skill_row("3. Метод неопределенных коэффициентов", "Ищи структуру квадрата суммы (a+b)² в сложных корнях.", GOLD)
        
        skills_group = VGroup(s1, s2, s3).arrange(DOWN, aligned_edge=LEFT, buff=0.8).next_to(skills_header, DOWN, buff=0.8)
        
        # Аудио: "Во-первых... частям" (до 252.4)
        self.play(FadeIn(s1, shift=RIGHT*0.5))
        self.sync_to(252.4)

        # Аудио: "Во-вторых... в знаменателе" (до 259.2)
        self.play(FadeIn(s2, shift=RIGHT*0.5))
        self.sync_to(259.2)
        
        # Аудио: "И в-третьих... сложные корни" (до 265.5)
        self.play(FadeIn(s3, shift=RIGHT*0.5))
        self.sync_to(265.5)

        # === СЦЕНА 11: АРСЕНАЛ (ФОРМУЛЫ) ===
        # Аудио: "Вот ваш арсенал-формул... сохраняйте и пользуйтесь" (до 270.94)
        self.clear()
        
        base_title = Text("Необходимый арсенал", font_size=42, color=RED).to_edge(UP)
        self.play(Write(base_title))
        
        def create_formula_row(name, formula, color=WHITE):
            t = Text(name, font_size=28, color=GREY_A)
            f = MathTex(formula, color=color).scale(1.1)
            return VGroup(t, f).arrange(DOWN, buff=0.2)

        row1 = create_formula_row("1. Разность квадратов", r"a^2 - b^2 = (a-b)(a+b)", TEAL)
        row2 = create_formula_row("2. Квадрат суммы", r"(a+b)^2 = a^2 + 2ab + b^2", GOLD)
        row3 = create_formula_row("3. Свойства корней", r"(\sqrt{a})^2 = a, \quad \sqrt{a}\sqrt{b} = \sqrt{ab}", BLUE)

        grid = VGroup(row1, row2, row3).arrange(DOWN, buff=0.8).next_to(base_title, DOWN, buff=0.5)
        
        for row in grid:
            self.play(FadeIn(row[0]), Write(row[1]))
            
        self.sync_to(270.94)
        self.wait(2)
