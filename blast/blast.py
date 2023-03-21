from datetime import datetime, date, timedelta
import sqlite3
import os
import math
from twilio.rest import Client
from dotenv import load_dotenv
from dataclasses import dataclass
import argparse


@dataclass
class Reminder:
    name: str
    day: str
    month: str
    year: str


def day_delta(day1: date, day2: date) -> int:
    return (day1 - day2).days


def generate_single_reminder(reminder: Reminder, next_occurrence: date) -> str:
    day_of_the_week = next_occurrence.strftime("%a")
    days_left = day_delta(next_occurrence, date.today())
    name = reminder.name
    age = 0
    if reminder.year:
        age = math.floor((next_occurrence - datetime.strptime(
            f"{reminder.month:02}/{reminder.day:02}/{reminder.year}", '%m/%d/%Y').date()).days / 365)
        if not days_left:
            return f"{name} turns {age} today!"
        elif days_left == 1:
            return f"{name} turns {age} tomorrow!"
        elif days_left < 7:
            return f"{name} turns {age} this coming {day_of_the_week}"
        else:
            return f"{name} turns {age} on {reminder.month}/{reminder.day}"
    else:
        if not days_left:
            return f"{name}'s birthday is today"
        elif days_left == 1:
            return f"{name}'s birthday is tomorrow!"
        elif days_left < 7:
            return f"{name}'s birthday is this coming {day_of_the_week}"
        else:
            return f"{name}'s birthday is {reminder.month}/{reminder.day}"


def generate_message(reminders: list[Reminder], notification_weeks: int) -> str:
    # Find the date of the next occurrence (this year or next)
    today = date.today()
    next_occurrences = []
    for reminder in reminders:
        date_this_year = datetime.strptime(
            f"{reminder.month:02}/{reminder.day:02}/{today.strftime('%Y')}", '%m/%d/%Y').date()
        date_next_year = datetime.strptime(
            f"{reminder.month:02}/{reminder.day:02}/{int(today.strftime('%Y'))+1}", '%m/%d/%Y').date()
        if day_delta(date_this_year, today) < 0:
            next_occurrences.append(
                (reminder, date_next_year, day_delta(date_next_year, today)))
        else:
            next_occurrences.append(
                (reminder, date_this_year, day_delta(date_this_year, today)))

    relevant_next_occurrences = filter(lambda x: (
        day_delta(x[1], today) < (notification_weeks * 7)), next_occurrences)
    relevant_next_occurrences = sorted(
        relevant_next_occurrences, key=lambda x: x[2])

    reminder_messages = [generate_single_reminder(
        reminder, next_occurrence) for reminder, next_occurrence, _ in relevant_next_occurrences]

    return '\n'.join(reminder_messages)


def send_messages(messages: tuple[int, str], twilio_phone_num: str, twilio_auth_token: str, twilio_account_sid: str) -> None:
    client = Client(twilio_account_sid, twilio_auth_token)
    for phone_number, message in messages:
        client.messages.create(body=message,
                               from_=f"+{twilio_phone_num}",
                               to=f"+{phone_number}")
    return


def main(db_path: str, hour: int, dry_run: bool):
    # Query SQLite for user info and relevant reminders
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    reminders_res = cur.execute("""
    SELECT phone_number, name, day, month, year FROM reminders WHERE phone_number in (SELECT phone_number FROM users WHERE notification_time = ?);
    """, (hour,))
    reminders_list = reminders_res.fetchall()
    users_res = cur.execute("""
    SELECT phone_number, notification_weeks FROM users WHERE notification_time = ?
    """, (hour,))
    users = users_res.fetchall()
    cur.close()

    # Create dictionary for notification weeks
    notification_weeks = {}
    for user in users:
        notification_weeks[user[0]] = user[1]

    # Collate Reminders
    reminder_messages = {}
    for reminder in reminders_list:
        phone_number = reminder[0]
        if phone_number not in reminder_messages:
            reminder_messages[phone_number] = []
        reminder_messages[phone_number].append(
            Reminder(reminder[1], reminder[2], reminder[3], reminder[4]))

    messages = []
    for phone_number, reminders in reminder_messages.items():
        messages.append((phone_number, generate_message(
            reminders, notification_weeks[phone_number])))

    if not dry_run:
        send_messages(messages, os.getenv('TWILIO_PHONE_NUMBER'), os.getenv(
            'TWILIO_AUTH_TOKEN'), os.getenv('TWILIO_ACCOUNT_SID'))
    else:
        for number, message in messages:
            print(f"sending message:\n{message}\nto +{number}")
    return


if __name__ == '__main__':
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog='BirthdayBlast', description='Sends out texts to individuals to help people remember birthdays.')
    parser.add_argument(
        '--db_path', help='Path to the SQLite database to query')
    parser.add_argument('--hour', type=int, choices=range(0, 24),
                        help='What hour in the EST timezone this script is being run at.')
    parser.add_argument('--dry_run', action='store_true',
                        help='If true, instead of sending texts it will dump the intended messages to stdout.')
    args = parser.parse_args()
    main(args.db_path, args.hour, args.dry_run)