import os
import random
import subprocess
import threading
import time
import warnings
import easyocr
import sys
from google import genai
from pynput import keyboard

warnings.filterwarnings("ignore")

API_KEY = os.getenv("GEMINI_API_KEY")

'''
    В целом можете ввести свой API_KEY через обычную переменную
'''

if not API_KEY:
    raise ValueError(
        "Не найдена переменная окружения GEMINI_API_KEY! Проверьте файл .zshrc"
    )


print(" \033[31mSkatat'")
print(" 1.0 MAC OS")
print(" by tetramino\033[0m")

client = genai.Client(api_key=API_KEY)

ocr_reader = easyocr.Reader(["ru", "en"])

keyboard_controller = keyboard.Controller()
stop_typing_event = threading.Event()


def show_mac_notification(body: str, title: str):
    safe_body = (
        body.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    )
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    script = f'display notification "{safe_body}" with title "{safe_title}" sound name "default"'
    subprocess.run(["osascript", "-e", script])


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
    models_to_try = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]

    random.shuffle(models_to_try)

    for model in models_to_try:
        print(f"\n[*] Выбрана модель: {model}")
        for attempt in range(1, 4):  # 3 попытки на каждую модель
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(
                        f"    [503/429] {model} занята. Попытка {attempt}/3 через 1.5 сек..."
                    )
                    time.sleep(1.5)
                elif "404" in err_str or "NOT_FOUND" in err_str:
                    print(f"    [404] Модель {model} не существует. Пропускаем.")
                    break
                else:
                    # Если ошибка другая (например, сетевая), сразу выбрасываем
                    raise RuntimeError(f"Ошибка Gemini API: {e}")

        print(f"[fallback] {model} не ответила, переключаемся на резерв...")

    raise RuntimeError("Братан не робит нухия, потерпи")

def process_simple():
    raw_text = get_text_from_screenshot()
    if not raw_text:
        print("[simple] Выделение отменено или текст не найден.")
        return

    print(f"\n[распознано]:\n{raw_text}\n")

    prompt = f"""
                Ты ассистент по тестам. Ниже вопрос (в нем могут быть мелкие опечатки OCR распознавания):
                \"\"\"
                {raw_text}
                \"\"\"

                Задание:
                Привет, нужно ответить на вопрос касательно ассемблера и gdb, если перед тобой будет множественный ответ, то выпиши порядковый номер правильного ответа. Не пиши очень много текста или комментарий, не надо объяснений, просто ответ и всё, желательно кратко и по делу. В заданиях могут быть сразу несколько ответов к вопросам.
            """
    print("[simple] Отправка чистого текста в Gemini...")
    try:
        answer = ask_gemini_text(prompt)
        print(f"\n=== ОТВЕТ ===\n{answer}\n=============")
        show_mac_notification(answer, "Ответ на тест")
    except Exception as e:
        print(f"[error] {e}")
        show_mac_notification(str(e), "Ошибка")


def process_hard():
    """Режим кода: решение задачи и человекоподобная печать в поле ввода (только OCR)."""
    raw_text = get_text_from_screenshot()
    if not raw_text:
        print("[hard] Выделение отменено или текст не найден.")
        return

    print(f"\n[распознано]:\n{raw_text}\n")

    prompt = f"""
                    Напиши решение для следующей задачи (текст получен через OCR):
                    \"\"\"
                    {raw_text}
                    \"\"\"

                    Требования:
                    - Если требуется написать код, ты должен написать код. 
                    - Если просят в задании ответ, то пишешь только ответ без пояснений. Не придумывай сам условия, сконцентрируйся только на задаче
                    - Если потребуется развёрнутый ответ по теоритической базе, то напиши предложенией 4-5 по этому поводу
                    - Без маркдауна и тройных кавычек (```).
                """
    print("[hard request]")
    try:
        code = ask_gemini_text(prompt)
        
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            
        code = code.replace("\t", "    ").strip()

        show_mac_notification(
            "Ответ есть епта! Кликни в поле ввода (ввод начнётся через 3 сек)", "Внимание"
        )
        time.sleep(3)

        smart_layout_switch(code)

        stop_typing_event.clear()
        print("[hard] Поехали нахуй...")

        for ch in code:
            if stop_typing_event.is_set():
                print("[stop] Ты дебил бля зачем печать остановил.")
                show_mac_notification("Печать остановлена", "Стоп")
                return

            if ch == "\n":
                keyboard_controller.tap(keyboard.Key.enter)
            else:
                keyboard_controller.type(ch)

            time.sleep(random.uniform(0.02, 0.08))

        show_mac_notification("Лее, братан, напечатали", "Всё норм")
    except Exception as e:
        print(f"[error] {e}")
        show_mac_notification(str(e), "Ошибка")


def stop_typing():
    print("[stop] Экстренная остановка")
    stop_typing_event.set()

def smart_layout_switch(text: str):
    has_russian = any('а' <= char.lower() <= 'я' for char in text)
    
    if not has_russian:
        print("[layout] Обнаружен код/латиница. Переключаем на английский (ABC)...")
        apple_script = '''
        tell application "System Events"
            set selected input source of current locale to input source "com.apple.keylayout.ABC"
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", apple_script], capture_output=True)
            time.sleep(0.2)
        except Exception:
            pass
    else:
        print("[layout] Обнаружен русский текст (теория). Раскладка не трогается")


HOTKEYS = {
    "<cmd>+<shift>+3": lambda: threading.Thread(
        target=process_simple
    ).start(),

    "<cmd>+<shift>+2": lambda: threading.Thread(
        target=process_hard
    ).start(),
    
    "<cmd>+<shift>+1": stop_typing,
}


def main():
    print()
    print(" Управление ёпта, ставим английскую раскладку")
    print(" \033[32mCmd + Shift + 3\033[0m : Ответ на тест (всплывающее уведомление)")
    print(" \033[32mCmd + Shift + 2\033[0m : Решение задачи (автопечать кода)")
    print(" \033[32mCmd + Shift + 1\033[0m : Экстренная остановка печати")

    listener = keyboard.GlobalHotKeys(HOTKEYS)
    listener.start()

    try:
        while True:
            cmd = input().strip().lower()
            if cmd == "exit":
                listener.stop()
                sys.exit(0)
            elif cmd != "":
                print(f"Неизвестная команда. Введите 'exit' для выхода.")
    except (KeyboardInterrupt, SystemExit):
        listener.stop()
        print(f"\n[выход] Приложение остановлено. Удачи!")

if __name__ == "__main__":
    main()