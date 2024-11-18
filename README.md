Структура проекта
-------------------

    bot/        скрипты бота (сообщения, клавиатуры, хэндлерсы)
    db/         скрипты работы с базой данных
    utils/      Утилиты

Требования
------------
Проект разрабатывался на python 3.13, используется библиотека python-telegram-bot 21.7
    
**Установка**
------------
- Скачать проект
~~~
git clone <project-path>
~~~
- Заменить файл /config/*.example на соответствующий конфиг
- База данных создается при первом запуске бота
- Создать виртуальное окружение python -m venv venv
~~~
python -m venv venv
~~~
- Активировать виртуальное окружение 
~~~
.\venv\Scripts\activate
~~~
- Установите все зависимости из requirements.txt
~~~
pip install -r requirements.txt
~~~