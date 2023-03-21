from django.db import models


class Reminder(models.Model):
    name = models.CharField(max_length=50)
    day = models.SmallIntegerField()
    month = models.SmallIntegerField()
    year = models.SmallIntegerField()
    phone_number = models.ForeignKey('User', on_delete=models.CASCADE)


class User(models.Model):
    phone_number = models.IntegerField(primary_key=True)
    notification_weeks = models.SmallIntegerField(default=2)
    notification_time = models.SmallIntegerField(default=8)
    birthdays_notified = models.SmallIntegerField(default=0)
