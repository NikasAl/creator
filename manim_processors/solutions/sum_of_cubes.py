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

class SumOfCubesDetective(Scene):
    def construct(self):
        # === ЧАСТЬ 1: ВСТУПЛЕНИЕ (00:00 - 00:28) ===
        # [00:00] Добро пожаловать...
        title = Text("Задача №1.152", font_size=42, weight=BOLD).to_edge(UP)
        self.play(Write(title), run_time=2)
        
        # Ждем фразы "В этой задаче нам даны..." [00:13]
        self.wait(11) 

        # [00:13 - 00:22] Дано: сумма 11, произведение 21
        problem_tex = MathTex(
            r"\text{Дано: } \begin{cases} a + b = 11 \\ a \cdot b = 21 \end{cases}"
        ).scale(1.2).shift(UP * 0.5)
        self.play(Write(problem_tex), run_time=3)
        
        # Ждем фразы "Наша цель..." [00:22.9]
        self.wait(1) 

        # [00:23 - 00:28] Найти a^3 + b^3
        target_tex = MathTex(r"\text{Найти: } a^3 + b^3 = ?").scale(1.2).next_to(problem_tex, DOWN, buff=1)
        target_tex.set_color(YELLOW)
        self.play(Write(target_tex), run_time=2)
        
        # Ждем конца вступления "...безобидно, правда?" [00:28]
        self.wait(2)

        # === ЧАСТЬ 2: ТУПИК (00:28 - 01:22) ===
        # [00:28] Первое желание... Убираем условие в угол
        given_group = VGroup(
            MathTex(r"a+b=11").set_color(BLUE),
            MathTex(r"ab=21").set_color(TEAL)
        ).arrange(DOWN).to_edge(UL).scale(0.8)

        self.play(
            FadeOut(title),
            ReplacementTransform(problem_tex, given_group),
            FadeOut(target_tex),
            run_time=2
        )
        
        # Ждем фразы "Узнать кто такие..." [00:34]
        self.wait(4)

        path1_title = Text("Попытка 1: Найти числа a и b", font_size=36, color=RED).to_edge(UP)
        self.play(Write(path1_title), run_time=1.5)

        # Ждем "Выразим Б через А..." [00:40.9]
        self.wait(4)
        
        step1 = MathTex(r"b = 11 - a").next_to(path1_title, DOWN, buff=1)
        self.play(Write(step1), run_time=1)

        # Ждем "и подставим во второе" [00:44.3]
        self.wait(2)
        
        step2 = MathTex(r"a(11 - a) = 21").next_to(step1, DOWN)
        self.play(Write(step2), run_time=1.5)

        # Ждем "получаем стандартное квадратное" [00:46]
        step3 = MathTex(r"a^2 - 11a + 21 = 0").next_to(step2, DOWN)
        self.play(TransformMatchingShapes(step2.copy(), step3), run_time=1.5)

        # Ждем "Но давайте посчитаем дискриминант" [00:50.6]
        self.wait(1.5)

        # [00:51 - 00:61] Расчет дискриминанта
        discrim = MathTex(r"D = (-11)^2 - 4\cdot 21 = 121 - 84 = 37").next_to(step3, DOWN)
        self.play(Write(discrim), run_time=4) # Медленно пишем, пока голос считает
        self.wait(6) # Ждем пока голос скажет "Корень не извлекается" [00:64]

        # [00:65 - 00:74] Появление страшных корней
        roots = MathTex(r"a_{1,2} = \frac{11 \pm \sqrt{37}}{2}").next_to(discrim, DOWN, buff=0.5).scale(1.2)
        roots.set_color(RED_B)
        self.play(Write(roots), run_time=2)
        
        # Ждем фразы "Вы действительно хотите возводить..." [00:74.4]
        self.wait(2)
        
        horror_text = Text("И это возводить в куб?!", font_size=32, color=RED).next_to(roots, DOWN)
        self.play(Write(horror_text), run_time=1)
        
        # Ждем "Тупик." [00:81]
        self.wait(4)

        # Перечеркиваем
        cross_group = VGroup(step1, step3, discrim, roots, horror_text)
        cross = Cross(cross_group).set_color(RED)
        self.play(Create(cross), run_time=0.5)
        
        # Ждем "Остановимся." [00:82]
        self.wait(1)
        self.play(FadeOut(path1_title), FadeOut(cross_group), FadeOut(cross), FadeOut(step2), run_time=1)

        # === ЧАСТЬ 3: ОЗАРЕНИЕ (01:23 - 02:24) ===
        # [00:83] Умный математик...
        path2_title = Text("Попытка 2: Алгебраическая хитрость", font_size=36, color=GREEN).to_edge(UP)
        self.play(Write(path2_title), run_time=2)

        # [00:86] Давайте вспомним формулу
        idea_text = Text("Мы помним формулу куба суммы:", font_size=28, color=GRAY).next_to(path2_title, DOWN)
        self.play(Write(idea_text), run_time=1.5)

        # [00:88 - 01:00] Пишем длинную формулу под диктовку
        cube_formula = MathTex(
            r"(a+b)^3", r"=", r"a^3", r"+", r"3a^2b", r"+", r"3ab^2", r"+", r"b^3"
        ).scale(1.2)
        # Медленное появление в такт словам "А в кубе... плюс 3 а квадрат б..."
        self.play(Write(cube_formula), run_time=10) 
        
        # Ждем "Взгляните на середину" [01:01.5]
        self.wait(1)

        # [01:03] Подсветка "3 а квадрат..."
        middle_part = VGroup(cube_formula[4], cube_formula[5], cube_formula[6])
        self.play(middle_part.animate.set_color(TEAL), run_time=1)
        
        # Ждем "сокровище" и "вынести за скобку" [01:10.5]
        self.wait(5)
        
        brace = Brace(middle_part, DOWN)
        factor_text = MathTex(r"3ab(a+b)").next_to(brace, DOWN).set_color(TEAL)
        self.play(GrowFromCenter(brace), Write(factor_text), run_time=2)

        # Ждем "Снова наша сумма..." [01:17] и переход к группировке [01:20]
        self.wait(4)

        grouped_formula = MathTex(
            r"(a+b)^3", r"=", r"(a^3 + b^3)", r"+", r"3ab(a+b)"
        ).scale(1.2)
        grouped_formula[2].set_color(YELLOW)
        grouped_formula[4].set_color(TEAL)

        self.play(
            FadeOut(brace), 
            FadeOut(factor_text), 
            ReplacementTransform(cube_formula, grouped_formula),
            run_time=2
        )

        # Ждем "Теперь дело техники... срезать путь" [01:26 - 01:41]
        # В этот момент на экране формула куба суммы, зритель осознает
        self.wait(18)

        # [01:44] Подставляем наши значения (Переход к финалу)
        final_formula = MathTex(
            r"a^3 + b^3", r"=", r"(a+b)^3", r"-", r"3ab(a+b)"
        ).scale(1.3)
        # Красим под данные: Сумма (Синий), Произведение (Бирюзовый)
        final_formula[0].set_color(YELLOW)
        final_formula[2].set_color(BLUE) 
        final_formula[4][1:3].set_color(TEAL)
        final_formula[4][4:].set_color(BLUE)

        calc_title = Text("Подставляем числа", font_size=36).to_edge(UP)
        
        self.play(
            ReplacementTransform(path2_title, calc_title), 
            FadeOut(idea_text),
            TransformMatchingShapes(grouped_formula, final_formula),
            run_time=2
        )

        # === ЧАСТЬ 4: ВЫЧИСЛЕНИЕ (02:26 - КОНЕЦ) ===
        # Напоминаем условия. Голос: "Вместо суммы 11..." [01:46.8]
        self.play(given_group.animate.scale(1.2).next_to(calc_title, DOWN, buff=0.5).arrange(RIGHT, buff=1), run_time=1.5)
        # self.wait(2)
        self.play(FadeOut(given_group)) # Убираем, чтобы не мешало

        # [01:52] "11 в кубе..."
        substitution = MathTex(
            r"a^3 + b^3", r"=", r"11^3", r"-", r"3 \cdot 21 \cdot 11"
        ).scale(1.2)
        substitution[2].set_color(BLUE)
        substitution[4][2:4].set_color(TEAL)
        substitution[4][5:].set_color(BLUE)

        self.play(ReplacementTransform(final_formula, substitution), run_time=2)
        
        # Ждем "Вычитаем..." [01:56.8]
        self.wait(2)

        # [02:01] "1331 минус..."
        calc_step1 = MathTex(
            r"=", r"1331", r"-", r"693"
        ).scale(1.2).next_to(substitution, DOWN)
        
        self.play(Write(calc_step1), run_time=3)
        
        # Ждем "И получаем..." [02:04]
        self.wait(1)

        final_answer = MathTex(r"638").scale(2).set_color(GREEN).next_to(calc_step1, DOWN, buff=0.5)
        box = SurroundingRectangle(final_answer, color=GREEN, buff=0.2)
        
        # [02:07] Появление ответа
        self.play(Write(final_answer), Create(box), run_time=1.5)
        
        # [02:09] Итог "Задача решена..."
        summary = Text("Ответ: 638", font_size=48, weight=BOLD).set_color(GREEN)
        self.wait(2)
        self.clear()
        self.play(Write(summary))
        self.play(Circumscribe(summary))
        self.wait(4)