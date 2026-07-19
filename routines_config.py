import models

# Whenever you want to change your base schedule, just edit this list!
DEFAULT_ROUTINES = [
    # WEEKDAYS (Mon - Fri)
    {"name": "Wakeup", "time": "04:00", "freq": models.FrequencyEnum.weekday},
    {"name": "Study for personal development", "time": "04:00", "freq": models.FrequencyEnum.weekday},
    {"name": "Workout", "time": "06:00", "freq": models.FrequencyEnum.weekday},
    {"name": "Cooking", "time": "07:30", "freq": models.FrequencyEnum.weekday},
    {"name": "Prepare for office & Breakfast", "time": "09:30", "freq": models.FrequencyEnum.weekday},
    {"name": "Travel to office", "time": "10:30", "freq": models.FrequencyEnum.weekday},
    {"name": "Work", "time": "11:30", "freq": models.FrequencyEnum.weekday},
    {"name": "Have a dinner", "time": "20:00", "freq": models.FrequencyEnum.weekday},
    {"name": "Dishwashing", "time": "20:30", "freq": models.FrequencyEnum.weekday},
    {"name": "Rewind day, give feedback, talk with parents/Meena, prepare for tomorrow", "time": "21:00",
     "freq": models.FrequencyEnum.weekday},
    {"name": "Set sleep alarm & go to bed", "time": "21:30", "freq": models.FrequencyEnum.weekday},

    # WEEKENDS
    {"name": "Wash dress, clean house, study", "time": "10:00", "freq": models.FrequencyEnum.weekend},
    {"name": "Watch a movie and chill", "time": "14:00", "freq": models.FrequencyEnum.weekend},

    # MONTHLY - 1st
    {"name": "Plan financial goals", "time": "10:00", "freq": models.FrequencyEnum.monthly_1st},
    {"name": "Pay rent & electricity bill", "time": "10:00", "freq": models.FrequencyEnum.monthly_1st},
    {"name": "Pay broadband bill", "time": "10:00", "freq": models.FrequencyEnum.monthly_1st},
    {"name": "Pay investment amount", "time": "10:00", "freq": models.FrequencyEnum.monthly_1st},
    {"name": "Pay insurance", "time": "10:00", "freq": models.FrequencyEnum.monthly_1st},
    {"name": "Pay for retirement", "time": "10:00", "freq": models.FrequencyEnum.monthly_1st},
    {"name": "Pay credit card payment", "time": "10:00", "freq": models.FrequencyEnum.monthly_1st},
    {"name": "Allocate 30K for savings", "time": "10:00", "freq": models.FrequencyEnum.monthly_1st},
    {"name": "Allocate amount for food/grocery", "time": "10:00", "freq": models.FrequencyEnum.monthly_1st},

    # MONTHLY - 6th
    {"name": "Have you paid HDFC Diners Club credit card?", "time": "10:00", "freq": models.FrequencyEnum.monthly_6th}
]