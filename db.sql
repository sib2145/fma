BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "dialog_options" (
	"id"	INTEGER,
	"dialog_id"	INTEGER NOT NULL,
	"condition"	TEXT,
	"weight"	INTEGER,
	"text_id"	INTEGER NOT NULL,
	"next_dialog_id"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "dialogs" (
	"id"	INTEGER,
	"text_id"	INTEGER NOT NULL,
	"image"	TEXT,
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
COMMIT;
