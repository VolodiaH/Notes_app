from datetime import date

from django.shortcuts import render


def index(request):
    notes = [
        {
            'title': 'Плани на тиждень',
            'content': 'Завершити головну сторінку застосунку.\nПовторити шаблони Django та роботу зі статичними файлами.',
            'category': 'Навчання',
            'created_at': date(2026, 10, 1),
        },
        {
            'title': 'Ідеї для проєкту',
            'content': 'Додати пошук за назвою та категорії нотаток.\nПродумати зручну форму для створення нових записів.',
            'category': 'Ідеї',
            'created_at': date(2026, 9, 30),
        },
        {
            'title': 'Список покупок',
            'content': 'Кава, молоко, яблука та хліб.\nНовий блокнот для записів.',
            'category': 'Особисте',
            'created_at': date(2026, 9, 29),
        },
    ]
    return render(request, 'notes/index.html', {'notes': notes})
