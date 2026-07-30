"""
Универсальный инструмент для массового нанесения водяного знака на JPEG-изображения.
Особенности:
- Рекурсивный обход всех подпапок
- Для каждой папки с фото создаёт:
    - 'правая' – оригиналы с водяным знаком (всегда)
    - 'левая' – отражённые по горизонтали копии (опционально, настраивается)
- При первом запуске – окно предпросмотра с настройками (размер, отступ, включение отражения)
- Настройки сохраняются в файл и используются при следующих запусках
- Исходные файлы не изменяются
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import configparser

# ===================== НАСТРОЙКИ ПО УМОЛЧАНИЮ =====================
DEFAULT_SCALE = 0.16          # 16% от ширины фото
DEFAULT_MARGIN = 30           # пикселей
DEFAULT_MIRROR = True         # создавать ли отражённые копии
CONFIG_FILE = "watermark_config.ini"

# ===================== РАБОТА С КОНФИГОМ =====================
def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if 'settings' in config:
            return {
                'scale': config.getfloat('settings', 'scale', fallback=DEFAULT_SCALE),
                'margin': config.getint('settings', 'margin', fallback=DEFAULT_MARGIN),
                'mirror': config.getboolean('settings', 'mirror', fallback=DEFAULT_MIRROR)
            }
    return {'scale': DEFAULT_SCALE, 'margin': DEFAULT_MARGIN, 'mirror': DEFAULT_MIRROR}

def save_config(scale, margin, mirror):
    config = configparser.ConfigParser()
    config['settings'] = {
        'scale': str(scale),
        'margin': str(margin),
        'mirror': str(mirror)
    }
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

# ===================== ПОИСК ПЕРВОГО ИЗОБРАЖЕНИЯ ДЛЯ ПРЕДПРОСМОТРА =====================
def find_first_image(root_dir):
    """Находит первый JPEG-файл в дереве папок для показа в предпросмотре."""
    for current_root, dirs, files in os.walk(root_dir):
        # Исключаем служебные папки, чтобы не зациклиться
        dirs[:] = [d for d in dirs if d not in ("правая", "левая")]
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg")):
                return os.path.join(current_root, f)
    return None

# ===================== ОБРАБОТКА ОДНОЙ ПАПКИ =====================
def process_folder(folder_path, watermark, wm_width, wm_height, scale, margin, mirror):
    """
    Обрабатывает одну папку:
    - Всегда создаёт 'правая' с водяным знаком.
    - Если mirror=True, создаёт 'левая' с отражёнными копиями.
    """
    files = [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".jpeg"))]
    if not files:
        return

    right_dir = os.path.join(folder_path, "правая")
    os.makedirs(right_dir, exist_ok=True)

    left_dir = None
    if mirror:
        left_dir = os.path.join(folder_path, "левая")
        os.makedirs(left_dir, exist_ok=True)

    print(f"Обработка: {folder_path}")

    for filename in files:
        image_path = os.path.join(folder_path, filename)
        try:
            with Image.open(image_path) as img:
                # ---------- Правая папка (оригинал + марка) ----------
                img_rgb = img.convert("RGBA") if img.mode != 'RGBA' else img
                wm_right = watermark.copy()
                bg_w, bg_h = img_rgb.size
                max_wm_w = int(bg_w * scale)
                if wm_width > max_wm_w:
                    ratio = max_wm_w / wm_width
                    new_size = (max_wm_w, int(wm_height * ratio))
                    wm_right = wm_right.resize(new_size, Image.Resampling.LANCZOS)
                wm_w, wm_h = wm_right.size
                pos = (margin, margin)
                combined = img_rgb.copy()
                combined.paste(wm_right, pos, wm_right)
                base, ext = os.path.splitext(filename)
                combined.convert("RGB").save(
                    os.path.join(right_dir, f"{base}_wm{ext}"), "JPEG", quality=95
                )

                # ---------- Левая папка (отражённое + марка) – только если нужно ----------
                if mirror:
                    mirrored = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                    mirrored_rgba = mirrored.convert("RGBA") if mirrored.mode != 'RGBA' else mirrored
                    wm_left = watermark.copy()
                    bg_w_l, bg_h_l = mirrored_rgba.size
                    max_wm_w_l = int(bg_w_l * scale)
                    if wm_width > max_wm_w_l:
                        ratio_l = max_wm_w_l / wm_width
                        new_size_l = (max_wm_w_l, int(wm_height * ratio_l))
                        wm_left = wm_left.resize(new_size_l, Image.Resampling.LANCZOS)
                    wm_w_l, wm_h_l = wm_left.size
                    pos_left = (margin, margin)
                    combined_left = mirrored_rgba.copy()
                    combined_left.paste(wm_left, pos_left, wm_left)
                    combined_left.convert("RGB").save(
                        os.path.join(left_dir, f"{base}_wm_mirrored{ext}"), "JPEG", quality=95
                    )

                print(f"  {filename} -> обработан")

        except Exception as e:
            print(f"  Ошибка с {filename}: {e}")

# ===================== ОСНОВНАЯ ФУНКЦИЯ ОБРАБОТКИ ВСЕХ ПАПОК =====================
def run_processing(scale, margin, mirror):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    watermark_path = os.path.join(script_dir, "mark.png")
    if not os.path.exists(watermark_path):
        messagebox.showerror("Ошибка", "Файл mark.png не найден!")
        return

    watermark = Image.open(watermark_path).convert("RGBA")
    wm_width, wm_height = watermark.size

    print("\nНачинаем рекурсивную обработку всех папок...")
    print(f"Размер: {scale*100:.0f}%, отступ: {margin}px")
    print(f"Отражённые копии: {'включены' if mirror else 'выключены'}\n")

    for root, dirs, files in os.walk(script_dir):
        # Исключаем служебные папки, чтобы не обрабатывать их повторно
        dirs[:] = [d for d in dirs if d not in ("правая", "левая")]
        process_folder(root, watermark, wm_width, wm_height, scale, margin, mirror)

    print("\n✅ Готово! Все папки обработаны.")
    messagebox.showinfo("Завершено", "Обработка всех папок завершена!")

# ===================== ОКНО ПРЕДПРОСМОТРА =====================
class PreviewWindow:
    def __init__(self, master, first_image_path):
        self.master = master
        master.title("Настройка водяного знака")
        master.geometry("800x750")

        # Загружаем конфиг
        config = load_config()
        self.scale = config['scale']
        self.margin = config['margin']
        self.mirror = config['mirror']

        # Загружаем водяной знак
        script_dir = os.path.dirname(os.path.abspath(__file__))
        watermark_path = os.path.join(script_dir, "mark.png")
        if not os.path.exists(watermark_path):
            messagebox.showerror("Ошибка", "mark.png не найден!")
            master.destroy()
            return
        self.watermark_orig = Image.open(watermark_path).convert("RGBA")
        self.wm_w, self.wm_h = self.watermark_orig.size

        # Загружаем первое изображение
        self.orig_image = Image.open(first_image_path)
        self.orig_image.thumbnail((600, 500))
        self.tk_image = ImageTk.PhotoImage(self.orig_image)

        # Холст для отображения
        self.canvas = tk.Canvas(master, width=600, height=500, bg='gray')
        self.canvas.pack(pady=10)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.preview_id = None

        # Фрейм для ползунков и галочки
        controls = tk.Frame(master)
        controls.pack(pady=10, fill='x')

        # Ползунок размера
        tk.Label(controls, text="Размер водяного знака (% от ширины фото):").grid(
            row=0, column=0, sticky='w'
        )
        self.scale_var = tk.DoubleVar(value=self.scale * 100)
        scale_slider = tk.Scale(
            controls, from_=5, to=50, orient='horizontal',
            variable=self.scale_var, length=300,
            command=self.update_preview
        )
        scale_slider.grid(row=0, column=1, padx=10)
        self.scale_label = tk.Label(controls, text=f"{self.scale_var.get():.0f}%")
        self.scale_label.grid(row=0, column=2)

        # Ползунок отступа
        tk.Label(controls, text="Отступ от края (пикселей):").grid(
            row=1, column=0, sticky='w', pady=5
        )
        self.margin_var = tk.IntVar(value=self.margin)
        margin_slider = tk.Scale(
            controls, from_=0, to=200, orient='horizontal',
            variable=self.margin_var, length=300,
            command=self.update_preview
        )
        margin_slider.grid(row=1, column=1, padx=10)
        self.margin_label = tk.Label(controls, text=f"{self.margin_var.get()}px")
        self.margin_label.grid(row=1, column=2)

        # Галочка "Создавать отражённые копии"
        self.mirror_var = tk.BooleanVar(value=self.mirror)
        mirror_check = tk.Checkbutton(
            controls,
            text="Создавать отражённые копии (папка 'левая')",
            variable=self.mirror_var,
            command=self.update_preview
        )
        mirror_check.grid(row=2, column=0, columnspan=3, pady=10, sticky='w')

        # Кнопка "Применить и обработать"
        btn_apply = tk.Button(
            master, text="Применить и обработать все папки",
            command=self.apply_and_process, bg="#5cb85c", fg="white",
            font=('Arial', 12), padx=20, pady=10
        )
        btn_apply.pack(pady=20)

        # Кнопка для выхода без обработки
        btn_exit = tk.Button(
            master, text="Выйти (без обработки)",
            command=master.destroy, bg="#d9534f", fg="white"
        )
        btn_exit.pack(pady=5)

        self.update_preview()

    def update_preview(self, event=None):
        """Обновляет предпросмотр с текущими параметрами (показывает только правую версию)."""
        scale = self.scale_var.get() / 100.0
        margin = self.margin_var.get()
        self.scale_label.config(text=f"{self.scale_var.get():.0f}%")
        self.margin_label.config(text=f"{margin}px")

        bg = self.orig_image.convert("RGBA")
        bg_w, bg_h = bg.size

        wm = self.watermark_orig.copy()
        max_wm_w = int(bg_w * scale)
        if self.wm_w > max_wm_w:
            ratio = max_wm_w / self.wm_w
            new_size = (max_wm_w, int(self.wm_h * ratio))
            wm = wm.resize(new_size, Image.Resampling.LANCZOS)
        wm_w, wm_h = wm.size

        pos = (margin, margin)
        combined = bg.copy()
        combined.paste(wm, pos, wm)

        combined = combined.convert("RGB")
        self.preview_image = ImageTk.PhotoImage(combined)
        if self.preview_id:
            self.canvas.delete(self.preview_id)
        self.preview_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
        self.master.preview_img = self.preview_image

    def apply_and_process(self):
        """Сохраняет настройки и запускает обработку."""
        scale = self.scale_var.get() / 100.0
        margin = self.margin_var.get()
        mirror = self.mirror_var.get()
        save_config(scale, margin, mirror)
        self.master.destroy()
        threading.Thread(target=run_processing, args=(scale, margin, mirror), daemon=True).start()
        messagebox.showinfo(
            "Запуск",
            "Обработка начата в фоновом режиме.\nСледите за консолью."
        )

# ===================== ТОЧКА ВХОДА =====================
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    watermark_path = os.path.join(script_dir, "mark.png")
    if not os.path.exists(watermark_path):
        print("ОШИБКА: mark.png не найден в папке со скриптом.")
        input("Нажмите Enter для выхода...")
        return

    # Если есть сохранённый конфиг – сразу запускаем обработку
    if os.path.exists(CONFIG_FILE):
        config = load_config()
        print(f"Настройки загружены: размер {config['scale']*100:.0f}%, отступ {config['margin']}px")
        print(f"Отражённые копии: {'включены' if config['mirror'] else 'выключены'}")
        print("Начинаем обработку...\n")
        run_processing(config['scale'], config['margin'], config['mirror'])
        input("\nНажмите Enter для выхода...")
        return

    # Иначе – открываем предпросмотр
    first_img = find_first_image(script_dir)
    if not first_img:
        print("Не найдено ни одного JPEG-изображения для предпросмотра.")
        input("Нажмите Enter для выхода...")
        return

    root = tk.Tk()
    app = PreviewWindow(root, first_img)
    root.mainloop()

if __name__ == "__main__":
    main()