from manim import *

# Настройка LaTeX для кириллицы
config.tex_template = TexTemplate(
    documentclass=r"\documentclass[preview]{standalone}",
    preamble=r"""
    \usepackage{amsmath}
    \usepackage{amsfonts}
    \usepackage{amssymb}
    \usepackage{mathtools}
    \usepackage{fontspec}
    \setmainfont{DejaVu Serif}
    \setsansfont{DejaVu Sans}
    """,
    tex_compiler="lualatex",
)

class PythagorasProofPart1(Scene):
    def construct(self):
        # === ШАГ 1: Заголовок ===
        title = Text("Доказательство теоремы Пифагора", font_size=48, color=BLUE)
        self.play(Write(title), run_time=2)
        self.wait(1)
        self.play(title.animate.to_edge(UP).scale(0.6), run_time=0.5)
        self.wait(0.2)

        # === ШАГ 2: Показываем треугольник для иллюстрации теоремы ===
        a = 2.0
        b = 3.0
        c = (a**2 + b**2)**0.5  # гипотенуза

        # Простой треугольник для иллюстрации
        triangle = Polygon(
            [0, 0, 0],
            [b, 0, 0],
            [0, a, 0],
            fill_opacity=0.7,
            color=YELLOW,
            stroke_color=YELLOW,
            stroke_width=3
        )

        label_a = MathTex("a").next_to(triangle, LEFT, buff=0.2)
        label_b = MathTex("b").next_to(triangle, DOWN, buff=0.2)
        label_c = MathTex("c").next_to(triangle.get_center(), UR, buff=0.2)

        triangle_group = VGroup(triangle, label_a, label_b, label_c)

        formula = MathTex("a^2 + b^2 = c^2", color=BLUE).scale(0.9).next_to(triangle_group, DOWN, buff=0.5)
        to_prove = Tex("Требуется доказать это утверждение", color=GRAY).scale(0.7).next_to(formula, DOWN, buff=0.2)

        self.play(Create(triangle_group), run_time=0.5)
        self.play(Write(formula), Write(to_prove))
        self.wait(0.2)

        # === ШАГ 3: Удаляем треугольник ===
        self.play(FadeOut(triangle_group), FadeOut(formula), FadeOut(to_prove), run_time=0.2)
        self.wait(0.1)

        # === ШАГ 4: Рисуем новый чертёж - большой квадрат со стороной (a+b) ===
        side_length = a + b  # = 5
        scale = 1.0  # масштаб для наглядности
        
        # Координаты углов большого квадрата (центрируем)
        offset = np.array([-side_length * scale / 2, -side_length * scale / 2, 0])
        
        # Углы внешнего квадрата
        A = np.array([0, 0, 0]) * scale + offset
        B = np.array([side_length, 0, 0]) * scale + offset
        C = np.array([side_length, side_length, 0]) * scale + offset
        D = np.array([0, side_length, 0]) * scale + offset
        
        # Точки деления на каждой стороне (на расстоянии b от начала)
        # Нижняя сторона: A -> B делится на b и a
        P1 = A + np.array([b, 0, 0]) * scale
        # Правая сторона: B -> C делится на b и a
        P2 = B + np.array([0, b, 0]) * scale
        # Верхняя сторона: C -> D делится на b и a (идём от C влево на b)
        P3 = C + np.array([-b, 0, 0]) * scale
        # Левая сторона: D -> A делится на b и a (идём от D вниз на b)
        P4 = D + np.array([0, -b, 0]) * scale

        # Рисуем внешний квадрат
        outer_square = Polygon(A, B, C, D, stroke_color=WHITE, stroke_width=3, fill_opacity=0)
        self.play(Create(outer_square), run_time=0.5)
        self.wait(0.2)

        # Отмечаем точки деления на сторонах
        dots = VGroup(
            Dot(P1, color=RED, radius=0.06),
            Dot(P2, color=RED, radius=0.06),
            Dot(P3, color=RED, radius=0.06),
            Dot(P4, color=RED, radius=0.06)
        )
        self.play(Create(dots), run_time=0.2)

        # === ШАГ 5: Добавляем метки a и b на сторонах ===
        # Нижняя сторона: сначала b, потом a
        label_b_bottom = MathTex("b", color=BLUE).scale(0.8).next_to((A + P1) / 2, DOWN, buff=0.15)
        label_a_bottom = MathTex("a", color=GREEN).scale(0.8).next_to((P1 + B) / 2, DOWN, buff=0.15)
        
        # Правая сторона: сначала b, потом a
        label_b_right = MathTex("b", color=BLUE).scale(0.8).next_to((B + P2) / 2, RIGHT, buff=0.15)
        label_a_right = MathTex("a", color=GREEN).scale(0.8).next_to((P2 + C) / 2, RIGHT, buff=0.15)
        
        # Верхняя сторона: сначала a, потом b
        label_a_top = MathTex("b", color=BLUE).scale(0.8).next_to((C + P3) / 2, UP, buff=0.15)
        label_b_top = MathTex("a", color=GREEN).scale(0.8).next_to((P3 + D) / 2, UP, buff=0.15)
        
        # Левая сторона: сначала a, потом b
        label_a_left = MathTex("b", color=BLUE).scale(0.8).next_to((D + P4) / 2, LEFT, buff=0.15)
        label_b_left = MathTex("a", color=GREEN).scale(0.8).next_to((P4 + A) / 2, LEFT, buff=0.15)

        side_labels = VGroup(
            label_b_bottom, label_a_bottom,
            label_b_right, label_a_right,
            label_a_top, label_b_top,
            label_a_left, label_b_left
        )
        
        self.play(Write(side_labels), run_time=0.5)
        self.wait(0.2)

        # === ШАГ 6: Соединяем точки - рисуем внутренний квадрат ===
        inner_square = Polygon(P1, P2, P3, P4, stroke_color=YELLOW, stroke_width=3, fill_opacity=0.3, fill_color=YELLOW)
        self.play(Create(inner_square), run_time=0.5)
        self.wait(0.2)

        # Добавляем метку c на одной из сторон внутреннего квадрата
        label_c_inner = MathTex("c", color=YELLOW).scale(0.9).next_to((P1 + P2) / 2, DR, buff=0.2)
        self.play(Write(label_c_inner), run_time=0.5)
        self.wait(0.5)

        # === Создаём группу из всей конструкции ===
        square_construction = VGroup(outer_square, dots, side_labels, inner_square, label_c_inner)
        
        # Двигаем конструкцию вправо для размещения текста слева
        self.play(square_construction.animate.scale(0.7).shift(RIGHT * 3.5), run_time=0.5)
        self.wait(0.2)

        # === ШАГ 7: Доказательство - текст и формулы ===
        
        # Текст: вычислим площадь квадрата двумя способами
        text1 = Tex(
            "Вычислим площадь квадрата со стороной $(a+b)$ двумя способами:",
            font_size=24
        ).to_edge(LEFT, buff=0.5).shift(UP * 2.5)
        self.play(Write(text1), run_time=1.5)
        self.wait(1)

        # Способ 1: площадь большого квадрата
        formula1 = MathTex("S = (a+b)^2 = a^2 + 2ab + b^2", color=BLUE).scale(0.6).next_to(text1, DOWN, buff=0.4, aligned_edge=LEFT)
        self.play(Write(formula1), run_time=1)
        self.wait(0.8)

        # Способ 2: площадь = 4 треугольника + внутренний квадрат
        text2 = Tex(
            "Или: 4 треугольника $+$ квадрат $c^2$:",
            font_size=24
        ).next_to(formula1, DOWN, buff=0.5, aligned_edge=LEFT)
        self.play(Write(text2), run_time=1.5)
        self.wait(0.5)

        # TODO: Подсветим треугольники на чертеже

        formula3 = MathTex("S = 4 \\cdot \\frac{1}{2}ab + c^2 = 2ab + c^2", color=GREEN).scale(0.6).next_to(text2, DOWN, buff=0.3, aligned_edge=LEFT)
        self.play(Write(formula3), run_time=1.2)
        self.wait(0.8)

        # Приравниваем два выражения
        text3 = Tex("Приравняем:", font_size=24).next_to(formula3, DOWN, buff=0.5, aligned_edge=LEFT)
        self.play(Write(text3), run_time=0.8)
        self.wait(0.3)

        formula5 = MathTex("a^2 + 2ab + b^2 = 2ab + c^2", color=YELLOW).scale(0.6).next_to(text3, DOWN, buff=0.3, aligned_edge=LEFT)
        self.play(Write(formula5), run_time=1.5)
        self.wait(1.5)

        # Сокращаем 2ab с обеих сторон
        text4 = Tex("Сократим $2ab$:", font_size=24).next_to(formula5, DOWN, buff=0.4, aligned_edge=LEFT)
        self.play(Write(text4), run_time=0.8)
        self.wait(0.3)

        # Финальная формула
        formula_final = MathTex("a^2 + b^2 = c^2", color=YELLOW).scale(1.2).next_to(text4, DOWN, buff=0.4, aligned_edge=LEFT)
        box = SurroundingRectangle(formula_final, color=YELLOW, buff=0.15, stroke_width=3)
        
        self.play(Write(formula_final), run_time=1.5)
        self.play(Create(box), run_time=0.8)
        self.wait(1)

        # Заключение
        conclusion = Tex("Теорема доказана!", font_size=28, color=GREEN)
        self.play(Write(conclusion), run_time=1)
        self.wait(3)
