import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
import config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем специалистов из JSON
try:
    with open('specialists.json', 'r', encoding='utf-8') as f:
        SPECIALISTS = json.load(f)
    print(f"✅ Загружено {len(SPECIALISTS)} специалистов")
except Exception as e:
    print(f"❌ Ошибка загрузки specialists.json: {e}")
    SPECIALISTS = {}

# Состояния для ConversationHandler
(INDIVIDUAL_CHOICE, AGE_CHECK, AGE_15_CHECK, FORMAT_CHOICE, TOPIC_CHOICE,
 CHILD_CHOICE, NEURO_CHOICE, GROUP_CHOICE) = range(8)

# Хранилище данных пользователя
user_data = {}

# Глобальная ссылка на ConversationHandler
conv_handler = None

# Все темы для офлайн
OFFLINE_TOPICS = [
    ("родительство", ["Юлия Курчанова", "Александра Иванова", "Мария Белых"]),
    ("трудности в межличностных отношениях", ["Анастасия Дира", "Александра Иванова", "Лала Джагитян", "Мария Белых"]),
    ("я страдаю от насилия", ["Александра Иванова", "Анастасия Дира"]),
    ("Я — автор насилия", ["Александра Иванова", "Анастасия Дира"]),
    ("самооценка и самоценность", ["Анастасия Дира", "Александра Иванова", "Лала Джагитян", "Екатерина Бычкова", "Мария Белых"]),
    ("тревога и тревожные состояния", ["Анастасия Дира", "Александра Иванова", "Мария Белых"]),
    ("тяжелый кризис", ["Александра Иванова", "Анна Карманова", "Анастасия Дира", "Мария Белых"]),
    ("я потерял(а) близкого человека", ["Александра Иванова", "Анастасия Дира", "Лала Джагитян", "Мария Белых"]),
    ("выгорание", ["Екатерина Бычкова"]),
    ("потеря смыслов и ценностей", ["Александра Иванова", "Лала Джагитян", "Анастасия Дира", "Мария Белых"]),
    ("я проживаю тяжелый период", ["Анастасия Дира", "Александра Иванова", "Лала Джагитян", "Мария Белых"]),
    ("мой близкий человек употребляет ПАВ/алкоголь", ["Анна Карманова", "Анастасия Дира"]),
    ("у меня депрессия/диагностировано психическое расстройство врачом-психиатром", ["Юлия Курчанова"]),  # 👈 НОВАЯ ТЕМА
]

# Все темы для онлайн
ONLINE_TOPICS = [
    ("родительство", ["Юлия Курчанова", "Александра Иванова", "Армина Нерсесян", "Мария Белых"]),
    ("трудности в межличностных отношениях", ["Анастасия Дира", "Александра Иванова", "Лала Джагитян", "Армина Нерсесян", "Анастасия Блинова", "Вилена Васильева", "Мария Белых"]),
    ("я страдаю от насилия", ["Александра Иванова", "Анастасия Дира", "Армина Нерсесян"]),
    ("Я — автор насилия", ["Александра Иванова", "Анастасия Дира"]),
    ("самооценка и самоценность", ["Анастасия Дира", "Александра Иванова", "Лала Джагитян", "Екатерина Бычкова", "Анна Карманова", "Анастасия Блинова", "Вилена Васильева", "Армина Нерсесян", "Мария Белых"]),
    ("тревога и тревожные состояния", ["Анастасия Блинова", "Анастасия Дира", "Александра Иванова", "Армина Нерсесян", "Вилена Васильева", "Мария Белых"]),
    ("тяжелый кризис", ["Анастасия Блинова", "Александра Иванова", "Анна Карманова", "Армина Нерсесян", "Вилена Васильева", "Мария Белых"]),
    ("я потерял(а) близкого человека", ["Александра Иванова", "Анастасия Дира", "Лала Джагитян", "Армина Нерсесян", "Мария Белых"]),
    ("выгорание", ["Екатерина Бычкова"]),
    ("потеря смыслов и ценностей", ["Александра Иванова", "Вилена Васильева", "Лала Джагитян", "Армина Нерсесян", "Мария Белых"]),
    ("я проживаю тяжелый период", ["Анастасия Дира", "Александра Иванова", "Лала Джагитян", "Анастасия Блинова", "Армина Нерсесян", "Мария Белых"]),
    ("мой близкий человек употребляет ПАВ/алкоголь", ["Анна Карманова", "Анастасия Дира", "Армина Нерсесян"]),
    ("у меня депрессия/диагностировано психическое расстройство врачом-психиатром", ["Юлия Курчанова", "Анастасия Блинова"]),  # 👈 НОВАЯ ТЕМА
]

# Все темы для "без разницы"
ANY_TOPICS = ONLINE_TOPICS  # остается как есть

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога - первый вопрос"""
    user_id = update.effective_user.id
    print(f"✅ Команда /start получена от пользователя {user_id}")
    
    # Полностью очищаем данные пользователя
    if user_id in user_data:
        del user_data[user_id]
    
    # Очищаем данные в контексте
    if context.user_data:
        context.user_data.clear()
    
    # СБРАСЫВАЕМ СОСТОЯНИЕ ДИАЛОГА
    conversation_key = (user_id, update.effective_chat.id)
    if conv_handler and conversation_key in conv_handler._conversations:
        del conv_handler._conversations[conversation_key]
    
    keyboard = [
        [InlineKeyboardButton("✅ Да", callback_data="individual_yes")],
        [InlineKeyboardButton("❌ Нет", callback_data="individual_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Определяем, откуда пришел вызов
    if update.message:
        # Обычный /start
        await update.message.reply_text(
            "👋 Здравствуйте! Я помогу подобрать специалиста.\n\n"
            "Вы ищете специалиста для своей индивидуальной работы?",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        # Если вызвано из callback (например, после нажатия кнопки)
        await update.callback_query.message.reply_text(
            "👋 Здравствуйте! Я помогу подобрать специалиста.\n\n"
            "Вы ищете специалиста для своей индивидуальной работы?",
            reply_markup=reply_markup
        )
    
    return INDIVIDUAL_CHOICE

async def individual_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора: для себя или нет"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "individual_yes":
        # Для себя - проверяем возраст
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="age_over_18")],
            [InlineKeyboardButton("❌ Нет", callback_data="age_under_18")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Вам больше 18 лет?",
            reply_markup=reply_markup
        )
        return AGE_CHECK
    
    else:
        # Не для себя - варианты
        keyboard = [
            [InlineKeyboardButton("👶 Для ребенка", callback_data="for_child")],
            [InlineKeyboardButton("💑 В паре", callback_data="for_pair")],
            [InlineKeyboardButton("👥 В группу", callback_data="for_group")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Что вы ищете?",
            reply_markup=reply_markup
        )
        return CHILD_CHOICE

async def age_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка возраста 18+"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "age_over_18":
        # Больше 18 - спрашиваем формат
        keyboard = [
            [InlineKeyboardButton("🏠 Очно (Москва)", callback_data="format_offline")],
            [InlineKeyboardButton("💻 Онлайн", callback_data="format_online")],
            [InlineKeyboardButton("🔄 Без разницы", callback_data="format_any")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Вы хотите работать очно или онлайн?",
            reply_markup=reply_markup
        )
        return FORMAT_CHOICE
    
    else:
        # Меньше 18 - спрашиваем про 15
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="age_15_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="age_15_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Вам больше 15 лет?",
            reply_markup=reply_markup
        )
        return AGE_15_CHECK

async def age_15_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка возраста 15+"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "age_15_yes":
        # Показываем специалистов (Мария Белых, Юлия Курчанова)
        await show_specialists_by_names(
            update, context, 
            ["Мария Белых", "Юлия Курчанова"],
            "Для вас подходят специалисты:"
        )
        return ConversationHandler.END
    else:
        # Меньше 15 - отказ
        await query.edit_message_text(
            "К сожалению, чтобы записаться на прием к психологу, нужно согласие вашего родителя. "
            "Пожалуйста, попросите его записать вас к психологу.\n\n"
            "Нажмите /start чтобы начать заново"
        )
        return ConversationHandler.END

async def child_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора для ребенка"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "for_child":
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="neuro_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="neuro_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Вам нужен нейропсихолог?",
            reply_markup=reply_markup
        )
        return NEURO_CHOICE
    
    elif query.data == "for_pair":
        # Специалисты для пар
        await show_specialists_by_names(
            update, context,
            ["Лала Джагитян", "Армина Нерсесян"],
            "Специалисты для пар:"
        )
        return ConversationHandler.END
    
    elif query.data == "for_group":
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="group_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="group_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Вы хотите попасть в группу?",
            reply_markup=reply_markup
        )
        return GROUP_CHOICE

async def neuro_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора нейропсихолога"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "neuro_yes":
        # Нужен нейропсихолог - только Мария Белых
        await show_specialists_by_names(
            update, context,
            ["Мария Белых"],
            "Нейропсихолог:"
        )
    else:
        # Не нужен нейропсихолог - Мария Белых, Юлия Курчанова
        await show_specialists_by_names(
            update, context,
            ["Мария Белых", "Юлия Курчанова"],
            "Специалисты для ребенка:"
        )
    return ConversationHandler.END

async def group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора группы"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "group_yes":
        await query.edit_message_text(
            "Запись на группы доступна через @vmartelife\n\n"
            "Нажмите /start чтобы начать заново"
        )
    else:
        await query.edit_message_text(
            "Я не понял, что вам нужно. Вернитесь к началу.\n\n"
            "Нажмите /start чтобы начать заново"
        )
    return ConversationHandler.END

async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора формата работы"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['format'] = query.data
    
    # Показываем темы в зависимости от формата
    keyboard = []
    
    if query.data == "format_offline":
        topics = OFFLINE_TOPICS
    elif query.data == "format_online":
        topics = ONLINE_TOPICS
    else:  # format_any
        topics = ANY_TOPICS
    
    for i, (topic, _) in enumerate(topics):
        keyboard.append([InlineKeyboardButton(topic, callback_data=f"topic_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Выберите 1 основную тему, с которой хотите работать:",
        reply_markup=reply_markup
    )
    return TOPIC_CHOICE

async def topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора темы"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    
    format_choice = user_data[user_id].get('format', 'format_online')
    
    # Определяем список тем по формату
    if format_choice == "format_offline":
        topics = OFFLINE_TOPICS
    elif format_choice == "format_online":
        topics = ONLINE_TOPICS
    else:
        topics = ANY_TOPICS
    
    # Получаем индекс темы из callback
    topic_index = int(query.data.replace("topic_", ""))
    selected_topic, specialists_names = topics[topic_index]
    
    # Показываем специалистов
    await show_specialists_by_names(
        update, context,
        specialists_names,
        f"По теме '{selected_topic}' вам подходят:"
    )
    return ConversationHandler.END

async def show_specialists_by_names(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   names: list, header: str):
    """Показывает специалистов по списку имен с кнопками на каждого"""
    query = update.callback_query
    
    # Словарь ссылок на страницы специалистов
    specialist_links = {
        "Анастасия Дира": "https://vmarte.life/anastasiyadira",
        "Александра Иванова": "https://vmarte.life/aleksandraivanova",
        "Мария Белых": "https://vmarte.life/belyhmaria",
        "Екатерина Бычкова": "https://vmarte.life/bychkovaekaterina",
        "Армина Нерсесян": "https://vmarte.life/arminanarsesyan",
        "Юлия Курчанова": "https://vmarte.life/kurshanovayuliya",
        "Лала Джагитян": "https://vmarte.life/laladzhagityan",
        "Вилена Васильева": "https://vmarte.life/vasilevavilena",
        "Анастасия Блинова": "https://vmarte.life/blinovaanastasiya",
        "Анна Карманова": "https://vmarte.life/karmanovaanna"
    }
    
    response = f"{header}\n\n"
    keyboard = []
    
    for name in names:
        if name in SPECIALISTS:
            data = SPECIALISTS[name]
            
            # Информация о специалисте
            response += f"👤 {name}\n"
            response += f"📝 {data['description']}\n"
            if data.get('experience'):
                response += f"⏳ {data['experience']}\n"
            if data.get('specialization'):
                response += f"🔹 {data['specialization']}\n"
            response += f"💰 Стоимость: {data['price']} руб"
            if data.get('price_pair'):
                response += f" | Для пары: {data['price_pair']} руб"
            if data.get('price_hypnosis'):
                response += f" | Гипноз: {data['price_hypnosis']} руб"
            response += "\n\n"
            
            # Кнопка для этого специалиста
            if name in specialist_links:
                keyboard.append([InlineKeyboardButton(f"📌 Подробнее о {name}", url=specialist_links[name])])
            
            response += "-" * 30 + "\n\n"
    
    # Добавляем информацию о промокоде
    response += "🎁 ДАРИМ ПРОМОКОД!\n"
    response += "🔥 МАРТhelp - скидка 20% на первую сессию с любым специалистом центра!\n\n"
    response += "✨ Больше бонусов и полезного в канале: @martcentrhappy\n\n"
    response += "📌 Как получить скидку:\n"
    response += "1. Нажмите кнопку «Записаться» ниже\n"
    response += "2. В графе «Промокод» укажите специалиста и промокод\n"
    response += "3. Пример: МАРТhelp Александра Иванова\n"
    
    # Добавляем общую кнопку записи
    keyboard.append([InlineKeyboardButton("📅 Записаться со скидкой 20%", url=config.BOOKING_URL)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    response += "\n\n❓ Нажмите /start чтобы начать заново"
    
    await query.edit_message_text(response, reply_markup=reply_markup)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    await update.message.reply_text(
        "До свидания! Если захотите продолжить - нажмите /start"
    )
    return ConversationHandler.END

def main():
    """Запуск бота"""
    print("🚀 Запуск бота...")
    
    # Создаем приложение
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Создаем ConversationHandler
    global conv_handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            INDIVIDUAL_CHOICE: [CallbackQueryHandler(individual_choice_callback, pattern="^individual_")],
            AGE_CHECK: [CallbackQueryHandler(age_callback, pattern="^age_")],
            AGE_15_CHECK: [CallbackQueryHandler(age_15_callback, pattern="^age_15_")],
            FORMAT_CHOICE: [CallbackQueryHandler(format_callback, pattern="^format_")],
            TOPIC_CHOICE: [CallbackQueryHandler(topic_callback, pattern="^topic_")],
            CHILD_CHOICE: [CallbackQueryHandler(child_choice_callback, pattern="^for_")],
            NEURO_CHOICE: [CallbackQueryHandler(neuro_callback, pattern="^neuro_")],
            GROUP_CHOICE: [CallbackQueryHandler(group_callback, pattern="^group_")],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start)  # 👈 Теперь /start работает в любой момент
        ],
        per_message=False,
        name="psychologist_bot"
    )
    
    application.add_handler(conv_handler)
    
    print("✅ Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
