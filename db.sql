BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "condition_operators" (
	"id"	INTEGER NOT NULL,
	"text_id"	INTEGER NOT NULL,
	"weight"	INTEGER NOT NULL DEFAULT 1,
	"comment"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "condition_type_operators" (
	"condition_type_id"	INTEGER NOT NULL,
	"operator_type_id"	INTEGER NOT NULL,
	PRIMARY KEY("condition_type_id","operator_type_id"),
	CONSTRAINT "ctop_condition_type_id" FOREIGN KEY("condition_type_id") REFERENCES "condition_types"("id"),
	CONSTRAINT "ctop_operator_type_id" FOREIGN KEY("operator_type_id") REFERENCES "condition_operators"("id")
);
CREATE TABLE IF NOT EXISTS "condition_types" (
	"id"	INTEGER NOT NULL,
	"text_id"	INTEGER NOT NULL,
	"weight"	INTEGER NOT NULL DEFAULT 0,
	"comment"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "conditions" (
	"id"	INTEGER NOT NULL,
	"dialog_id"	INTEGER,
	"option_id"	INTEGER,
	"condition_type_id"	INTEGER NOT NULL,
	"operator_type_id"	INTEGER,
	"weight"	INTEGER NOT NULL DEFAULT 1,
	"value1"	TEXT,
	"value2"	TEXT,
	CONSTRAINT "cond_dial_id_weight" UNIQUE("dialog_id","weight"),
	PRIMARY KEY("id" AUTOINCREMENT),
	CONSTRAINT "cond_opt_id_weigth" UNIQUE("option_id","weight"),
	CONSTRAINT "cond_cond_type_id" FOREIGN KEY("condition_type_id") REFERENCES "condition_types"("id"),
	CONSTRAINT "cond_dialog_id" FOREIGN KEY("dialog_id") REFERENCES "dialogs"("id"),
	CONSTRAINT "cond_oper_type_id" FOREIGN KEY("operator_type_id") REFERENCES "condition_operators"("id"),
	CONSTRAINT "cond_option_id" FOREIGN KEY("option_id") REFERENCES "dialog_options"("id")
);
CREATE TABLE IF NOT EXISTS "dialog_options" (
	"id"	INTEGER,
	"dialog_id"	INTEGER NOT NULL,
	"condition"	TEXT,
	"weight"	INTEGER,
	"text_id"	INTEGER NOT NULL,
	"next_dialog_id"	INTEGER,
	"save_choice"	INTEGER NOT NULL DEFAULT 1,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "dialogs" (
	"id"	INTEGER,
	"text_id"	INTEGER NOT NULL,
	"image"	TEXT,
	"next_dialog_id"	INTEGER,
	"save_choice"	INTEGER NOT NULL DEFAULT 1,
	"multiselect"	INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "locales" (
	"id"	INTEGER NOT NULL,
	"code"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "player_dialog_choices" (
	"id"	INTEGER,
	"player_id"	INTEGER NOT NULL,
	"dialog_id"	INTEGER NOT NULL,
	"option_id"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "players" (
	"id"	INTEGER NOT NULL,
	"telegram_id"	INTEGER NOT NULL UNIQUE,
	"locale_id"	INTEGER NOT NULL DEFAULT 1,
	"join_date"	DATETIME,
	"last_active"	DATETIME,
	"current_dialog_id"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	CONSTRAINT "fk_current_dialog_id" FOREIGN KEY("current_dialog_id") REFERENCES "dialogs"("id")
);
CREATE TABLE IF NOT EXISTS "texts" (
	"id"	INTEGER NOT NULL,
	"locale_id"	INTEGER NOT NULL DEFAULT 1,
	"text"	TEXT,
	PRIMARY KEY("id","locale_id")
);
INSERT INTO "condition_operators" VALUES (1,24,1,'=');
INSERT INTO "condition_operators" VALUES (2,25,2,'<>');
INSERT INTO "condition_operators" VALUES (3,26,3,'<=');
INSERT INTO "condition_operators" VALUES (4,27,4,'>=');
INSERT INTO "condition_type_operators" VALUES (3,1);
INSERT INTO "condition_type_operators" VALUES (3,2);
INSERT INTO "condition_type_operators" VALUES (4,1);
INSERT INTO "condition_type_operators" VALUES (4,2);
INSERT INTO "condition_types" VALUES (1,16,1,'group begin');
INSERT INTO "condition_types" VALUES (2,17,2,'group end');
INSERT INTO "condition_types" VALUES (3,18,3,'option <x> selected in dialog <y>');
INSERT INTO "condition_types" VALUES (4,19,4,'dialog <x> completed');
INSERT INTO "condition_types" VALUES (5,21,5,'or');
INSERT INTO "condition_types" VALUES (6,22,6,'function result');
INSERT INTO "condition_types" VALUES (7,23,7,'player flag <x> = <y>');
INSERT INTO "conditions" VALUES (1,2,NULL,4,1,1,'1',NULL);
INSERT INTO "dialog_options" VALUES (49,1,NULL,1,5007,2,1);
INSERT INTO "dialog_options" VALUES (50,2,NULL,1,5009,NULL,1);
INSERT INTO "dialog_options" VALUES (52,2,NULL,2,5011,NULL,1);
INSERT INTO "dialog_options" VALUES (53,2,NULL,3,5012,NULL,1);
INSERT INTO "dialog_options" VALUES (54,2,NULL,4,5013,NULL,1);
INSERT INTO "dialog_options" VALUES (55,2,NULL,5,5014,3,0);
INSERT INTO "dialog_options" VALUES (56,4,NULL,1,5017,1,1);
INSERT INTO "dialog_options" VALUES (57,3,NULL,1,5018,2,1);
INSERT INTO "dialogs" VALUES (1,5006,NULL,NULL,1,0);
INSERT INTO "dialogs" VALUES (2,5008,NULL,4,1,1);
INSERT INTO "dialogs" VALUES (3,5015,NULL,2,0,0);
INSERT INTO "dialogs" VALUES (4,5016,NULL,NULL,1,0);
INSERT INTO "locales" VALUES (1,'ru');
INSERT INTO "player_dialog_choices" VALUES (50,9,2,50);
INSERT INTO "player_dialog_choices" VALUES (53,9,2,52);
INSERT INTO "player_dialog_choices" VALUES (54,9,4,56);
INSERT INTO "player_dialog_choices" VALUES (55,9,1,49);
INSERT INTO "players" VALUES (9,6136061550,1,'2026-09-25 09:01:27.257004',NULL,4);
INSERT INTO "texts" VALUES (5000,1,'Привет тебе в игре 🔸️ <b>Fantasy Market</b> 🔸️! 
Создай свой магазин в мире фэнтези и управляй им!

Начни с алхимической лавки:

🧪️ - Смешивай зелья;
👩‍💼 - Нанимай и вербуй сильный персонал;
💎 - Продавай предметы бродячим искателям приключений или другим игрокам;
🏆 - Повышай престиж лавки и её узнаваемость.


⬇️ Попробуй сразу или почитай что интересного в кнопках ниже!');
INSERT INTO "texts" VALUES (5001,1,'Привет тебе в игре 🔸️ <b>Fantasy Market</b> 🔸️! 
Создай свой магазин в мире фэнтези и управляй им!

Начни с алхимической лавки:

🧪️ - Смешивай зелья;
👩‍💼 - Нанимай и вербуй сильный персонал;
💎 - Продавай предметы бродячим искателям приключений или другим игрокам;
🏆 - Повышай престиж лавки и её узнаваемость.

<b>Что тут интересного:</b>

🔹 Искатели приключений независимы и могут иногда захаживать в твою лавку продать травы и купить зелья;
🔹 Ты можешь нанять искателей приключений на поиски и сбор трав и реагентов;
🔹 Разные локальные и глобальные мировые события влияют на доступность и ценность трав, на востребованность и цену зелий;
🔹 Искатели приключений попадаются разной редкости, рас и типов;
🔹 Работники магазина со временем повышают уровень и меняют типа на более сильный. Более сильный - более эффективный;
🔹 Давай задания работникам и авантюристам, а потом насладжася результатом;
🔹 Лавка растет, развивается, приносит прибыль, открывает новые рецепты и возможности;
🔹 Новые рецепты для зелий можно открывать, а можно своровать у соседей, найти в странствиях авантюристов или неожиданно получить от клиента за деньги;
🔹 Игра не сильно отвлекает и напрягает, но позволяет скратить твоё время при скуке;
🔹 Никаких приложений, установок, тормозов - игра только через бот в этом диалоге.');
INSERT INTO "texts" VALUES (1,1,'🔥 Что тут интересного?');
INSERT INTO "texts" VALUES (2,1,'❇️ Создать свой магазин в мире');
INSERT INTO "texts" VALUES (3,1,'🏆 Рейтинг игроков');
INSERT INTO "texts" VALUES (4,1,'📊 Статистика мира');
INSERT INTO "texts" VALUES (5002,1,'Мы запомним ваш <b>ID</b> в <b>Telegram</b>(номер вашего аккаунта, не номер телефона), чтобы выдавать вам доступ к механикам в игре под вашим управлением.

Никакие другие данные, включая имя пользователя или телефон мы не запрашиваем и не храним, а связь с игровыми механиками осуществляем исключительно по <b>ID</b>. Если где-то используем ваше имя, оно подставляется ботом автоматически в диалогах в Telegram и у нас не хранится.

Мы считаем хорошим тоном уведомить вас об этом сразу, перед нашим дальнейшим взаимодействием.

Продолжая, вы подтверждаете, что персональными данными эти данные не являются, а также полностью соглашаетесь с правилами нашего проекта.');
INSERT INTO "texts" VALUES (5,1,'✅ Принять и продолжить');
INSERT INTO "texts" VALUES (6,1,'◀️️ Назад');
INSERT INTO "texts" VALUES (5003,1,'Здесь полный текст правил');
INSERT INTO "texts" VALUES (7,1,'📋️ Полный текст правил');
INSERT INTO "texts" VALUES (8,1,'✅ Продолжить');
INSERT INTO "texts" VALUES (9,1,'❇️ Войти в мир игры');
INSERT INTO "texts" VALUES (10,1,'⚒️ Админка');
INSERT INTO "texts" VALUES (11,1,'Редактор диалогов');
INSERT INTO "texts" VALUES (5004,1,'✨ Добро пожаловать в панель администратора! ✨

Выберите действие:');
INSERT INTO "texts" VALUES (5005,1,'✨ Редактор диалогов ✨

Выберите действие:');
INSERT INTO "texts" VALUES (12,1,'Добавить');
INSERT INTO "texts" VALUES (13,1,'Просмотр');
INSERT INTO "texts" VALUES (14,1,'Список диалогов');
INSERT INTO "texts" VALUES (15,1,'Поиск');
INSERT INTO "texts" VALUES (5006,1,'Передвигаясь по большой пыльной дороге, ты периодически встречаешь людей, движущихся в обратном направлении. 

Их лица тебе не знакомы и ты уже успеваешь заскучать, как кто то сзади окликает тебя...');
INSERT INTO "texts" VALUES (5007,1,'Продолжить');
INSERT INTO "texts" VALUES (16,1,'Начало группы условий');
INSERT INTO "texts" VALUES (17,1,'Конец группы условий');
INSERT INTO "texts" VALUES (18,1,'Кнопка Х нажата в диалоге У');
INSERT INTO "texts" VALUES (19,1,'Диалог Х завершен');
INSERT INTO "texts" VALUES (21,1,'Логическое ИЛИ');
INSERT INTO "texts" VALUES (22,1,'Результат функции');
INSERT INTO "texts" VALUES (23,1,'Значение флага у игрока');
INSERT INTO "texts" VALUES (24,1,'= Равно');
INSERT INTO "texts" VALUES (25,1,'<> Не равно');
INSERT INTO "texts" VALUES (26,1,'<= Меньше или равно');
INSERT INTO "texts" VALUES (27,1,'=> Больше или равно');
INSERT INTO "texts" VALUES (5008,1,'Привет, мой старый знакомый!

Мы давно не виделись. Несколько лет прошло с нашей последней встречи.

Кем ты был эти последние годы?');
INSERT INTO "texts" VALUES (5009,1,'Странствующим торговцем');
INSERT INTO "texts" VALUES (5010,1,'Продолжить');
INSERT INTO "texts" VALUES (5011,1,'Алхимиком в лавке');
INSERT INTO "texts" VALUES (5012,1,'Ученым');
INSERT INTO "texts" VALUES (5013,1,'Управляющим гостиницы');
INSERT INTO "texts" VALUES (5014,1,'Подробнее о выборах');
INSERT INTO "texts" VALUES (5015,1,'- Странствующим торговцем (цены лучше на 5%)
- Алхимиком в лавке (шанс создать более редкое зелье +5%)
- Ученым (скорость исследований рецептов и пр. +5%)
- Управляющим гостиницы (+5% шанс найти более редкий персонал для найма)');
INSERT INTO "texts" VALUES (5016,1,'Что ж. Эти годы я тоже не сидел на месте. 

А прямо сейчас объезжаю деревни и города наживать добра и прощупывать почву.

Многие деревни богаты ресурсами, а местные готовы продавать их по хорошей цене. В городах всё дороже, но там выгоднее продавать конечный продукт.

В какое место ты направляешься?');
INSERT INTO "texts" VALUES (5017,1,'Вернуться');
INSERT INTO "texts" VALUES (5018,1,'Назад к выбору');
CREATE UNIQUE INDEX IF NOT EXISTS "idx_player_dialog_choice_unique" ON "player_dialog_choices" (
	"player_id",
	"dialog_id",
	"option_id"
);
COMMIT;
