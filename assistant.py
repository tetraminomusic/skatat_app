import json
import os
import random
import subprocess
import sys
import threading
import time
import warnings
import easyocr
from google import genai
from pynput import keyboard

warnings.filterwarnings("ignore")

CONFIG_FILE = "config.json"


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"Файл {CONFIG_FILE} не найден! Создайте его рядом со скриптом."
        )
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_config()

API_KEY = CONFIG.get("api_key") or os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "Не найдена переменная окружения GEMINI_API_KEY и не указан api_key в config.json!"
    )

print(" \033[31mSkatat'")
print(" 1.1 MAC OS")
print(" by tetramino\033[0m")

client = genai.Client(api_key=API_KEY)
ocr_reader = easyocr.Reader(["ru", "en"])

keyboard_controller = keyboard.Controller()
stop_typing_event = threading.Event()


def show_mac_notification(body: str, title: str):
    if CONFIG.get("silent_mode", False):
        return

    safe_body = (
        body.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    )
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    script = f'display notification "{safe_body}" with title "{safe_title}" sound name "default"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def get_text_from_screenshot() -> str:
    tmp_path = "/tmp/gemini_ocr_capture.png"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    res = subprocess.run(["screencapture", "-i", tmp_path])

    if res.returncode != 0 or not os.path.exists(tmp_path):
        return ""

    print("[ocr] Распознаем текст с области...")
    lines = ocr_reader.readtext(tmp_path, detail=0)

    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    return "\n".join(lines).strip()


def ask_gemini_text(prompt: str) -> str:
    models_to_try = CONFIG["models"].copy()
    random.shuffle(models_to_try)

    for model in models_to_try:
        print(f"\n[*] Выбрана модель: {model}")
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                err_str = str(e)
                if (
                    "503" in err_str
                    or "UNAVAILABLE" in err_str
                    or "429" in err_str
                    or "RESOURCE_EXHAUSTED" in err_str
                ):
                    print(
                        f"    [503/429] {model} занята. Попытка {attempt}/3 через 1.5 сек..."
                    )
                    time.sleep(1.5)
                elif "404" in err_str or "NOT_FOUND" in err_str:
                    print(
                        f"    [404] Модель {model} не существует. Пропускаем."
                    )
                    break
                else:
                    raise RuntimeError(f"Ошибка Gemini API: {e}")

        print(f" [fallback] {model} not reponse, changing one")

    raise RuntimeError("Братан не робит нухия, потерпи")


def process_simple():
    raw_text = get_text_from_screenshot()
    if not raw_text:
        print(" [simple] Text not found or get")
        return

    print(f"\n[распознано]:\n{raw_text}\n")

    template = CONFIG["prompts"]["simple_test"]
    prompt = template.format(text=raw_text)

    print(" [simple] Отправка чистого текста в Gemini...")
    try:
        answer = ask_gemini_text(prompt)
        print(f"\n=== ОТВЕТ ===\n{answer}\n=============")
        show_mac_notification(answer, "Ответ на тест")
    except Exception as e:
        print(f"[error] {e}")
        show_mac_notification(str(e), "Ошибка")


def process_hard():
    raw_text = get_text_from_screenshot()
    if not raw_text:
        print(" [hard] Выделение отменено или текст не найден.")
        return

    print(f"\n[распознано]:\n{raw_text}\n")

    template = CONFIG["prompts"]["hard_task"]
    prompt = template.format(text=raw_text)

    print("[hard request]")
    try:
        code = ask_gemini_text(prompt)

        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(
                lines[1:-1] if lines[-1].startswith("```") else lines[1:]
            )

        code = code.replace("\t", "    ").strip()

        countdown = CONFIG["typing_settings"]["countdown"]
        show_mac_notification(
            f"Ответ есть епта! Кликни в поле ввода (ввод начнётся через {countdown} сек)",
            "Внимание",
        )

        for i in range(countdown, 0, -1):
            print(f"Печать через {i}...")
            time.sleep(1)

        smart_layout_switch(code)

        stop_typing_event.clear()
        print(" [hard] Поехали нахуй...")

        min_delay = CONFIG["typing_settings"]["min_delay"]
        max_delay = CONFIG["typing_settings"]["max_delay"]

        for ch in code:
            if stop_typing_event.is_set():
                print(" [stop] Ты дебил бля зачем печать остановил.")
                show_mac_notification("Печать остановлена", "Стоп")
                return

            if ch == "\n":
                keyboard_controller.tap(keyboard.Key.enter)
            else:
                keyboard_controller.type(ch)

            time.sleep(random.uniform(min_delay, max_delay))

        show_mac_notification("Лее, братан, напечатали", "Всё норм")
    except Exception as e:
        print(f"[error] {e}")
        show_mac_notification(str(e), "Ошибка")


def stop_typing():
    print("[stop] Экстренная остановка")
    stop_typing_event.set()


def smart_layout_switch(text: str):
    has_russian = any("а" <= char.lower() <= "я" for char in text)

    if not has_russian:
        print(
            "[layout] changing to ABC layout"
        )
        apple_script = """
        tell application "System Events"
            set selected input source of current locale to input source "com.apple.keylayout.ABC"
        end tell
        """
        try:
            subprocess.run(
                ["osascript", "-e", apple_script], capture_output=True
            )
            time.sleep(0.2)
        except Exception:
            pass
    else:
        print("[layout] found RU layout")


HOTKEYS = {
    "<cmd>+<shift>+3": lambda: threading.Thread(target=process_simple).start(),
    "<cmd>+<shift>+2": lambda: threading.Thread(target=process_hard).start(),
    "<cmd>+<shift>+1": stop_typing,
}


def main():
    global CONFIG
    print()
    print(" Управление ёпта, ставим английскую раскладку")
    print(" \033[32mCmd + Shift + 3\033[0m : Ответ на тест (всплывающее уведомление)")
    print(" \033[32mCmd + Shift + 2\033[0m : Решение задачи (автопечать кода)")
    print(" \033[32mCmd + Shift + 1\033[0m : Экстренная остановка печати")
    print()
    print(
        f" Silent Mode: {'\033[31mВКЛ\033[0m' if CONFIG.get('silent_mode') else '\033[32mВЫКЛ\033[0m'}"
    )
    print(" Доступные команды в терминале: silent, reload, exit")
    print()

    listener = keyboard.GlobalHotKeys(HOTKEYS)
    listener.start()

    try:
        while True:
            cmd = input(" ").strip().lower()
            if cmd == "exit":
                listener.stop()
                sys.exit(0)
            elif cmd == "silent":
                CONFIG["silent_mode"] = not CONFIG.get("silent_mode", False)
                state = "ВКЛ" if CONFIG["silent_mode"] else "ВЫКЛ"
                print(f" [silent] Режим без уведомлений: {state}")
            elif cmd == "reload":
                CONFIG = load_config()
                print("[config] Файл config.json перезагружен.")
            elif cmd != "":
                print("Команды: silent, reload, exit")
    except (KeyboardInterrupt, SystemExit):
        listener.stop()
        print("\n [выход] Goodbye ёпта")


if __name__ == "__main__":
    main()