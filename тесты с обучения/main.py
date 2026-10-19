import calc

# Используем константу
print(calc.PI)
# Вызываем функции
print(calc.add(10, 5))
print(calc.divide(10, 3))
# Создаём объект класса
my_circle = calc.Circle(10)
print(my_circle.area())