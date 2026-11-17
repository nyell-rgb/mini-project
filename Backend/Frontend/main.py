import sys
from pathlib import Path
from collections.abc import Callable
import math
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
from tkinter import ttk


class RecipeKeeperApp:
    ACCENT = "#D14300"
    SIDEBAR = "#F3F3F3"
    WINDOW_BG = "#FAFAFA"
    SEARCH_BG = "#F9F9F9"
    TEXT = "#1A1A1A"
    MUTED = "#6E6E6E"
    PLACEHOLDER_FG = "#5F5F5F"
    PLACEHOLDER_TEXT = "Search recipes"
    FONT = "Inter"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.scale = self._screen_scale()
        self.FONT = self._pick_font()
        self.icons: dict[str, tk.PhotoImage] = {}
        self.recipes = [
            {
                "name": "Pancakes",
                "color": "#E2AE58",
                "ingredients": [
                    ("3 cups/375g", "all-purpose flour"),
                    ("3 teaspoons", "baking powder"),
                    ("1 tablespoon", "caster sugar"),
                    ("1 1/2 cups/375ml", "milk"),
                    ("3", "eggs"),
                    ("1/2 teaspoon", "salt"),
                ],
                "directions": [
                    "Sift the flour, baking powder, salt and caster sugar into a bowl.",
                    "Break the eggs into a separate bowl and whisk together with the milk.",
                    "Gradually add the milk and egg mixture to the flour mixture and whisk to a smooth batter.",
                    "Heat a frying pan over a medium heat and melt a small knob of butter. Pour the batter into the pan, using approximately 1/4 cup for each pancake.",
                    "When the top of the pancake begins to bubble, turn and cook the other side until golden brown.",
                    "Serve with butter and maple syrup.",
                ],
                "favorite": False,
            },
            {"name": "Cheesecake", "color": "#5E3B70", "ingredients": [], "directions": [], "favorite": False},
            {"name": "Spaghetti", "color": "#C94A2E", "ingredients": [], "directions": [], "favorite": False},
            {"name": "Cookies", "color": "#B8793A", "ingredients": [], "directions": [], "favorite": False},
            {"name": "Nasi Goreng", "color": "#D9A441", "ingredients": [], "directions": [], "favorite": False},
        ]
        self.recipe_colors = [str(recipe["color"]) for recipe in self.recipes]
        # Match the Figma heading even though its current grid shows five cards.
        self.recipe_count = 6
        self.active_tab = "Resep"
        self.current_view = "home"
        self.current_recipe: dict[str, object] | None = None
        self.editing_recipe: dict[str, object] | None = None
        self.search_placeholder = True
        self.is_maximized = False
        self.previous_geometry = ""
        self._drag_offset_x: int | None = None
        self._drag_offset_y: int | None = None
        self._load_icons()
        self._configure_window()
        self._build_window()
        self.root.after(50, self._enable_taskbar_icon)

    # ------------------------------------------------------------------ utils
    def _enable_taskbar_icon(self) -> None:
        """Windows: window tanpa frame (overrideredirect) tidak muncul di taskbar.
        Beri gaya WS_EX_APPWINDOW lalu map ulang window agar ikon taskbar muncul."""
        if sys.platform != "win32":
            return
        import ctypes

        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(self.root.winfo_id())
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        self.root.withdraw()
        self.root.after(10, self.root.deiconify)

    def _px(self, value: int) -> int:
        return max(1, round(value * self.scale))

    def _font(self, size: int) -> tuple[str, int]:
        return (self.FONT, -self._px(size))

    def _screen_scale(self) -> float:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        return min(1.0, (screen_width - 40) / 1317, (screen_height - 60) / 867)

    def _pick_font(self) -> str:
        """Pakai Inter jika terpasang, kalau tidak jatuh ke font yang tersedia."""
        available = set(tkfont.families(self.root))
        for name in (self.FONT, "Segoe UI", "Helvetica", "Arial", "DejaVu Sans"):
            if name in available:
                return name
        return "TkDefaultFont"

    def _load_icons(self) -> None:
        icon_dir = Path(__file__).resolve().parent / "assets" / "icons"
        for name in ("minimize", "maximize", "close", "menu", "search", "plus", "home"):
            try:
                self.icons[name] = tk.PhotoImage(
                    master=self.root,
                    file=str(icon_dir / f"{name}.png"),
                )
            except tk.TclError:
                # File ikon tidak ada / rusak: pakai gambar kosong agar app tetap jalan.
                self.icons[name] = tk.PhotoImage(master=self.root, width=24, height=24)

    def _configure_window(self) -> None:
        width = self._px(1317)
        height = self._px(867)
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.title("Recipe Keeper")
        self.root.overrideredirect(True)
        self.root.configure(bg=self.WINDOW_BG)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(self._px(760), self._px(520))

    # ----------------------------------------------------------------- layout
    def _build_window(self) -> None:
        self._build_titlebar()

        self.content = tk.Frame(self.root, bg=self.WINDOW_BG)
        self.content.pack(fill="both", expand=True)
        self._show_home_view()

    def _build_titlebar(self) -> None:
        bar = tk.Frame(self.root, bg=self.ACCENT, height=self._px(41))
        bar.pack(fill="x")
        bar.pack_propagate(False)
        bar.bind("<Button-1>", self._start_window_move)
        bar.bind("<B1-Motion>", self._move_window)
        bar.bind("<Double-Button-1>", lambda _e: self._toggle_maximize())

        self.back_button = tk.Canvas(
            bar,
            width=self._px(58),
            height=self._px(41),
            bg=self.ACCENT,
            highlightthickness=0,
            cursor="hand2",
        )
        self._draw_icon(self.back_button, "back", self._px(29), self._px(20), "#FFFFFF")
        self.back_button.bind("<Button-1>", lambda _e: self._navigate_back())
        self.back_button.bind("<Enter>", lambda _e: self.back_button.configure(bg="#C13D00"))
        self.back_button.bind("<Leave>", lambda _e: self.back_button.configure(bg=self.ACCENT))
        self.back_button.pack_forget()

        self.title_label = tk.Label(
            bar,
            text="Recipe Keeper",
            bg=self.ACCENT,
            fg="#FFFFFF",
            font=self._font(15),
            anchor="w",
        )
        self.title_label.pack(side="left", fill="y", padx=self._px(16))
        self.title_label.bind("<Button-1>", self._start_window_move)
        self.title_label.bind("<B1-Motion>", self._move_window)
        self.title_label.bind("<Double-Button-1>", lambda _e: self._toggle_maximize())

        controls = tk.Frame(bar, bg=self.ACCENT)
        controls.pack(side="right", fill="y")
        self._window_control(controls, "minimize", self._minimize)
        self._window_control(controls, "maximize", self._toggle_maximize)
        self._window_control(controls, "close", self.root.destroy)

    def _set_titlebar_back(self, visible: bool) -> None:
        if visible:
            self.back_button.pack(side="left", before=self.title_label)
            self.title_label.pack_configure(padx=0)
        else:
            self.back_button.pack_forget()
            self.title_label.pack_configure(padx=self._px(16))

    def _draw_icon(
        self,
        canvas: tk.Canvas,
        icon: str,
        center_x: int,
        center_y: int,
        color: str,
    ) -> None:
        unit = self._px(1)
        options = {"fill": color, "width": max(1, self._px(2)), "capstyle": tk.ROUND}
        if icon == "back":
            canvas.create_line(
                center_x + self._px(5), center_y,
                center_x - self._px(5), center_y,
                center_x, center_y - self._px(5),
                fill=color, width=max(1, self._px(2)), capstyle=tk.ROUND, joinstyle=tk.ROUND,
            )
            canvas.create_line(
                center_x - self._px(5), center_y,
                center_x, center_y + self._px(5),
                fill=color, width=max(1, self._px(2)), capstyle=tk.ROUND, joinstyle=tk.ROUND,
            )
        elif icon == "cancel":
            canvas.create_line(
                center_x - self._px(5), center_y - self._px(5),
                center_x + self._px(5), center_y + self._px(5),
                **options,
            )
            canvas.create_line(
                center_x + self._px(5), center_y - self._px(5),
                center_x - self._px(5), center_y + self._px(5),
                **options,
            )
        elif icon == "save":
            left, top = center_x - self._px(6), center_y - self._px(7)
            right, bottom = center_x + self._px(6), center_y + self._px(7)
            canvas.create_rectangle(left, top, right, bottom, outline=color, width=unit)
            canvas.create_rectangle(
                center_x - self._px(3), top,
                center_x + self._px(3), center_y - self._px(2),
                outline=color, width=unit,
            )
            canvas.create_rectangle(
                center_x - self._px(4), center_y + self._px(2),
                center_x + self._px(4), bottom,
                outline=color, width=unit,
            )
        elif icon == "edit":
            canvas.create_line(
                center_x - self._px(5), center_y + self._px(5),
                center_x + self._px(4), center_y - self._px(4),
                **options,
            )
            canvas.create_line(
                center_x - self._px(6), center_y + self._px(7),
                center_x - self._px(2), center_y + self._px(6),
                **options,
            )
        elif icon == "trash":
            canvas.create_rectangle(
                center_x - self._px(5), center_y - self._px(4),
                center_x + self._px(5), center_y + self._px(7),
                outline=color, width=unit,
            )
            canvas.create_line(
                center_x - self._px(7), center_y - self._px(6),
                center_x + self._px(7), center_y - self._px(6),
                **options,
            )
            canvas.create_line(
                center_x - self._px(2), center_y - self._px(8),
                center_x + self._px(2), center_y - self._px(8),
                **options,
            )
        elif icon == "star":
            points: list[int] = []
            for index in range(10):
                angle = -90 + index * 36
                radius = self._px(8 if index % 2 == 0 else 3.5)
                points.extend(
                    (
                        round(center_x + radius * math.cos(math.radians(angle))),
                        round(center_y + radius * math.sin(math.radians(angle))),
                    )
                )
            canvas.create_polygon(points, fill="", outline=color, width=unit)

    def _header_action(
        self,
        parent: tk.Frame,
        text: str,
        icon: str,
        width: int,
        primary: bool,
        command: Callable[[], None],
        foreground: str | None = None,
    ) -> tk.Canvas:
        background = self.ACCENT if primary else "#FFFFFF"
        foreground = foreground or ("#FFFFFF" if primary else self.TEXT)
        canvas = tk.Canvas(
            parent,
            width=self._px(width),
            height=self._px(40),
            bg=background,
            highlightthickness=0,
            cursor="hand2",
        )
        if not primary:
            canvas.create_rectangle(
                0, 0, self._px(width) - 1, self._px(40) - 1,
                outline="#D0D0D0", width=self._px(1),
            )
        self._draw_icon(canvas, icon, self._px(26 if primary else 21), self._px(20), foreground)
        canvas.create_text(
            self._px(48 if primary else 41),
            self._px(20),
            text=text,
            anchor="w",
            fill=foreground,
            font=self._font(17),
            tags=("action_label",),
        )
        hover = "#B93600" if primary else "#F5F5F5"
        canvas.bind("<Button-1>", lambda _event: command())
        canvas.bind("<Enter>", lambda _event: canvas.configure(bg=hover))
        canvas.bind("<Leave>", lambda _event: canvas.configure(bg=background))
        return canvas

    def _step_heading(self, parent: tk.Frame, number: int, title: str) -> tk.Frame:
        heading = tk.Frame(parent, bg="#FFFFFF", height=self._px(51))
        heading.grid(row=0, column=0, sticky="ew")
        heading.grid_propagate(False)
        badge = tk.Canvas(
            heading,
            width=self._px(28),
            height=self._px(28),
            bg="#FFFFFF",
            highlightthickness=0,
        )
        badge.create_oval(
            0, 0, self._px(28), self._px(28),
            fill=self.ACCENT, outline=self.ACCENT,
        )
        badge.create_text(
            self._px(14), self._px(14), text=str(number),
            fill="#FFFFFF", font=(self.FONT, -self._px(15), "bold"),
        )
        badge.place(x=self._px(19), y=self._px(15))
        tk.Label(
            heading,
            text=title,
            bg="#FFFFFF",
            fg=self.TEXT,
            font=self._font(19),
            anchor="w",
        ).place(x=self._px(59), y=self._px(12), height=self._px(32))
        return heading

    def _bordered_panel(
        self,
        parent: tk.Frame,
        row: int,
        column: int,
        columnspan: int = 1,
        rowspan: int = 1,
        padx: tuple[int, int] = (0, 0),
        height: int | None = None,
    ) -> tk.Frame:
        panel = tk.Frame(parent, bg="#D0D0D0", highlightthickness=0)
        panel.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            rowspan=rowspan,
            sticky="nsew",
            padx=padx,
        )
        panel.grid_propagate(False)
        if height is not None:
            panel.configure(height=self._px(height))
        surface = tk.Frame(panel, bg="#FFFFFF")
        surface.place(
            x=self._px(1),
            y=self._px(1),
            relwidth=1,
            width=-self._px(2),
            relheight=1,
            height=-self._px(2),
        )
        return surface

    def _window_control(
        self,
        parent: tk.Frame,
        icon_name: str,
        command: Callable[[], None],
    ) -> None:
        control = tk.Frame(
            parent,
            bg=self.ACCENT,
            width=self._px(58),
            height=self._px(41),
            cursor="hand2",
        )
        control.pack(side="left")
        control.pack_propagate(False)
        icon = tk.Label(control, image=self.icons[icon_name], bg=self.ACCENT)
        icon.place(relx=0.5, rely=0.5, anchor="center")

        hover = "#B93600" if icon_name == "close" else "#C13D00"

        def set_bg(color: str) -> None:
            # Ubah frame DAN ikon bersama-sama supaya tidak berkedip saat kursor
            # pindah dari frame ke label di dalamnya.
            control.configure(bg=color)
            icon.configure(bg=color)

        for widget in (control, icon):
            widget.bind("<Button-1>", lambda _event: command())
            widget.bind("<Enter>", lambda _event: set_bg(hover))
            widget.bind("<Leave>", lambda _event: set_bg(self.ACCENT))

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(parent, bg=self.SIDEBAR, width=self._px(321))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)

        menu_row = tk.Frame(sidebar, bg=self.SIDEBAR, height=self._px(58))
        menu_row.grid(row=0, column=0, sticky="ew")
        menu_row.grid_propagate(False)
        menu_button = tk.Label(
            menu_row,
            image=self.icons["menu"],
            bg=self.SIDEBAR,
            cursor="hand2",
        )
        menu_button.place(
            x=self._px(18),
            y=self._px(16),
            width=self._px(28),
            height=self._px(28),
        )

        search_wrap = tk.Frame(
            sidebar,
            bg="#8A8A8A",
            width=self._px(289),
            height=self._px(40),
        )
        search_wrap.grid(
            row=1,
            column=0,
            sticky="w",
            padx=(self._px(17), self._px(15)),
            pady=(self._px(12), self._px(18)),
        )
        search_wrap.grid_propagate(False)
        search_inner = tk.Frame(search_wrap, bg=self.SEARCH_BG)
        search_inner.place(
            x=1,
            y=1,
            width=max(1, self._px(289) - 2),
            height=max(1, self._px(40) - 2),
        )
        search_inner.grid_rowconfigure(0, weight=1)
        search_inner.grid_columnconfigure(0, weight=1)

        self.search_var = tk.StringVar(value=self.PLACEHOLDER_TEXT)
        self.search_entry = tk.Entry(
            search_inner,
            textvariable=self.search_var,
            bg=self.SEARCH_BG,
            fg=self.PLACEHOLDER_FG,
            insertbackground=self.TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=self._font(17),
        )
        self.search_entry.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(self._px(11), self._px(4)),
        )
        search_icon = tk.Label(
            search_inner,
            image=self.icons["search"],
            bg=self.SEARCH_BG,
        )
        search_icon.grid(row=0, column=1, padx=(0, self._px(10)))
        self.search_entry.bind("<FocusIn>", self._clear_search_placeholder)
        self.search_entry.bind("<FocusOut>", self._restore_search_placeholder)
        self.search_entry.bind("<KeyRelease>", self._filter_cards)

        new_recipe = self._nav_row(
            sidebar,
            row=2,
            icon="plus",
            text="New recipe",
            active=False,
            command=self._open_new_recipe,
        )
        home = self._nav_row(
            sidebar,
            row=3,
            icon="home",
            text="Home",
            active=True,
            command=lambda: self._select_tab("Resep"),
        )
        self.nav_rows = {"new": new_recipe, "home": home}

    def _nav_row(
        self,
        parent: tk.Frame,
        row: int,
        icon: str,
        text: str,
        active: bool,
        command: Callable[[], None],
    ) -> tk.Frame:
        color = self.ACCENT if active else self.TEXT
        row_frame = tk.Frame(parent, bg=self.SIDEBAR, height=self._px(60), cursor="hand2")
        row_frame.grid(row=row, column=0, sticky="ew")
        row_frame.grid_propagate(False)

        if active:
            tk.Frame(row_frame, bg=self.ACCENT, width=self._px(5)).place(
                x=0,
                y=self._px(4),
                height=self._px(52),
            )
        icon_label = tk.Label(row_frame, image=self.icons[icon], bg=self.SIDEBAR)
        icon_label.place(
            x=self._px(20),
            y=self._px(18),
            width=self._px(24),
            height=self._px(24),
        )
        text_label = tk.Label(
            row_frame,
            text=text,
            bg=self.SIDEBAR,
            fg=color,
            font=self._font(18),
            anchor="w",
        )
        text_label.place(
            x=self._px(61),
            y=0,
            relheight=1,
            width=self._px(240),
        )
        for widget in (row_frame, icon_label, text_label):
            widget.bind("<Button-1>", lambda _event: command())
        return row_frame

    def _build_main(self, parent: tk.Frame) -> None:
        main = tk.Frame(parent, bg=self.WINDOW_BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)

        header = tk.Frame(main, bg=self.WINDOW_BG, height=self._px(70))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        self.heading = tk.Label(
            header,
            text=f"Semua Resep ({self._total_recipes()})",
            bg=self.WINDOW_BG,
            fg=self.TEXT,
            font=self._font(26),
            anchor="w",
        )
        self.heading.pack(side="left", fill="y", padx=self._px(30))

        tabs = tk.Frame(main, bg=self.WINDOW_BG, height=self._px(50))
        tabs.grid(row=1, column=0, sticky="ew")
        tabs.grid_propagate(False)
        tab_row = tk.Frame(tabs, bg=self.WINDOW_BG)
        tab_row.pack(side="left", fill="y", padx=self._px(30))

        self.tab_labels: dict[str, tk.Label] = {}
        for column, name, width in ((0, "Resep", 120), (2, "Favorit", 130)):
            tab = tk.Label(
                tab_row,
                text=name,
                bg=self.WINDOW_BG,
                fg=self.TEXT if name == self.active_tab else self.MUTED,
                font=self._font(24),
                anchor="w",
                cursor="hand2",
            )
            tab.grid(row=0, column=column, sticky="nsew")
            tab_row.grid_columnconfigure(column, minsize=self._px(width))
            tab.bind("<Button-1>", lambda _event, value=name: self._select_tab(value))
            self.tab_labels[name] = tab
        tab_row.grid_columnconfigure(1, minsize=self._px(28))

        # Area kartu: canvas yang bisa di-scroll hanya ketika isi melebihi tinggi area.
        main.grid_rowconfigure(2, weight=1)
        self.card_scrollbar = ttk.Scrollbar(main, orient="vertical")
        self.card_canvas = tk.Canvas(
            main,
            bg=self.WINDOW_BG,
            highlightthickness=0,
            yscrollincrement=self._px(30),
            yscrollcommand=self._on_cards_scroll,
        )
        self.card_canvas.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=(self._px(30), self._px(10)),
            pady=(0, self._px(20)),
        )
        self.card_scrollbar.configure(command=self.card_canvas.yview)

        self.card_area = tk.Frame(self.card_canvas, bg=self.WINDOW_BG)
        self._cards_window = self.card_canvas.create_window(
            (0, 0), window=self.card_area, anchor="nw"
        )
        self.card_canvas.bind("<Configure>", self._on_cards_canvas_configure)
        self.card_area.bind("<Configure>", lambda _e: self._sync_cards_scroll())
        self.root.bind_all("<MouseWheel>", self._on_home_wheel)

        # Perkiraan jumlah kolom awal; dihitung ulang saat ukuran canvas diketahui.
        self._cards_cols = self._calc_columns(
            self._px(1317) - self._px(321) - self._px(30) - self._px(20)
        )
        self._render_cards()

    def _show_home_view(self) -> None:
        self.current_view = "home"
        self.current_recipe = None
        self.editing_recipe = None
        self._set_titlebar_back(False)
        for child in self.content.winfo_children():
            child.destroy()

        body = tk.Frame(self.content, bg=self.WINDOW_BG)
        body.pack(fill="both", expand=True)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, minsize=self._px(321))
        body.grid_columnconfigure(1, weight=1)
        self._build_sidebar(body)
        self._build_main(body)
        body.bind("<Button-1>", lambda _event: self.root.focus_set())

    def _show_recipe_form(self, recipe_to_edit: dict[str, object] | None = None) -> None:
        self.current_view = "form"
        self.editing_recipe = recipe_to_edit
        self._set_titlebar_back(True)
        for child in self.content.winfo_children():
            child.destroy()

        header = tk.Frame(self.content, bg=self.SIDEBAR, height=self._px(70))
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="Edit Resep" if recipe_to_edit else "Resep Baru",
            bg=self.SIDEBAR,
            fg=self.TEXT,
            font=self._font(30),
            anchor="w",
        ).pack(side="left", fill="y", padx=self._px(30))

        self._header_action(
            header, "Batal", "cancel", 103, False, self._cancel_recipe_form
        ).pack(side="right", padx=(0, self._px(30)), pady=self._px(15))
        self._header_action(
            header, "Simpan", "save", 120, True, self._save_recipe
        ).pack(side="right", padx=(0, self._px(12)), pady=self._px(15))

        form_body = tk.Frame(self.content, bg=self.SIDEBAR)
        form_body.pack(fill="both", expand=True)
        form_body.grid_columnconfigure(0, weight=1)
        form_body.grid_rowconfigure(0, minsize=self._px(110))
        form_body.grid_rowconfigure(1, minsize=self._px(20))
        form_body.grid_rowconfigure(2, weight=1)
        form_body.grid_rowconfigure(3, minsize=self._px(30))

        layout = tk.Frame(form_body, bg=self.SIDEBAR)
        layout.grid(row=0, column=0, rowspan=4, sticky="nsew")
        layout.grid_columnconfigure(0, weight=1)
        layout.grid_rowconfigure(0, minsize=self._px(110))
        layout.grid_rowconfigure(1, minsize=self._px(20))
        layout.grid_rowconfigure(2, weight=1)
        layout.grid_rowconfigure(3, minsize=self._px(30))

        top_card = self._bordered_panel(
            layout,
            row=0,
            column=0,
            columnspan=3,
            padx=(self._px(30), self._px(30)),
            height=110,
        )
        top_card.grid_columnconfigure(0, weight=1)
        top_card.grid_rowconfigure(0, minsize=self._px(51))
        top_card.grid_rowconfigure(1, weight=1)
        self._step_heading(top_card, 1, "Nama Makanan")

        self.recipe_title_var = tk.StringVar()
        self.form_title_entry = tk.Entry(
            top_card,
            textvariable=self.recipe_title_var,
            bg=self.WINDOW_BG,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=self._px(1),
            highlightbackground="#D0D0D0",
            highlightcolor="#1A6FD0",
            font=self._font(17),
        )
        self.form_title_entry.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=self._px(19),
            pady=(0, self._px(15)),
            ipady=self._px(5),
        )
        self.form_title_entry.bind("<Return>", lambda _event: self.ingredients_text.focus_set())

        layout.grid_columnconfigure(0, weight=459, minsize=self._px(1))
        layout.grid_columnconfigure(1, minsize=self._px(20))
        layout.grid_columnconfigure(2, weight=776, minsize=self._px(1))
        ingredients_card = self._bordered_panel(
            layout,
            row=2,
            column=0,
            padx=(self._px(30), 0),
        )
        directions_card = self._bordered_panel(
            layout,
            row=2,
            column=2,
            padx=(0, self._px(30)),
        )

        for surface in (ingredients_card, directions_card):
            surface.grid_columnconfigure(0, weight=1)
            surface.grid_rowconfigure(0, minsize=self._px(51))
            surface.grid_rowconfigure(1, weight=1)

        self._step_heading(ingredients_card, 2, "Bahan")
        self._step_heading(directions_card, 3, "Langkah")
        self.ingredients_text = tk.Text(
            ingredients_card,
            bg=self.WINDOW_BG,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            font=self._font(16),
            wrap="word",
            undo=True,
            relief="flat",
            borderwidth=0,
            highlightthickness=self._px(1),
            highlightbackground="#D0D0D0",
            highlightcolor="#1A6FD0",
            padx=self._px(9),
            pady=self._px(8),
        )
        self.ingredients_text.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=self._px(19),
            pady=(0, self._px(19)),
        )
        self.directions_text = tk.Text(
            directions_card,
            bg=self.WINDOW_BG,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            font=self._font(16),
            wrap="word",
            undo=True,
            relief="flat",
            borderwidth=0,
            highlightthickness=self._px(1),
            highlightbackground="#D0D0D0",
            highlightcolor="#1A6FD0",
            padx=self._px(9),
            pady=self._px(8),
        )
        self.directions_text.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=self._px(19),
            pady=(0, self._px(19)),
        )
        if recipe_to_edit:
            self.recipe_title_var.set(str(recipe_to_edit.get("name", "")))
            self.ingredients_text.insert(
                "1.0", self._format_ingredients(recipe_to_edit.get("ingredients", []))
            )
            self.directions_text.insert(
                "1.0", self._format_directions(recipe_to_edit.get("directions", []))
            )
        self.form_title_entry.focus_set()
        self.content.bind("<Escape>", lambda _event: self._cancel_recipe_form())

    def _format_ingredients(self, ingredients: object) -> str:
        if isinstance(ingredients, str):
            return ingredients
        if not isinstance(ingredients, (list, tuple)):
            return ""
        lines: list[str] = []
        for ingredient in ingredients:
            if isinstance(ingredient, (list, tuple)) and len(ingredient) >= 2:
                lines.append(f"{ingredient[0]} | {ingredient[1]}")
            elif isinstance(ingredient, dict):
                lines.append(
                    f"{ingredient.get('quantity', '')} | {ingredient.get('name', '')}"
                )
            else:
                lines.append(str(ingredient))
        return "\n".join(lines)

    def _format_directions(self, directions: object) -> str:
        if isinstance(directions, str):
            return directions
        if isinstance(directions, (list, tuple)):
            return "\n".join(str(step) for step in directions)
        return ""

    def _cancel_recipe_form(self) -> None:
        if self.editing_recipe is not None:
            self._show_recipe_detail(self.editing_recipe)
        else:
            self._show_home_view()

    def _navigate_back(self) -> None:
        if self.current_view == "form":
            self._cancel_recipe_form()
        elif self.current_view == "detail":
            self._show_home_view()
        else:
            self._show_home_view()

    def _save_recipe(self) -> None:
        name = self.recipe_title_var.get().strip()
        if not name:
            self.form_title_entry.configure(highlightbackground=self.ACCENT)
            self.form_title_entry.focus_set()
            return

        values = {
            "name": name,
            "ingredients": self.ingredients_text.get("1.0", "end-1c").strip(),
            "directions": self.directions_text.get("1.0", "end-1c").strip(),
        }
        if self.editing_recipe is not None:
            self.editing_recipe.update(values)
            self._show_recipe_detail(self.editing_recipe)
            return

        color = self.recipe_colors[len(self.recipes) % len(self.recipe_colors)]
        self.recipes.append({**values, "color": color, "favorite": False})
        self.recipe_count += 1
        self.active_tab = "Resep"
        self._show_home_view()

    def _show_recipe_detail(self, recipe: dict[str, object]) -> None:
        self.current_view = "detail"
        self.current_recipe = recipe
        self.editing_recipe = None
        self._set_titlebar_back(True)
        for child in self.content.winfo_children():
            child.destroy()

        header = tk.Frame(self.content, bg=self.SIDEBAR, height=self._px(70))
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="Recipe",
            bg=self.SIDEBAR,
            fg=self.TEXT,
            font=self._font(30),
            anchor="w",
        ).pack(side="left", fill="y", padx=self._px(30))

        self.favorite_button = self._header_action(
            header,
            "Hapus Favorit" if recipe.get("favorite", False) else "Tambah Favorit",
            "star",
            187,
            False,
            self._toggle_favorite,
        )
        self.favorite_button.pack(side="right", padx=(0, self._px(31)), pady=self._px(15))
        self._header_action(
            header,
            "Hapus",
            "trash",
            112,
            False,
            self._delete_recipe,
            foreground="#C42B1C",
        ).pack(side="right", padx=(0, self._px(13)), pady=self._px(15))
        self._header_action(
            header,
            "Edit",
            "edit",
            100,
            False,
            lambda: self._show_recipe_form(recipe),
        ).pack(side="right", padx=(0, self._px(13)), pady=self._px(15))

        body = tk.Frame(self.content, bg=self.SIDEBAR)
        body.pack(fill="both", expand=True)
        layout = tk.Frame(body, bg=self.SIDEBAR)
        layout.pack(fill="both", expand=True)
        layout.grid_columnconfigure(0, weight=420)
        layout.grid_columnconfigure(1, minsize=self._px(20))
        layout.grid_columnconfigure(2, weight=817)
        layout.grid_rowconfigure(0, minsize=self._px(300))
        layout.grid_rowconfigure(1, minsize=self._px(20))
        layout.grid_rowconfigure(2, weight=1)
        layout.grid_rowconfigure(3, minsize=self._px(30))

        photo = self._bordered_panel(
            layout,
            row=0,
            column=0,
            padx=(self._px(30), 0),
            height=300,
        )
        photo.grid_rowconfigure(0, weight=1)
        photo.grid_rowconfigure(1, minsize=self._px(56))
        photo.grid_columnconfigure(0, weight=1)
        tk.Frame(photo, bg=str(recipe.get("color", "#E2AE58"))).grid(
            row=0, column=0, sticky="nsew"
        )
        name_bar = tk.Frame(photo, bg=self.ACCENT)
        name_bar.grid(row=1, column=0, sticky="nsew")
        tk.Label(
            name_bar,
            text=str(recipe.get("name", "Recipe")),
            bg=self.ACCENT,
            fg="#FFFFFF",
            font=self._font(26),
            anchor="w",
        ).pack(fill="both", expand=True, padx=self._px(14))

        ingredients_panel = self._bordered_panel(
            layout,
            row=2,
            column=0,
            padx=(self._px(30), 0),
            height=406,
        )
        directions_panel = self._bordered_panel(
            layout,
            row=0,
            column=2,
            rowspan=3,
            padx=(0, self._px(30)),
            height=726,
        )
        self._detail_section_heading(ingredients_panel, "Ingredients")
        self._detail_section_heading(directions_panel, "Directions")

        ingredient_canvas, ingredient_rows = self._detail_scroll_area(
            ingredients_panel, height=336
        )
        ingredient_list = self._ingredient_rows(recipe.get("ingredients", []))
        if not ingredient_list:
            ingredient_list = [("", "No ingredients added")]
        for index, (quantity, item_name) in enumerate(ingredient_list):
            row = tk.Frame(ingredient_rows, bg="#FFFFFF", height=self._px(56))
            row.grid(row=index, column=0, sticky="ew")
            row.grid_propagate(False)
            row.grid_columnconfigure(0, minsize=self._px(170))
            row.grid_columnconfigure(1, minsize=self._px(2))
            row.grid_columnconfigure(2, weight=1)
            tk.Label(
                row,
                text=quantity,
                bg="#FFFFFF",
                fg=self.TEXT,
                font=(self.FONT, -self._px(17), "bold"),
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            tk.Label(
                row,
                text=item_name,
                bg="#FFFFFF",
                fg=self.TEXT,
                font=self._font(17),
                anchor="w",
            ).grid(row=0, column=2, sticky="w")
            if index < len(ingredient_list) - 1:
                tk.Frame(row, bg="#E6E6E6", height=self._px(1)).place(
                    x=0, rely=1, relwidth=1, anchor="sw"
                )
        self._bind_list_wheel(ingredient_canvas, ingredient_rows)

        direction_canvas, direction_rows = self._detail_scroll_area(
            directions_panel, height=654
        )
        directions = self._direction_steps(recipe.get("directions", []))
        if not directions:
            directions = ["No directions added"]
        for index, direction in enumerate(directions):
            row_height = 120 if len(direction) > 120 else 96
            row = tk.Frame(direction_rows, bg="#FFFFFF")
            row.grid(row=index, column=0, sticky="ew")
            row.grid_columnconfigure(1, weight=1)
            direction_rows.grid_rowconfigure(index, minsize=self._px(row_height))

            badge = tk.Canvas(
                row,
                width=self._px(32),
                height=self._px(32),
                bg="#FFFFFF",
                highlightthickness=0,
            )
            badge.create_oval(
                0, 0, self._px(32), self._px(32),
                fill=self.ACCENT, outline=self.ACCENT,
            )
            badge.create_text(
                self._px(16), self._px(16), text=str(index + 1),
                fill="#FFFFFF", font=(self.FONT, -self._px(16), "bold"),
            )
            badge.grid(
                row=0,
                column=0,
                sticky="n",
                padx=(0, self._px(18)),
                pady=self._px(18),
            )
            tk.Label(
                row,
                text=direction,
                bg="#FFFFFF",
                fg=self.TEXT,
                font=self._font(18),
                justify="left",
                anchor="nw",
                wraplength=self._px(700),
            ).grid(row=0, column=1, sticky="ew", pady=(self._px(12), self._px(12)))
            if index < len(directions) - 1:
                tk.Frame(row, bg="#E6E6E6", height=self._px(1)).place(
                    x=0, rely=1, relwidth=1, anchor="sw"
                )
        self._bind_list_wheel(direction_canvas, direction_rows)

    def _detail_section_heading(self, parent: tk.Frame, title: str) -> None:
        tk.Frame(parent, bg=self.ACCENT, width=self._px(4), height=self._px(22)).place(
            x=self._px(19), y=self._px(17)
        )
        tk.Label(
            parent,
            text=title,
            bg="#FFFFFF",
            fg=self.TEXT,
            font=(self.FONT, -self._px(20), "bold"),
            anchor="w",
        ).place(x=self._px(33), y=self._px(12), height=self._px(32))

    def _detail_scroll_area(
        self,
        parent: tk.Frame,
        height: int,
    ) -> tuple[tk.Canvas, tk.Frame]:
        canvas = tk.Canvas(
            parent,
            bg="#FFFFFF",
            highlightthickness=0,
            yscrollincrement=self._px(28),
        )
        canvas.place(
            x=self._px(19),
            y=self._px(55),
            relwidth=1,
            width=-self._px(38),
            height=self._px(height),
        )
        rows = tk.Frame(canvas, bg="#FFFFFF")
        rows.grid_columnconfigure(0, weight=1)
        window_id = canvas.create_window((0, 0), window=rows, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window_id, width=event.width),
        )
        rows.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        return canvas, rows

    def _bind_list_wheel(self, canvas: tk.Canvas, rows: tk.Frame) -> None:
        def scroll(event: tk.Event) -> str:
            amount = -1 if event.delta > 0 else 1
            canvas.yview_scroll(amount, "units")
            return "break"

        canvas.bind("<MouseWheel>", scroll)
        rows.bind("<MouseWheel>", scroll)
        for row in rows.winfo_children():
            row.bind("<MouseWheel>", scroll)
            for child in row.winfo_children():
                child.bind("<MouseWheel>", scroll)

    def _ingredient_rows(self, value: object) -> list[tuple[str, str]]:
        if isinstance(value, (list, tuple)):
            rows: list[tuple[str, str]] = []
            for ingredient in value:
                if isinstance(ingredient, (list, tuple)) and len(ingredient) >= 2:
                    rows.append((str(ingredient[0]), str(ingredient[1])))
                elif isinstance(ingredient, dict):
                    rows.append(
                        (
                            str(ingredient.get("quantity", "")),
                            str(ingredient.get("name", "")),
                        )
                    )
                else:
                    rows.append(("", str(ingredient)))
            return rows
        if isinstance(value, str):
            rows = []
            for line in value.splitlines():
                line = line.strip()
                if not line:
                    continue
                separator = " | " if " | " in line else " - "
                if separator in line:
                    quantity, item_name = line.split(separator, 1)
                    rows.append((quantity.strip(), item_name.strip()))
                else:
                    rows.append(("", line))
            return rows
        return []

    def _direction_steps(self, value: object) -> list[str]:
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        if isinstance(value, (list, tuple)):
            return [str(step).strip() for step in value if str(step).strip()]
        return []

    def _toggle_favorite(self) -> None:
        if self.current_recipe is None:
            return
        self.current_recipe["favorite"] = not bool(
            self.current_recipe.get("favorite", False)
        )
        self._show_recipe_detail(self.current_recipe)

    def _delete_recipe(self) -> None:
        recipe = self.current_recipe
        if recipe is None:
            return
        if not messagebox.askyesno(
            "Hapus resep",
            f"Hapus resep “{recipe.get('name', 'Recipe')}”?",
            parent=self.root,
        ):
            return
        if recipe in self.recipes:
            self.recipes.remove(recipe)
            self.recipe_count = max(len(self.recipes), self.recipe_count - 1)
        self._show_home_view()

    # ------------------------------------------------------------------ cards
    def _total_recipes(self) -> int:
        return self.recipe_count

    def _calc_columns(self, width: int) -> int:
        card = self._px(177)
        gap = self._px(10)
        return max(1, (width + gap) // (card + gap))

    def _cards_can_scroll(self) -> bool:
        canvas = getattr(self, "card_canvas", None)
        if canvas is None or not canvas.winfo_exists():
            return False
        bbox = canvas.bbox("all")
        if not bbox:
            return False
        content_height = bbox[3] - bbox[1]
        viewport_height = canvas.winfo_height()
        return content_height > viewport_height > 1

    def _sync_cards_scroll(self) -> None:
        canvas = getattr(self, "card_canvas", None)
        if canvas is None or not canvas.winfo_exists():
            return
        bbox = canvas.bbox("all")
        if not bbox:
            canvas.configure(scrollregion=(0, 0, 0, 0))
            self.card_scrollbar.grid_remove()
            return

        viewport_w = canvas.winfo_width()
        viewport_h = canvas.winfo_height()
        content_h = bbox[3] - bbox[1]

        if content_h > viewport_h > 1:
            canvas.configure(scrollregion=(0, 0, viewport_w, content_h))
            self.card_scrollbar.grid(row=2, column=1, sticky="ns", pady=(0, self._px(20)))
        else:
            canvas.configure(scrollregion=(0, 0, viewport_w, max(1, viewport_h)))
            canvas.yview_moveto(0.0)
            self.card_scrollbar.grid_remove()

    def _on_cards_scroll(self, first: str, last: str) -> None:
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.card_scrollbar.grid_remove()
        else:
            self.card_scrollbar.set(first, last)

    def _on_cards_canvas_configure(self, event: tk.Event) -> None:
        self.card_canvas.itemconfigure(self._cards_window, width=event.width)
        cols = self._calc_columns(event.width)
        if cols != self._cards_cols:
            self._cards_cols = cols
            self._filter_cards()
        else:
            self._sync_cards_scroll()

    def _on_home_wheel(self, event: tk.Event) -> None:
        if self.current_view != "home" or not self._cards_can_scroll():
            return
        canvas = getattr(self, "card_canvas", None)
        if canvas is None or not canvas.winfo_exists():
            return
        canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _render_cards(self, query: str = "") -> None:
        for child in self.card_area.winfo_children():
            child.destroy()

        needle = query.casefold()
        visible = [
            recipe
            for recipe in self.recipes
            if needle in str(recipe["name"]).casefold()
            and (self.active_tab != "Favorit" or bool(recipe.get("favorite", False)))
        ]

        cols = max(1, self._cards_cols)
        for index, recipe in enumerate(visible):
            row, column = divmod(index, cols)
            self._create_recipe_card(recipe, row=row, column=column)

        if not visible:
            tk.Label(
                self.card_area,
                text=(
                    "Belum ada resep favorit"
                    if self.active_tab == "Favorit"
                    else "No recipes found"
                ),
                bg=self.WINDOW_BG,
                fg=self.MUTED,
                font=self._font(16),
            ).grid(row=0, column=0, sticky="w")

        self.card_canvas.yview_moveto(0.0)
        self.root.after_idle(self._sync_cards_scroll)

    def _create_recipe_card(
        self,
        recipe: dict[str, object],
        row: int,
        column: int,
    ) -> None:
        color = str(recipe["color"])
        card = tk.Frame(
            self.card_area,
            bg=color,
            width=self._px(177),
            height=self._px(177),
            highlightthickness=0,
        )
        card.grid(
            row=row,
            column=column,
            sticky="nw",
            padx=(0, self._px(10)),
            pady=(0, self._px(10)),
        )
        card.pack_propagate(False)

        image_area = tk.Frame(card, bg=color, height=self._px(139))
        image_area.pack(fill="x", side="top")
        image_area.pack_propagate(False)

        label_bar = tk.Frame(card, bg=self.ACCENT, height=self._px(38))
        label_bar.pack(fill="x", side="bottom")
        label_bar.pack_propagate(False)
        tk.Label(
            label_bar,
            text=str(recipe["name"]),
            bg=self.ACCENT,
            fg="#FFFFFF",
            font=self._font(24),
            anchor="w",
        ).pack(side="left", padx=(self._px(8), 0))
        for widget in (card, image_area, label_bar, *label_bar.winfo_children()):
            widget.configure(cursor="hand2")
            widget.bind(
                "<Button-1>",
                lambda _event, selected=recipe: self._show_recipe_detail(selected),
            )

    # ----------------------------------------------------------------- search
    def _clear_search_placeholder(self, _event: tk.Event) -> None:
        if self.search_placeholder:
            self.search_var.set("")
            self.search_entry.configure(fg=self.TEXT)
            self.search_placeholder = False

    def _restore_search_placeholder(self, _event: tk.Event) -> None:
        if not self.search_var.get().strip():
            self.search_var.set(self.PLACEHOLDER_TEXT)
            self.search_entry.configure(fg=self.PLACEHOLDER_FG)
            self.search_placeholder = True
            self._filter_cards()

    def _filter_cards(self, _event: tk.Event | None = None) -> None:
        query = "" if self.search_placeholder else self.search_var.get().strip()
        self._render_cards(query)

    # ------------------------------------------------------------------- tabs
    def _select_tab(self, tab_name: str) -> None:
        self.active_tab = tab_name
        for name, label in self.tab_labels.items():
            label.configure(fg=self.TEXT if name == tab_name else self.MUTED)
        if tab_name == "Favorit":
            favorite_count = sum(
                bool(recipe.get("favorite", False)) for recipe in self.recipes
            )
            self.heading.configure(text=f"Favorit ({favorite_count})")
        else:
            self.heading.configure(text=f"Semua Resep ({self._total_recipes()})")
        self._filter_cards()

    # --------------------------------------------------------------- new recipe
    def _open_new_recipe(self) -> None:
        self._show_recipe_form()

    # ---------------------------------------------------------- window control
    def _minimize(self) -> None:
        # Jendela dengan overrideredirect(True) tidak bisa di-iconify di banyak
        # platform; matikan sementara lalu aktifkan lagi saat jendela dipulihkan.
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.bind("", self._restore_frameless)

    def _restore_frameless(self, event: tk.Event) -> None:
        if event.widget is self.root:
            self.root.unbind("")
            self.root.after(10, self._reapply_frameless)

    def _reapply_frameless(self) -> None:
        self.root.overrideredirect(True)
        self._enable_taskbar_icon()

    def _toggle_maximize(self) -> None:
        if self.is_maximized:
            self.root.geometry(self.previous_geometry)
            self.is_maximized = False
            return

        self.previous_geometry = self.root.geometry()
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        self.root.geometry(f"{width}x{height}+0+0")
        self.is_maximized = True

    def _start_window_move(self, event: tk.Event) -> None:
        if self.is_maximized:
            self._drag_offset_x = None
            return
        self._drag_offset_x = event.x_root - self.root.winfo_x()
        self._drag_offset_y = event.y_root - self.root.winfo_y()

    def _move_window(self, event: tk.Event) -> None:
        if self._drag_offset_x is None or self._drag_offset_y is None:
            return
        x = event.x_root - self._drag_offset_x
        y = event.y_root - self._drag_offset_y
        self.root.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    root = tk.Tk()
    app = RecipeKeeperApp(root)
    root.mainloop()