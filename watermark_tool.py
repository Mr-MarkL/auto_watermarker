"""
Watermark Tool Pro — современная версия
Минималистичный интерфейс 2026, выбор глубины обхода, предпросмотр, справка.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import configparser

# ===================== НАСТРОЙКИ =====================
DEFAULT_SCALE = 0.16
DEFAULT_MARGIN = 30
DEFAULT_MIRROR = True
DEFAULT_CORNER = 3
DEFAULT_RECURSIVE = True
CONFIG_FILE = "watermark_config.ini"

def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding='utf-8')
        if 'settings' in config:
            return {
                'scale': config.getfloat('settings', 'scale', fallback=DEFAULT_SCALE),
                'margin': config.getint('settings', 'margin', fallback=DEFAULT_MARGIN),
                'mirror': config.getboolean('settings', 'mirror', fallback=DEFAULT_MIRROR),
                'corner': config.getint('settings', 'corner', fallback=DEFAULT_CORNER),
                'recursive': config.getboolean('settings', 'recursive', fallback=DEFAULT_RECURSIVE),
                'watermark_path': config.get('settings', 'watermark_path', fallback=''),
                'folder_path': config.get('settings', 'folder_path', fallback='')
            }
    return {'scale': DEFAULT_SCALE, 'margin': DEFAULT_MARGIN,
            'mirror': DEFAULT_MIRROR, 'corner': DEFAULT_CORNER,
            'recursive': DEFAULT_RECURSIVE,
            'watermark_path': '', 'folder_path': ''}

def save_config(scale, margin, mirror, corner, recursive, watermark_path, folder_path):
    config = configparser.ConfigParser()
    config['settings'] = {
        'scale': str(scale),
        'margin': str(margin),
        'mirror': str(mirror),
        'corner': str(corner),
        'recursive': str(recursive),
        'watermark_path': watermark_path,
        'folder_path': folder_path
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)

# ===================== ОСНОВНАЯ ЛОГИКА =====================
def process_folder(folder_path, watermark, wm_width, wm_height,
                   scale, margin, mirror, corner, progress_callback=None):
    files = [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".jpeg"))]
    if not files:
        return 0

    right_dir = os.path.join(folder_path, "правая")
    os.makedirs(right_dir, exist_ok=True)

    left_dir = None
    if mirror:
        left_dir = os.path.join(folder_path, "левая")
        os.makedirs(left_dir, exist_ok=True)

    processed = 0
    for filename in files:
        image_path = os.path.join(folder_path, filename)
        try:
            with Image.open(image_path) as img:
                # ----- Правая копия -----
                img_rgb = img.convert("RGBA") if img.mode != 'RGBA' else img
                bg_w, bg_h = img_rgb.size

                wm = watermark.copy()
                max_wm_w = int(bg_w * scale)
                if wm_width > max_wm_w:
                    ratio = max_wm_w / wm_width
                    new_size = (max_wm_w, int(wm_height * ratio))
                    wm = wm.resize(new_size, Image.Resampling.LANCZOS)
                wm_w, wm_h = wm.size

                if corner == 0:
                    pos = (margin, margin)
                elif corner == 1:
                    pos = (bg_w - wm_w - margin, margin)
                elif corner == 2:
                    pos = (margin, bg_h - wm_h - margin)
                else:
                    pos = (bg_w - wm_w - margin, bg_h - wm_h - margin)

                combined = img_rgb.copy()
                combined.paste(wm, pos, wm)
                base, ext = os.path.splitext(filename)
                combined.convert("RGB").save(
                    os.path.join(right_dir, f"{base}_wm{ext}"), "JPEG", quality=95
                )

                # ----- Левая (отражённая) -----
                if mirror:
                    mirrored = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                    mirrored_rgba = mirrored.convert("RGBA") if mirrored.mode != 'RGBA' else mirrored
                    bg_w_l, bg_h_l = mirrored_rgba.size
                    wm_left = watermark.copy()
                    max_wm_w_l = int(bg_w_l * scale)
                    if wm_width > max_wm_w_l:
                        ratio_l = max_wm_w_l / wm_width
                        new_size_l = (max_wm_w_l, int(wm_height * ratio_l))
                        wm_left = wm_left.resize(new_size_l, Image.Resampling.LANCZOS)
                    wm_w_l, wm_h_l = wm_left.size

                    if corner == 0:
                        pos_l = (margin, margin)
                    elif corner == 1:
                        pos_l = (bg_w_l - wm_w_l - margin, margin)
                    elif corner == 2:
                        pos_l = (margin, bg_h_l - wm_h_l - margin)
                    else:
                        pos_l = (bg_w_l - wm_w_l - margin, bg_h_l - wm_h_l - margin)

                    combined_left = mirrored_rgba.copy()
                    combined_left.paste(wm_left, pos_l, wm_left)
                    combined_left.convert("RGB").save(
                        os.path.join(left_dir, f"{base}_wm_mirrored{ext}"), "JPEG", quality=95
                    )

                processed += 1
                if progress_callback:
                    progress_callback()

        except Exception as e:
            print(f"Ошибка с {filename}: {e}")

    return processed

def run_processing(root_folder, watermark_path, scale, margin, mirror, corner, recursive,
                   progress_callback, finish_callback):
    if not os.path.exists(watermark_path):
        finish_callback("Ошибка: файл водяного знака не найден.", True)
        return

    try:
        watermark = Image.open(watermark_path).convert("RGBA")
        wm_width, wm_height = watermark.size
    except Exception as e:
        finish_callback(f"Ошибка загрузки водяного знака: {e}", True)
        return

    # Собираем список всех JPEG
    all_files = []
    if recursive:
        for root, dirs, files in os.walk(root_folder):
            dirs[:] = [d for d in dirs if d not in ("правая", "левая")]
            for f in files:
                if f.lower().endswith((".jpg", ".jpeg")):
                    all_files.append(os.path.join(root, f))
    else:
        for f in os.listdir(root_folder):
            if f.lower().endswith((".jpg", ".jpeg")):
                all_files.append(os.path.join(root_folder, f))

    total = len(all_files)
    if total == 0:
        finish_callback("В выбранной папке нет JPEG-изображений.", True)
        return

    processed = 0
    def file_progress():
        nonlocal processed
        processed += 1
        percent = int((processed / total) * 100)
        progress_callback(percent, f"Обработано {processed} из {total}")

    if recursive:
        for root, dirs, files in os.walk(root_folder):
            dirs[:] = [d for d in dirs if d not in ("правая", "левая")]
            process_folder(root, watermark, wm_width, wm_height,
                           scale, margin, mirror, corner,
                           progress_callback=file_progress)
    else:
        process_folder(root_folder, watermark, wm_width, wm_height,
                       scale, margin, mirror, corner,
                       progress_callback=file_progress)

    finish_callback(f"Готово! Обработано {total} файлов.", False)

# ===================== ГЛАВНОЕ ПРИЛОЖЕНИЕ (СОВРЕМЕННЫЙ СТИЛЬ) =====================
class WatermarkApp:
    def __init__(self, master):
        self.master = master
        master.title("Watermark Tool Pro")
        master.geometry("750x800")
        master.resizable(False, False)
        master.configure(bg='#f5f7fa')

        # Загружаем конфиг
        self.config = load_config()
        self.scale = self.config['scale']
        self.margin = self.config['margin']
        self.mirror = self.config['mirror']
        self.corner = self.config['corner']
        self.recursive = self.config['recursive']
        self.watermark_path = self.config['watermark_path']
        self.folder_path = self.config['folder_path']

        # Переменные
        self.folder_var = tk.StringVar(value=self.folder_path)
        self.wm_var = tk.StringVar(value=self.watermark_path)
        self.scale_var = tk.DoubleVar(value=self.scale * 100)
        self.margin_var = tk.IntVar(value=self.margin)
        self.mirror_var = tk.BooleanVar(value=self.mirror)
        self.corner_var = tk.IntVar(value=self.corner)
        self.recursive_var = tk.BooleanVar(value=self.recursive)
        self.progress_var = tk.IntVar(value=0)
        self.status_text = tk.StringVar(value="Готов к работе")

        # Шрифты
        font_label = ('Segoe UI', 10)
        font_button = ('Segoe UI', 10, 'bold')

        # ---------- Верхняя панель: папка и водяной знак ----------
        frame_top = tk.Frame(master, bg='#f5f7fa')
        frame_top.pack(pady=15, padx=30, fill='x')

        # Папка
        tk.Label(frame_top, text="📁 Папка с фото:", bg='#f5f7fa', font=font_label).grid(row=0, column=0, sticky='w', pady=3)
        self.folder_entry = tk.Entry(frame_top, textvariable=self.folder_var, width=50,
                                     font=('Segoe UI', 9), relief='solid', bd=1)
        self.folder_entry.grid(row=0, column=1, padx=8)
        tk.Button(frame_top, text="Выбрать", command=self.select_folder,
                  bg='#e8ecf1', relief='flat', font=font_button,
                  padx=12, pady=4).grid(row=0, column=2)

        # Водяной знак
        tk.Label(frame_top, text="🖼️ Водяной знак:", bg='#f5f7fa', font=font_label).grid(row=1, column=0, sticky='w', pady=3)
        self.wm_entry = tk.Entry(frame_top, textvariable=self.wm_var, width=50,
                                 font=('Segoe UI', 9), relief='solid', bd=1)
        self.wm_entry.grid(row=1, column=1, padx=8)
        tk.Button(frame_top, text="Загрузить", command=self.select_watermark,
                  bg='#e8ecf1', relief='flat', font=font_button,
                  padx=12, pady=4).grid(row=1, column=2)

        # ---------- Предпросмотр ----------
        self.preview_canvas = tk.Canvas(master, width=500, height=350, bg='#ffffff',
                                        relief='solid', bd=1, highlightthickness=0)
        self.preview_canvas.pack(pady=15)
        self.preview_canvas.bind("<Button-1>", self.on_canvas_click)

        # Подпись под предпросмотром
        tk.Label(master, text="Кликните по области предпросмотра, чтобы выбрать угол",
                 bg='#f5f7fa', font=('Segoe UI', 9), fg='#888').pack()

        # ---------- Настройки (горизонтально) ----------
        frame_settings = tk.Frame(master, bg='#f5f7fa')
        frame_settings.pack(pady=15, padx=30, fill='x')

        # Размер
        tk.Label(frame_settings, text="Размер:", bg='#f5f7fa', font=font_label).grid(row=0, column=0, sticky='w')
        scale_slider = tk.Scale(frame_settings, from_=5, to=50, orient='horizontal',
                                variable=self.scale_var, length=180,
                                bg='#f5f7fa', troughcolor='#d0d7e2', highlightthickness=0)
        scale_slider.grid(row=0, column=1, padx=8)
        self.scale_label = tk.Label(frame_settings, text=f"{self.scale_var.get():.0f}%",
                                    bg='#f5f7fa', font=font_label, width=6)
        self.scale_label.grid(row=0, column=2)

        # Отступ
        tk.Label(frame_settings, text="Отступ:", bg='#f5f7fa', font=font_label).grid(row=0, column=3, padx=(20,0), sticky='w')
        margin_slider = tk.Scale(frame_settings, from_=0, to=200, orient='horizontal',
                                 variable=self.margin_var, length=180,
                                 bg='#f5f7fa', troughcolor='#d0d7e2', highlightthickness=0)
        margin_slider.grid(row=0, column=4, padx=8)
        self.margin_label = tk.Label(frame_settings, text=f"{self.margin_var.get()}px",
                                     bg='#f5f7fa', font=font_label, width=6)
        self.margin_label.grid(row=0, column=5)

        # Галочка "Отражение"
        tk.Checkbutton(frame_settings, text="Создавать отражённые копии",
                       variable=self.mirror_var, bg='#f5f7fa', font=font_label).grid(row=1, column=0, columnspan=3, sticky='w', pady=6)

        # Выпадающий список глубины обхода
        tk.Label(frame_settings, text="Обход:", bg='#f5f7fa', font=font_label).grid(row=1, column=3, padx=(20,0), sticky='w')
        self.recursive_combo = ttk.Combobox(frame_settings,
                                            values=["Только текущая папка", "Рекурсивно (все подпапки)"],
                                            state="readonly", width=25, font=('Segoe UI', 9))
        self.recursive_combo.grid(row=1, column=4, columnspan=2, padx=8, sticky='w')
        self.recursive_combo.current(1 if self.recursive else 0)
        self.recursive_combo.bind("<<ComboboxSelected>>", self.on_recursive_change)

        # ---------- Кнопка "Обработать" и "?" ----------
        frame_buttons = tk.Frame(master, bg='#f5f7fa')
        frame_buttons.pack(pady=20)

        self.btn_start = tk.Button(frame_buttons, text="Обработать все папки",
                                   command=self.start_processing,
                                   bg='#4a90d9', fg='white', relief='flat',
                                   font=('Segoe UI', 12, 'bold'), padx=30, pady=10)
        self.btn_start.pack(side='left', padx=10)

        btn_help = tk.Button(frame_buttons, text="?", command=self.show_help,
                             bg='#e8ecf1', relief='flat', font=('Segoe UI', 14, 'bold'),
                             padx=12, pady=6)
        btn_help.pack(side='left', padx=10)

        # ---------- Прогресс ----------
        self.progress = ttk.Progressbar(master, variable=self.progress_var, maximum=100, length=500)
        self.progress.pack(pady=10)

        self.status_label = tk.Label(master, textvariable=self.status_text,
                                     bg='#f5f7fa', font=('Segoe UI', 9))
        self.status_label.pack()

        # Привязки для обновления предпросмотра (используем trace_add)
        self.scale_var.trace_add('write', lambda *args: self.update_preview())
        self.margin_var.trace_add('write', lambda *args: self.update_preview())
        self.corner_var.trace_add('write', lambda *args: self.update_preview())
        self.mirror_var.trace_add('write', lambda *args: self.update_preview())
        self.folder_var.trace_add('write', lambda *args: self.update_preview())
        self.wm_var.trace_add('write', lambda *args: self.update_preview())

        self.update_preview()

    # ---------- Вспомогательные методы ----------
    def select_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с фотографиями")
        if folder:
            self.folder_var.set(folder)

    def select_watermark(self):
        path = filedialog.askopenfilename(title="Выберите файл водяного знака",
                                          filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if path:
            self.wm_var.set(path)

    def on_canvas_click(self, event):
        w = self.preview_canvas.winfo_width()
        h = self.preview_canvas.winfo_height()
        if event.x < w/2 and event.y < h/2:
            self.corner_var.set(0)
        elif event.x >= w/2 and event.y < h/2:
            self.corner_var.set(1)
        elif event.x < w/2 and event.y >= h/2:
            self.corner_var.set(2)
        else:
            self.corner_var.set(3)

    def on_recursive_change(self, event):
        self.recursive_var.set(self.recursive_combo.current() == 1)

    def get_first_image(self, folder, recursive):
        if recursive:
            for root, dirs, files in os.walk(folder):
                dirs[:] = [d for d in dirs if d not in ("правая", "левая")]
                for f in files:
                    if f.lower().endswith((".jpg", ".jpeg")):
                        return os.path.join(root, f)
        else:
            for f in os.listdir(folder):
                if f.lower().endswith((".jpg", ".jpeg")):
                    return os.path.join(folder, f)
        return None

    def update_preview(self):
        folder = self.folder_var.get()
        wm_path = self.wm_var.get()
        if not folder or not os.path.exists(folder) or not wm_path or not os.path.exists(wm_path):
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(250, 175, text="Выберите папку и водяной знак",
                                            font=('Segoe UI', 14), fill='#aaa')
            return

        recursive = self.recursive_combo.current() == 1
        first_img = self.get_first_image(folder, recursive)
        if not first_img:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(250, 175, text="Нет JPEG в выбранной папке",
                                            font=('Segoe UI', 14), fill='#aaa')
            return

        try:
            bg = Image.open(first_img).convert("RGBA")
            bg.thumbnail((500, 350), Image.Resampling.LANCZOS)
            bg_w, bg_h = bg.size

            wm = Image.open(wm_path).convert("RGBA")
            wm_w, wm_h = wm.size

            scale = self.scale_var.get() / 100.0
            margin = self.margin_var.get()
            max_wm_w = int(bg_w * scale)
            if wm_w > max_wm_w:
                ratio = max_wm_w / wm_w
                new_size = (max_wm_w, int(wm_h * ratio))
                wm = wm.resize(new_size, Image.Resampling.LANCZOS)
            wm_w, wm_h = wm.size

            corner = self.corner_var.get()
            if corner == 0:
                pos = (margin, margin)
            elif corner == 1:
                pos = (bg_w - wm_w - margin, margin)
            elif corner == 2:
                pos = (margin, bg_h - wm_h - margin)
            else:
                pos = (bg_w - wm_w - margin, bg_h - wm_h - margin)

            combined = bg.copy()
            combined.paste(wm, pos, wm)
            combined = combined.convert("RGB")

            self.preview_image = ImageTk.PhotoImage(combined)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
            self.master.preview_img = self.preview_image

        except Exception as e:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(250, 175, text=f"Ошибка: {e}", font=('Segoe UI', 12), fill='red')

    def show_help(self):
        help_text = (
            "Watermark Tool Pro\n\n"
            "Программа для массового нанесения водяного знака на JPEG-изображения.\n\n"
            "1. Выберите папку с фотографиями.\n"
            "2. Загрузите PNG-файл с водяным знаком (прозрачность поддерживается).\n"
            "3. Настройте размер, отступ и угол (кликните по предпросмотру).\n"
            "4. Выберите режим обхода:\n"
            "   - 'Только текущая папка' – обрабатываются только файлы в выбранной папке.\n"
            "   - 'Рекурсивно' – обрабатываются все подпапки.\n"
            "5. Нажмите 'Обработать' и следите за прогрессом.\n\n"
            "В каждой папке создаются подпапки:\n"
            "   'правая' – оригиналы с водяным знаком.\n"
            "   'левая' – отражённые копии (если включено).\n\n"
            "Исходные файлы не изменяются.\n"
            "Настройки автоматически сохраняются."
        )
        messagebox.showinfo("О программе", help_text)

    # ---------- Запуск обработки ----------
    def start_processing(self):
        if not self.folder_var.get() or not os.path.exists(self.folder_var.get()):
            messagebox.showerror("Ошибка", "Выберите корректную папку с фотографиями.")
            return
        if not self.wm_var.get() or not os.path.exists(self.wm_var.get()):
            messagebox.showerror("Ошибка", "Выберите корректный файл водяного знака.")
            return

        scale = self.scale_var.get() / 100.0
        margin = self.margin_var.get()
        mirror = self.mirror_var.get()
        corner = self.corner_var.get()
        recursive = self.recursive_combo.current() == 1
        wm_path = self.wm_var.get()
        folder = self.folder_var.get()

        save_config(scale, margin, mirror, corner, recursive, wm_path, folder)

        self.btn_start.config(state='disabled', text='Обработка...')
        self.progress_var.set(0)
        self.status_text.set("Начинаем обработку...")

        threading.Thread(target=run_processing,
                         args=(folder, wm_path, scale, margin, mirror, corner, recursive,
                               self.update_progress, self.finish_processing),
                         daemon=True).start()

    def update_progress(self, percent, text):
        self.progress_var.set(percent)
        self.status_text.set(text)
        self.master.update_idletasks()

    def finish_processing(self, message, is_error):
        self.btn_start.config(state='normal', text='Обработать все папки')
        if is_error:
            self.status_text.set(f"Ошибка: {message}")
            messagebox.showerror("Ошибка", message)
        else:
            self.status_text.set(message)
            self.progress_var.set(100)
            messagebox.showinfo("Завершено", message)

# ===================== ЗАПУСК =====================
def main():
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
