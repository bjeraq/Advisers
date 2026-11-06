---
name: screen-refresh
description: التحديث الأسبوعي للفحص الشرعي — يعيد فحص السوق الأمريكي بالنسب المالية ويحدّث data/universe_us.csv ويدفعه للفرع. Use when the weekly sharia-screen refresh session fires, or when the user asks to refresh the halal universe.
---

# تحديث الفحص الشرعي الأسبوعي

الهدف: إعادة الفحص الشرعي الكامل على السوق الأمريكي وحفظ القائمة المحدثة
في المستودع حتى يعتمد عليها راصد الصباح والمجلس طول الأسبوع.

## الخطوات

1. من داخل مجلد المستودع، اسحب البيانات وأعد الفحص:

   ```bash
   python3 -m advisers.quotes --out <مسار-السكراتش-باد>/scan.json
   python3 -m advisers.screener --rows <مسار-السكراتش-باد>/scan.json --out data/universe_us.csv
   ```

   احتفظ بسطر الملخص اللي يطبعه الفحص (المجموع/متوافق/غير متوافق/مراجعة).

2. شغّل الاختبارات للتأكد أن ما انكسر شي:

   ```bash
   python3 -m unittest discover -s tests -t .
   ```

3. اعمل commit لملف `data/universe_us.csv` وادفعه للفرع
   `claude/vibrant-mayer-mu1ifg` برسالة مثل:
   `Weekly sharia universe refresh: <سطر الملخص>`
   (أضف سطور التوثيق التي تحددها تعليمات نظامك إن وُجدت.)

4. لو `TELEGRAM_BOT_TOKEN` موجود ومعرف القروب مجهز، أرسل سطر ملخص للقروب:

   ```bash
   python3 -m advisers.telegram --send "🕌 تحدثت قائمة الأسهم الشرعية: <سطر الملخص>"
   ```

   لو التوكن غير مجهز، تجاوز هذه الخطوة بصمت.

5. افحص `config/market_holidays_us.json`: إذا أبعد تاريخ فيه يبعد أقل من
   ٦٠ يوم، أضف تنبيهاً في رسالة التيليجرام وردك النهائي أن قائمة العطل
   تحتاج تمديداً لسنة جديدة (حدّثها بنفسك من تقويم بورصة نيويورك المعلن
   إذا كنت متأكداً من التواريخ، وإلا اطلبها من المستخدم).

## قواعد

- لا أوامر تداول إطلاقاً.
- التعديل المسموح: `data/universe_us.csv` و(عند الحاجة) `config/market_holidays_us.json`.
- ردك النهائي سطر أو سطران بالعربي مع أرقام الملخص.
