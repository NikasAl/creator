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
    SHORT_PAUSE = 2
    LONG_PAUSE = 3
    
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
    
    def show_step_by_step(self, expressions, scale_factor=1.2):
        """
        Показывает выражения по одному.
        Использует FadeTransform, так как он лучше справляется 
        с резким изменением формы (например, дробь -> число), 
        чем TransformMatchingShapes.
        """
        current_obj = None
        for expr in expressions:
            obj = MathTex(expr).scale(scale_factor)
            obj = self.fit_to_screen(obj)
            
            if current_obj is None:
                self.play(Write(obj))
            else:
                # ИСПРАВЛЕНИЕ ЗДЕСЬ:
                # FadeTransform принудительно "растворяет" куски, которые не совпали.
                # Это убирает "призраков" при упрощении дробей.
                self.play(FadeTransform(current_obj, obj))
            
            self.wait(self.SHORT_PAUSE)
            current_obj = obj
        return current_obj

    def construct(self):
        # === СЦЕНА 1: ВСТУПЛЕНИЕ ===
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
        self.play(FadeIn(equation, shift=UP))
        self.play(Write(comment))
        self.wait(self.LONG_PAUSE)
        
        # === СЦЕНА 2: ГИПОТЕЗА 0 (ТУПИК) ===
        self.clear()
        hypothesis_title = Text("Путь 1: Лобовая атака", font_size=42, color=RED).to_edge(UP)
        hypothesis_text = Text("Возвести дроби в квадрат сразу?", font_size=32).next_to(hypothesis_title, DOWN)
        
        self.play(Write(hypothesis_title), Write(hypothesis_text))
        
        bad_math = MathTex(
            r"\frac{16}{14 - 6\sqrt{5}} - \frac{186 - 60\sqrt{6}}{31 - 10\sqrt{6}}"
        ).scale(1.2)
        self.play(Write(bad_math))
        self.wait(1)
        
        cross = Cross(bad_math).set_color(RED)
        warning = Text("Слишком сложные вычисления!", font_size=36, color=RED).next_to(cross, DOWN)
        
        self.play(Create(cross))
        self.play(Write(warning))
        self.wait(self.LONG_PAUSE)
        
        # === СЦЕНА 3: ПЛАН ===
        self.clear()
        plan_title = Text("Путь 2: Стратегия упрощения", font_size=42, color=GREEN).to_edge(UP)
        steps = VGroup(
            Text("1. Упростить знаменатели (избавиться от корней)", font_size=32),
            Text("2. Возвести упрощенные дроби в квадрат", font_size=32),
            Text("3. Преобразовать правую часть (выделить полный квадрат)", font_size=32)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        
        self.play(Write(plan_title))
        self.play(Write(steps), run_time=3)
        self.wait(self.LONG_PAUSE)
        
        # === СЦЕНА 4: ДРОБЬ 1 (С ПОЯСНЕНИЯМИ) ===
        self.clear()
        step_title = Text("Шаг 1: Первая дробь", font_size=42, color=BLUE).to_edge(UP)
        self.play(Write(step_title))
        
        frac1 = MathTex(r"\frac{4}{3 - \sqrt{5}}").scale(1.5)
        self.play(Write(frac1))
        self.wait(1)
        
        # Проблема
        problem_arrow = Arrow(start=frac1.get_bottom(), end=frac1.get_bottom() + DOWN, color=RED)
        problem_text = Text("Иррациональность внизу", font_size=24, color=RED).next_to(problem_arrow, DOWN)
        self.play(GrowArrow(problem_arrow), FadeIn(problem_text))
        self.wait(1)
        self.play(FadeOut(problem_arrow), FadeOut(problem_text))
        
        # Домножение
        self.play(frac1.animate.shift(LEFT * 2))
        
        conjugate_fraction = MathTex(r"\cdot \frac{3 + \sqrt{5}}{3 + \sqrt{5}}").scale(1.5)
        conjugate_fraction.next_to(frac1, RIGHT)
        conjugate_fraction[0][1:].set_color(YELLOW) 
        
        conj_label = Text("Сопряженное выражение", font_size=24, color=YELLOW).next_to(conjugate_fraction, UP)
        conj_desc = Text("(меняем минус на плюс)", font_size=20, color=GREY).next_to(conj_label, DOWN)
        
        self.play(Write(conjugate_fraction))
        self.play(FadeIn(conj_label), FadeIn(conj_desc))
        self.wait(2)
        self.play(FadeOut(conj_label), FadeOut(conj_desc))
        
        # Объединяем в одну длинную дробь
        long_frac = MathTex(r"\frac{4(3 + \sqrt{5})}{(3)^2 - (\sqrt{5})^2}").scale(1.5)
        long_frac[0][2:7].set_color(YELLOW) 
        
        # ИСПРАВЛЕНИЕ: Используем FadeTransform вместо TransformMatchingShapes
        # Это уберет "кашу" при слиянии дробей
        self.play(FadeTransform(VGroup(frac1, conjugate_fraction), long_frac))
        self.wait(1)
        self.play(FadeOut(long_frac))

        final_val = self.show_step_by_step([
             r"\frac{4(3 + \sqrt{5})}{9 - 5}",
             r"\frac{4(3 + \sqrt{5})}{4}",
             r"3 + \sqrt{5}"
        ], scale_factor=1.5)

        self.wait(self.LONG_PAUSE)

        # === СЦЕНА 5: ДРОБЬ 2 ===
        self.clear()
        step2_title = Text("Шаг 2: Вторая дробь", font_size=42, color=TEAL).to_edge(UP)
        self.play(Write(step2_title))
        
        frac2 = MathTex(r"\frac{6 - 5\sqrt{6}}{5 - \sqrt{6}}").scale(1.5).shift(LEFT * 2)
        self.play(Write(frac2))
        
        conjugate_fraction2 = MathTex(r"\cdot \frac{5 + \sqrt{6}}{5 + \sqrt{6}}").scale(1.5).next_to(frac2, RIGHT)
        conjugate_fraction2[0][1:].set_color(TEAL)
        
        conj_label2 = Text("Домножаем на сопряженное", font_size=24, color=TEAL).next_to(conjugate_fraction2, UP)
        
        self.play(Write(conjugate_fraction2), FadeIn(conj_label2))
        self.wait(1)
        self.play(FadeOut(conj_label2))
        
        # Схлопывание дробей
        long_frac2 = MathTex(r"\frac{(6 - 5\sqrt{6})(5 + \sqrt{6})}{25 - 6}").scale(1.3)
        long_frac2[0][8:14].set_color(TEAL)
        
        # ИСПРАВЛЕНИЕ: Тоже меняем на FadeTransform
        self.play(FadeTransform(VGroup(frac2, conjugate_fraction2), long_frac2))
        self.wait(1)
        self.play(FadeOut(long_frac2))

        final_val2 = self.show_step_by_step([
            r"\frac{30 + 6\sqrt{6} - 25\sqrt{6} - 30}{19}",
            r"\frac{-19\sqrt{6}}{19}",
            r"-\sqrt{6}"
        ], scale_factor=1.5)

        self.wait(self.LONG_PAUSE)

        # === СЦЕНА 6: СБОРКА ЛЕВОЙ ЧАСТИ ===
        self.clear()
        step3 = Text("Шаг 3: Подставляем в левую часть", font_size=36).to_edge(UP)
        self.play(Write(step3))
        
        self.show_step_by_step([
            r"(3 + \sqrt{5})^2 - (-\sqrt{6})^2",
            r"(9 + 6\sqrt{5} + 5) - 6",
            r"14 + 6\sqrt{5} - 6",
            r"8 + 6\sqrt{5}"
        ], scale_factor=1.5)
        
        left_res_keeper = MathTex(r"\text{Левая часть} = 8 + 6\sqrt{5}").to_edge(UP).set_color(BLUE)
        self.play(Transform(self.mobjects[0], left_res_keeper))
        self.wait(1)
        self.clear()

        # === СЦЕНА 7: АНАЛИЗ ПРАВОЙ ЧАСТИ ===
        self.clear()
        step_title = Text("Шаг 4: Анализ правой части", font_size=42, color=BLUE).to_edge(UP)
        self.play(Write(step_title))
        
        big_root = MathTex(r"\sqrt{61 + 24\sqrt{5}}").scale(1.5)
        self.play(Write(big_root))
        self.wait(1)
        
        question = Text("Как избавиться от внешнего корня?", font_size=32, color=YELLOW).next_to(big_root, DOWN, buff=1)
        self.play(Write(question))
        self.wait(1)
        
        logic_group = VGroup()
        rule = MathTex(r"\sqrt{X^2} = X").scale(1.2)
        rule.set_color(GREEN)
        explanation = Text("Корень уходит, только если внутри — полный квадрат!", font_size=28).next_to(rule, DOWN)
        logic_box = VGroup(rule, explanation).arrange(DOWN).next_to(question, DOWN, buff=0.5)
        
        self.play(FadeIn(logic_box))
        self.wait(2)
        
        self.play(
            FadeOut(question), 
            FadeOut(logic_box),
            big_root.animate.move_to(UP * 2)
        )
        
        hypothesis_text = Text("Значит, под корнем скрыт квадрат суммы:", font_size=32).next_to(big_root, DOWN)
        hypothesis_math = MathTex(r"61 + 24\sqrt{5}", r"=", r"(a + b\sqrt{5})^2").scale(1.4).next_to(hypothesis_text, DOWN)
        hypothesis_math[2].set_color(GOLD)
        
        self.play(Write(hypothesis_text))
        self.play(Write(hypothesis_math))
        self.wait(2)
        
        expanded = MathTex(r"=", r"a^2 + 5b^2", r"+", r"2ab\sqrt{5}").scale(1.4).next_to(hypothesis_math[0], RIGHT)
        expanded.align_to(hypothesis_math[1], LEFT) 
        
        self.play(TransformMatchingShapes(hypothesis_math[2], expanded))
        self.wait(2)
        
        # === СОПОСТАВЛЕНИЕ КОЭФФИЦИЕНТОВ ===
        self.clear()
        self.add(step_title) # ИСПРАВЛЕНО: step_title вместо step4
        
        source_expr = MathTex(r"61", r" + ", r"24\sqrt{5}").scale(1.5).shift(UP*1.5)
        source_expr[0].set_color(YELLOW) 
        source_expr[2].set_color(ORANGE) 
        
        template_expr = MathTex(r"(a^2 + 5b^2)", r" + ", r"(2ab)\sqrt{5}").scale(1.5).next_to(source_expr, DOWN, buff=0.8)
        template_expr[0].set_color(YELLOW)
        template_expr[2].set_color(ORANGE)
        
        arrow1 = Arrow(start=source_expr[0].get_bottom(), end=template_expr[0].get_top(), color=YELLOW)
        arrow2 = Arrow(start=source_expr[2].get_bottom(), end=template_expr[2].get_top(), color=ORANGE)
        
        self.play(Write(source_expr))
        self.play(Write(template_expr))
        self.play(GrowArrow(arrow1), GrowArrow(arrow2))
        self.wait(1)
        
        system = MathTex(
            r"\begin{cases} "
            r"a^2 + 5b^2 = 61 \\ "
            r"2ab = 24 "
            r"\end{cases}"
        ).scale(1.3).next_to(template_expr, DOWN, buff=1)
        
        system[0][1:10].set_color(YELLOW)
        system[0][10:19].set_color(ORANGE)
        
        self.play(Write(system))
        self.wait(self.LONG_PAUSE)
        
        # === СЦЕНА 8: РЕШЕНИЕ СИСТЕМЫ ===
        self.clear()
        solve_title = Text("Подбор целых чисел", font_size=36).to_edge(UP)
        self.play(Write(solve_title))
        
        logic_steps = VGroup(
            MathTex(r"2ab = 24 \Rightarrow ab = 12"),
            Text("Возможные пары (a, b):", font_size=28),
            MathTex(r"(1, 12) \rightarrow 1^2 + 5(12)^2 = 721 \neq 61"),
            MathTex(r"(2, 6) \rightarrow 2^2 + 5(6)^2 = 184 \neq 61"),
            MathTex(r"(3, 4) \rightarrow 3^2 + 5(4)^2 = 89 \neq 61"),
            MathTex(r"(4, 3) \rightarrow 4^2 + 5(3)^2 = 16 + 45 = 61 \quad \checkmark").set_color(GREEN)
        ).arrange(DOWN, buff=0.4)
        
        self.play(Write(logic_steps[0]))
        self.play(FadeIn(logic_steps[1]))
        
        for step in logic_steps[2:]:
            self.play(Write(step), run_time=0.8)
        
        self.wait(1)
        
        final_extract = MathTex(r"\sqrt{61 + 24\sqrt{5}} = 4 + 3\sqrt{5}").scale(1.3).set_color(GOLD)
        self.play(ReplacementTransform(logic_steps, final_extract))
        self.wait(1)
        
        final_right = MathTex(r"2(4 + 3\sqrt{5}) = 8 + 6\sqrt{5}").scale(1.3).next_to(final_extract, DOWN)
        self.play(Write(final_right))
        self.wait(self.LONG_PAUSE)

        # === СЦЕНА 9: ФИНАЛ (ИСПРАВЛЕННАЯ) ===
        self.clear()
        
        # Создаем надписи
        left_part = MathTex(r"\text{Левая часть: } 8 + 6\sqrt{5}")
        right_part = MathTex(r"\text{Правая часть: } 8 + 6\sqrt{5}")
        
        # Группируем их, чтобы выровнять симметрично относительно центра
        comparison_group = VGroup(left_part, right_part).arrange(RIGHT, buff=2)
        comparison_group.to_edge(UP, buff=2)
        
        # Создаем разделительную черту на всю ширину текста
        # Line(LEFT, RIGHT) создает линию длиной 2 единицы, мы ее растягиваем
        line = Line(LEFT, RIGHT).match_width(comparison_group).scale(1.2)
        line.next_to(comparison_group, DOWN, buff=1)
        
        # Галочка по центру линии
        check_mark = Text("✔", color=GREEN, font_size=96).next_to(line, DOWN, buff=0.5)
        
        # Q.E.D. под галочкой
        qed = Text(r"Что требовалось доказать").next_to(check_mark, DOWN, buff=0.3)
        
        # Анимация
        self.play(Write(left_part), Write(right_part))
        self.play(Create(line))
        self.play(SpinInFromNothing(check_mark))
        self.play(Write(qed))
        
        self.wait(3)        
        # === СЦЕНА 10: ВЫВОДЫ ===
        self.clear()
        
        skills_header = Text("Чему учит эта задача?", font_size=42, weight=BOLD).to_edge(UP)
        self.play(Write(skills_header))
        
        def create_skill_row(title, desc, color=WHITE):
            t = Text(title, font_size=32, color=color, weight=BOLD)
            d = Text(desc, font_size=24, color=GREY_A)
            grp = VGroup(t, d).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
            return grp

        s1 = create_skill_row("1. Стратегическое планирование", "Не бросайся в вычисления сразу. Оцени сложность.", BLUE)
        s2 = create_skill_row("2. Рационализация", "Корни в знаменателе — зло. Убирай их сопряжением.", TEAL)
        s3 = create_skill_row("3. Метод неопределенных коэффициентов", "Ищи структуру квадрата суммы (a+b)² в сложных корнях.", GOLD)
        
        skills_group = VGroup(s1, s2, s3).arrange(DOWN, aligned_edge=LEFT, buff=0.8).next_to(skills_header, DOWN, buff=0.8)
        
        for skill in skills_group:
            self.play(FadeIn(skill, shift=RIGHT*0.5))
            self.wait(1)
            
        self.wait(3)

        self.wait(3)

        # === СЦЕНА 11: НЕОБХОДИМЫЙ АРСЕНАЛ (НОВАЯ) ===
        self.clear()
        
        base_title = Text("Что нужно знать для этой задачи?", font_size=42, color=RED).to_edge(UP)
        self.play(Write(base_title))
        
        def create_formula_row(name, formula, color=WHITE):
            # Создаем группу: Текст слева, Формула справа (или под ним)
            t = Text(name, font_size=28, color=GREY_A)
            f = MathTex(formula, color=color).scale(1.1)
            return VGroup(t, f).arrange(DOWN, buff=0.2)

        # 1. Разность квадратов (для сопряженного)
        row1 = create_formula_row("1. Разность квадратов", r"a^2 - b^2 = (a-b)(a+b)", TEAL)
        
        # 2. Квадрат суммы (для корня)
        row2 = create_formula_row("2. Квадрат суммы", r"(a+b)^2 = a^2 + 2ab + b^2", GOLD)
        
        # 3. Арифметика корней
        row3 = create_formula_row("3. Свойства корней", r"(\sqrt{a})^2 = a, \quad \sqrt{a}\sqrt{b} = \sqrt{ab}", BLUE)

        # Выстраиваем их в список
        grid = VGroup(row1, row2, row3).arrange(DOWN, buff=0.8).next_to(base_title, DOWN, buff=0.5)
        
        for row in grid:
            self.play(FadeIn(row[0]), Write(row[1]))
            self.wait(0.5)
            
        self.wait(3)