#!/bin/bash
# Активируем виртуальное окружение и запускаем планировщик
source /Users/amanturerkinov/Desktop/flowers/venv/bin/activate
cd /Users/amanturerkinov/Desktop/flowers
python scheduler.py >> scheduler.log 2>&1


