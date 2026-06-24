import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any

from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import aiohttp
from aiohttp import ClientTimeout

BOT_TOKEN = "8515421734:AAFmBit7CCCuyDDl810dsNp9NCWddcl6ouY"
PROXY = ""
YANDEX_FOLDER_ID = "b1gmc24t59jts6c3uus8"
YANDEX_API_KEY = "AQVNyWe5xXXKPcAqr_VZZ_amBlAODtKUTqp4-WOZ"
YANDEX_MODEL = "yandexgpt-lite"
YANDEX_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

logging.basicConfig(level=logging.INFO)

if PROXY:
    session = AiohttpSession(proxy=PROXY)
else:
    session = AiohttpSession()

bot = Bot(token=BOT_TOKEN, session=session)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class SurveyStates(StatesGroup):
    WAITING_ACTIVITIES = State()
    INTERESTS = State()
    SUBJECTS = State()
    GOALS = State()
    WORKLOAD = State()
    ACTIVITY_FORMAT = State()
    DIFFICULTY = State()
    SHOW_RESULTS = State()

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пройти анкету")]],
        resize_keyboard=True
    )

def get_activities_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Готово (завершить ввод)")]],
        resize_keyboard=True
    )

def get_interests_keyboard():
    builder = ReplyKeyboardBuilder()
    interests = [
        "Программирование", "Робототехника", "Дизайн",
        "Безопасность", "Аналитика", "Игры",
        "Природа/Экология", "Помощь людям", "Бизнес",
        "Обучение", "Спорт", "Музыка/Искусство"
    ]
    for interest in interests:
        builder.add(KeyboardButton(text=interest))
    builder.add(KeyboardButton(text="Готово"))
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True)

def get_subjects_keyboard():
    builder = ReplyKeyboardBuilder()
    subjects = [
        "Информатика", "Математика", "Физика", "Биология",
        "Химия", "ИЗО", "Литература", "Обществознание",
        "География", "История", "Иностранный язык"
    ]
    for subject in subjects:
        builder.add(KeyboardButton(text=subject))
    builder.add(KeyboardButton(text="Готово"))
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True)

def get_goals_keyboard():
    builder = ReplyKeyboardBuilder()
    goals = [
        "Научиться программировать", "Сделать свой проект",
        "Помочь людям", "Найти новых друзей", "Создать свою игру",
        "Изучить безопасность", "Стать волонтёром", "Запустить стартап"
    ]
    for goal in goals:
        builder.add(KeyboardButton(text=goal))
    builder.add(KeyboardButton(text="Готово"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_workload_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Низкая (1-3 часа в неделю)")],
            [KeyboardButton(text="Средняя (4-8 часов в неделю)")],
            [KeyboardButton(text="Высокая (9+ часов в неделю)")]
        ],
        resize_keyboard=True
    )

def get_format_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Офлайн")],
            [KeyboardButton(text="Онлайн")],
            [KeyboardButton(text="Смешанный формат")]
        ],
        resize_keyboard=True
    )

def get_difficulty_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Новичок")],
            [KeyboardButton(text="Средний уровень")],
            [KeyboardButton(text="Продвинутый")]
        ],
        resize_keyboard=True
    )

# ===================== ИИ =======================================

async def query_yandex(prompt: str) -> str:
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}",
        "completionOptions": {
            "temperature": 0.7,
            "maxTokens": 1000
        },
        "messages": [
            {"role": "user", "text": prompt}
        ]
    }
    timeout = ClientTimeout(total=30)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as aio_session:
            proxy_arg = PROXY if PROXY else None
            async with aio_session.post(YANDEX_URL, json=payload, headers=headers, proxy=proxy_arg) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "result" in data and "alternatives" in data["result"] and data["result"]["alternatives"]:
                        alternative = data["result"]["alternatives"][0]
                        if "message" in alternative and "text" in alternative["message"]:
                            return alternative["message"]["text"].strip()
                    logging.error(f"Unexpected Yandex response structure: {data}")
                    return ""
                else:
                    error_text = await resp.text()
                    logging.error(f"Yandex API error: {resp.status} - {error_text}")
                    return ""
    except Exception as e:
        logging.error(f"Exception during Yandex query: {e}")
        return ""

def build_prompt(activities: List[str], answers: Dict[str, Any]) -> str:
    interests_str = ", ".join(answers.get("interests", []))
    subjects_str = ", ".join(answers.get("subjects", []))
    goals_str = ", ".join(answers.get("goals", []))

    prompt = (
        "Ты – помощник, который подбирает кружки, секции и волонтёрские активности.\n"
        "Пользователь заполнил анкету. Обращайся к нему на 'ты' (во втором лице).\n\n"
        f"Его интересы: {interests_str}\n"
        f"Любимые предметы: {subjects_str}\n"
        f"Цели: {goals_str}\n"
        f"Уровень занятости: {answers.get('workload', 'не указано')}\n"
        f"Предпочитаемый формат: {answers.get('format', 'не указано')}\n"
        f"Желаемая сложность: {answers.get('difficulty', 'не указано')}\n\n"
        "Список доступных активностей:\n"
    )
    for act in activities:
        prompt += f"- {act}\n"
    prompt += (
        "\nНа основе анкеты выбери ДВЕ активности, которые лучше всего подходят пользователю: "
        "первую как наилучший вариант, вторую как альтернативу. "
        "Для каждой дай краткое пояснение, почему она подходит. "
        "Используй обращения 'тебе', 'ты', 'твой' и т.п. "
        "Структурируй ответ так:\n"
        "**Лучший вариант:**\n<название>\nОбъяснение: <текст>\n\n"
        "**Альтернативный вариант:**\n<название>\nОбъяснение: <текст>\n"
        "Если в списке меньше двух активностей, предложи общие рекомендации по развитию."
    )
    return prompt

# ===================== СОХРАНЕНИЕ ДАННЫХ ===========================

def save_record(user_id: int, activities: List[str], answers: Dict[str, Any], recommendations: str):
    record = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "activities": activities,
        "answers": answers,
        "recommendations": recommendations
    }
    try:
        with open("user_data.txt", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logging.info(f"Data saved for user {user_id}")
    except Exception as e:
        logging.error(f"Failed to save record: {e}")

# =================================================================

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я помогу подобрать кружки, секции или волонтёрские проекты.\n\n"
        "Сначала напиши список активностей, которые ты рассматриваешь (каждую с новой строки).\n"
        "Когда закончишь, нажми кнопку 'Готово'.\n\n"
        "После этого я задам несколько вопросов и дам рекомендации.",
        parse_mode="Markdown",
        reply_markup=get_activities_keyboard()
    )
    await state.set_state(SurveyStates.WAITING_ACTIVITIES)
    await state.update_data(activities=[])

@dp.message(StateFilter(SurveyStates.WAITING_ACTIVITIES))
async def process_activities(message: types.Message, state: FSMContext):
    if message.text == "Готово (завершить ввод)":
        data = await state.get_data()
        activities = data.get("activities", [])
        if len(activities) < 2:
            await message.answer("Введи хотя бы 2 активности!")
            return
        await state.update_data(activities=activities)
        await state.set_state(SurveyStates.INTERESTS)
        await message.answer(
            "Шаг 1 из 6: Твои интересы\n\n"
            "Выбери до 5 интересов (нажимай на кнопки).\n"
            "Когда выберешь всё, нажми 'Готово'.\n"
            "Если твоего интереса нет в списке, просто напиши его текстом.",
            parse_mode="Markdown",
            reply_markup=get_interests_keyboard()
        )
        await state.update_data(interests=[])
        return

    text = message.text.strip()
    if not text:
        await message.answer("Активность не может быть пустой.")
        return

    data = await state.get_data()
    activities = data.get("activities", [])
    if text not in activities:
        activities.append(text)
        await state.update_data(activities=activities)
        await message.answer(f"Добавлено: '{text}' (всего {len(activities)})")
    else:
        await message.answer("Эта активность уже добавлена.")

@dp.message(StateFilter(SurveyStates.INTERESTS))
async def process_interests(message: types.Message, state: FSMContext):
    if message.text == "Готово":
        data = await state.get_data()
        interests = data.get("interests", [])
        if len(interests) < 2:
            await message.answer("Выбери хотя бы 2 интереса!")
            return
        await state.set_state(SurveyStates.SUBJECTS)
        await message.answer(
            "Шаг 2 из 6: Любимые предметы\n\n"
            "Выбери до 3 любимых школьных предметов.\n"
            "Когда закончишь, нажми 'Готово'.\n"
            "Можешь написать свой вариант.",
            parse_mode="Markdown",
            reply_markup=get_subjects_keyboard()
        )
        await state.update_data(subjects=[])
        return

    data = await state.get_data()
    interests = data.get("interests", [])
    if message.text not in interests and len(interests) < 5:
        interests.append(message.text)
        await state.update_data(interests=interests)
        await message.answer(f"Добавлено: {message.text} (осталось {5 - len(interests)})")
    elif len(interests) >= 5:
        await message.answer("Ты уже выбрал максимум 5 интересов! Нажми 'Готово'.")
    else:
        await message.answer("Этот интерес уже добавлен.")

@dp.message(StateFilter(SurveyStates.SUBJECTS))
async def process_subjects(message: types.Message, state: FSMContext):
    if message.text == "Готово":
        data = await state.get_data()
        subjects = data.get("subjects", [])
        if len(subjects) < 1:
            await message.answer("Выбери хотя бы один предмет!")
            return
        await state.set_state(SurveyStates.GOALS)
        await message.answer(
            "Шаг 3 из 6: Твои цели\n\n"
            "Выбери до 3 целей.\n"
            "Когда закончишь, нажми 'Готово'.\n"
            "Можешь написать свою цель.",
            parse_mode="Markdown",
            reply_markup=get_goals_keyboard()
        )
        await state.update_data(goals=[])
        return

    data = await state.get_data()
    subjects = data.get("subjects", [])
    if message.text not in subjects and len(subjects) < 3:
        subjects.append(message.text)
        await state.update_data(subjects=subjects)
        await message.answer(f"Добавлено: {message.text} (осталось {3 - len(subjects)})")
    elif len(subjects) >= 3:
        await message.answer("Ты уже выбрал максимум 3 предмета! Нажми 'Готово'.")
    else:
        await message.answer("Этот предмет уже добавлен.")

@dp.message(StateFilter(SurveyStates.GOALS))
async def process_goals(message: types.Message, state: FSMContext):
    if message.text == "Готово":
        data = await state.get_data()
        goals = data.get("goals", [])
        if len(goals) < 1:
            await message.answer("Выбери хотя бы одну цель!")
            return
        await state.set_state(SurveyStates.WORKLOAD)
        await message.answer(
            "Шаг 4 из 6: Уровень занятости\n\n"
            "Сколько времени ты готов уделять активности в неделю?\n"
            "Выбери один из вариантов на клавиатуре.",
            parse_mode="Markdown",
            reply_markup=get_workload_keyboard()
        )
        return

    data = await state.get_data()
    goals = data.get("goals", [])
    if message.text not in goals and len(goals) < 3:
        goals.append(message.text)
        await state.update_data(goals=goals)
        await message.answer(f"Добавлено: {message.text} (осталось {3 - len(goals)})")
    elif len(goals) >= 3:
        await message.answer("Ты уже выбрал максимум 3 цели! Нажми 'Готово'.")
    else:
        await message.answer("Эта цель уже добавлена.")

@dp.message(StateFilter(SurveyStates.WORKLOAD))
async def process_workload(message: types.Message, state: FSMContext):
    if message.text in ["Низкая (1-3 часа в неделю)", "Средняя (4-8 часов в неделю)", "Высокая (9+ часов в неделю)"]:
        await state.update_data(workload=message.text)
        await state.set_state(SurveyStates.ACTIVITY_FORMAT)
        await message.answer(
            "Шаг 5 из 6: Формат активности\n\n"
            "Какой формат тебе удобнее? Выбери на клавиатуре.",
            parse_mode="Markdown",
            reply_markup=get_format_keyboard()
        )
    else:
        await message.answer("Пожалуйста, выбери один из вариантов на клавиатуре.")

@dp.message(StateFilter(SurveyStates.ACTIVITY_FORMAT))
async def process_format(message: types.Message, state: FSMContext):
    if message.text in ["Офлайн", "Онлайн", "Смешанный формат"]:
        await state.update_data(format=message.text)
        await state.set_state(SurveyStates.DIFFICULTY)
        await message.answer(
            "Шаг 6 из 6: Желаемая сложность\n\n"
            "Какой уровень сложности тебе подойдёт? Выбери на клавиатуре.",
            parse_mode="Markdown",
            reply_markup=get_difficulty_keyboard()
        )
    else:
        await message.answer("Пожалуйста, выбери один из вариантов на клавиатуре.")

@dp.message(StateFilter(SurveyStates.DIFFICULTY))
async def process_difficulty(message: types.Message, state: FSMContext):
    if message.text in ["Новичок", "Средний уровень", "Продвинутый"]:
        await state.update_data(difficulty=message.text)
        await state.set_state(SurveyStates.SHOW_RESULTS)
        await show_results(message, state)
    else:
        await message.answer("Пожалуйста, выбери один из вариантов на клавиатуре.")

async def show_results(message: types.Message, state: FSMContext):
    data = await state.get_data()
    activities = data.get("activities", [])
    answers = {
        "interests": data.get("interests", []),
        "subjects": data.get("subjects", []),
        "goals": data.get("goals", []),
        "workload": data.get("workload", ""),
        "format": data.get("format", ""),
        "difficulty": data.get("difficulty", "")
    }

    await message.answer("Обрабатываю твои ответы с помощью Yandex AI... это может занять до 30 секунд.")

    prompt = build_prompt(activities, answers)
    recommendations = await query_yandex(prompt)

    if not recommendations:
        recommendations = "Не удалось получить рекомендации. Попробуй позже или измени ответы."

    save_record(message.from_user.id, activities, answers, recommendations)

    result_text = "Твои рекомендации:\n\n"
    result_text += recommendations
    result_text += "\n\nЧтобы пройти заново, нажми /start"

    await message.answer(result_text, reply_markup=ReplyKeyboardRemove())
    await state.clear()

@dp.message()
async def catch_all(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Я не понимаю эту команду.\n"
            "Используй кнопки или напиши /start",
            reply_markup=get_main_keyboard()
        )
    else:
        state_name = current_state.split(":")[-1]
        hints = {
            "WAITING_ACTIVITIES": "Введи активности (каждую с новой строки) или нажми 'Готово'.",
            "INTERESTS": "Выбери интересы из кнопок или напиши свой, затем нажми 'Готово'.",
            "SUBJECTS": "Выбери предметы из кнопок или напиши свой, затем нажми 'Готово'.",
            "GOALS": "Выбери цели из кнопок или напиши свою, затем нажми 'Готово'.",
            "WORKLOAD": "Выбери уровень занятости из кнопок.",
            "ACTIVITY_FORMAT": "Выбери формат из кнопок.",
            "DIFFICULTY": "Выбери сложность из кнопок."
        }
        hint = hints.get(state_name, "Пожалуйста, следуй инструкциям на экране.")
        await message.answer(f"Сейчас мы на шаге: {state_name}\n{hint}", reply_markup=ReplyKeyboardRemove())

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
