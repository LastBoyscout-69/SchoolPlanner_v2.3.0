"""
Генератор ключей активации для SchoolPlanner.

ВАЖНО: этот файл НЕ ОТДАЁТСЯ пользователю!
Он используется только разработчиком для выдачи ключей покупателям.

Запуск:
    python keygen.py
"""

import sys
from license import _generate_key_from_number


def generate_keys(count, start_from=1):
    """
    Генерирует count ключей, начиная с номера start_from.
    Возвращает список кортежей (номер, ключ).
    """
    keys = []
    for n in range(start_from, start_from + count):
        keys.append((n, _generate_key_from_number(n)))
    return keys


def main():
    print("=" * 60)
    print("  🔑 Генератор ключей SchoolPlanner")
    print("=" * 60)
    print()

    # Спрашиваем количество
    try:
        count_str = input("Сколько ключей сгенерировать? [по умолчанию 10]: ").strip()
        count = int(count_str) if count_str else 10
    except ValueError:
        print("❌ Ошибка: нужно ввести число.")
        sys.exit(1)

    if count <= 0:
        print("❌ Ошибка: количество должно быть больше 0.")
        sys.exit(1)

    if count > 1000:
        print("⚠️ Внимание: больше 1000 ключей за раз — не рекомендуется.")

    # Спрашиваем, с какого номера начать
    try:
        start_str = input("Начать с номера? [по умолчанию 1]: ").strip()
        start_from = int(start_str) if start_str else 1
    except ValueError:
        print("❌ Ошибка: нужно ввести число.")
        sys.exit(1)

    # Генерируем
    print()
    print(f"Генерирую {count} ключей, начиная с #{start_from}...")
    print()

    keys = generate_keys(count, start_from)

    # Выводим
    print("=" * 60)
    print(f"  Сгенерировано {len(keys)} ключей:")
    print("=" * 60)
    for n, key in keys:
        print(f"  #{n:<5}  {key}")
    print("=" * 60)
    print()

    # Сохраняем в файл
    save_to_file = input("Сохранить в файл keys.txt? [y/n]: ").strip().lower()
    if save_to_file in ("y", "yes", "да", "д"):
        filename = "keys.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"  Ключи SchoolPlanner — {len(keys)} шт.\n")
                f.write("=" * 60 + "\n\n")
                for n, key in keys:
                    f.write(f"#{n:<5}  {key}\n")
            print(f"✅ Сохранено в {filename}")
        except IOError as e:
            print(f"❌ Не удалось сохранить: {e}")
    else:
        print("Ключи не сохранены в файл.")

    print()
    print("Готово! Отдай ключи покупателям.")
    print("Пользователь вводит ключ в программе → активация.")


if __name__ == "__main__":
    main()