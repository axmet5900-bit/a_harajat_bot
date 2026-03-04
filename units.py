import re
import io
import json
import base64
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import requests
from gtts import gTTS

def extract_amount(text):
    """Matndan summani ajratish"""
    numbers = re.findall(r'\d+', text)
    return int(numbers[0]) if numbers else None

def extract_person(text):
    """Matndan odam ismini ajratish"""
    words = text.split()
    for i, word in enumerate(words):
        if word.lower() == "qarz" and i > 0:
            return words[i-1]
    return "Do'st"

def create_expense_chart(data, title="Xarajatlar"):
    """Pie chart yaratish"""
    plt.figure(figsize=(10, 8))
    categories = list(data.keys())
    amounts = list(data.values())
    
    # Kichik kategoriyalarni birlashtirish
    if len(categories) > 5:
        main_cats = categories[:5]
        main_amts = amounts[:5]
        other_sum = sum(amounts[5:])
        if other_sum > 0:
            main_cats.append("Boshqa")
            main_amts.append(other_sum)
    else:
        main_cats = categories
        main_amts = amounts
    
    colors = plt.cm.Set3(range(len(main_cats)))
    plt.pie(main_amts, labels=main_cats, autopct='%1.1f%%', colors=colors)
    plt.title(f"{title}\nJami: {sum(amounts):,.0f} so'm")
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def create_trend_chart(dates, amounts):
    """Trend chizig'i yaratish"""
    plt.figure(figsize=(12, 6))
    plt.plot(dates, amounts, marker='o', linewidth=2)
    plt.title('Kunlik xarajatlar trendi')
    plt.xlabel('Sana')
    plt.ylabel('Summa')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf

def export_to_excel(transactions, filename):
    """Excel fayl yaratish"""
    df = pd.DataFrame(transactions, columns=['ID', 'Summa', 'Kategoriya', 'Turi', 'Izoh', 'Sana'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Xarajatlar')
    output.seek(0)
    return output

def export_to_pdf(transactions, filename):
    """PDF fayl yaratish"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Xarajatlar hisoboti")
    
    c.setFont("Helvetica", 10)
    y = height - 100
    
    for i, t in enumerate(transactions[:20]):
        line = f"{t[5]}: {t[2]:,.0f} so'm - {t[3]} ({t[4]})"
        c.drawString(50, y, line)
        y -= 20
        
        if y < 50:
            c.showPage()
            y = height - 50
    
    c.save()
    buffer.seek(0)
    return buffer

def text_to_speech(text, lang='uz'):
    """Matnni ovozga aylantirish"""
    tts = gTTS(text=text, lang=lang, slow=False)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

def get_currency_rates():
    """Valyuta kurslarini olish"""
    try:
        response = requests.get('https://cbu.uz/uz/arkhiv-kursov-valyut/json/')
        if response.status_code == 200:
            data = response.json()
            rates = {}
            for item in data[:5]:
                rates[item['Ccy']] = float(item['Rate'])
            return rates
    except:
        return {'USD': 12500, 'EUR': 13500, 'RUB': 140}
    return {}

def analyze_spending_habits(transactions):
    """Xarajat odatlarini tahlil qilish"""
    if not transactions:
        return {}
    
    habits = {}
    
    # Eng ko'p xarajat kategoriyasi
    categories = {}
    for t in transactions:
        cat = t[3]  # category
        amount = t[2]  # amount
        categories[cat] = categories.get(cat, 0) + amount
    
    top_cat = max(categories, key=categories.get)
    habits['top_category'] = top_cat
    habits['top_category_amount'] = categories[top_cat]
    
    # O'rtacha kunlik xarajat
    dates = {}
    for t in transactions:
        date = t[6][:10]  # date
        dates[date] = dates.get(date, 0) + t[2]
    
    avg_daily = sum(dates.values()) / len(dates) if dates else 0
    habits['avg_daily'] = avg_daily
    
    # Hafta kuni tahlili
    weekdays = [0]*7
    for t in transactions:
        date = datetime.strptime(t[6][:10], '%Y-%m-%d')
        weekdays[date.weekday()] += t[2]
    
    max_weekday = max(range(7), key=lambda x: weekdays[x])
    weekday_names = ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 
                     'Juma', 'Shanba', 'Yakshanba']
    habits['max_spending_day'] = weekday_names[max_weekday]
    
    return habits

def generate_pin_hash(pin):
    """PIN kodni xeshlash"""
    import hashlib
    return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin(pin, pin_hash):
    """PIN kodni tekshirish"""
    import hashlib
    return hashlib.sha256(pin.encode()).hexdigest() == pin_hash
