<div dir="rtl">

# Font2TTF

תוכנה קלה ואופליין להמרת קבצי פונט ל-TTF, עשרות או מאות קבצים בבת אחת.
בלי אינטרנט, בלי הגדרות מיותרות: מוסיפים קבצים, לוחצים, ומקבלים.

## מה היא עושה

- ממירה **WOFF / WOFF2 / OTF / TTF** לפורמט המתאים, בקבוצות.
- **מזהה אוטומטית** את סוג הפונט לפי התוכן שלו ולא לפי הסיומת:
  - פונט עם קווי מתאר TrueType ← נשמר כ-`.ttf`.
  - פונט עם קווי מתאר OpenType (CFF) ← נשמר כ-`.otf` **ללא אובדן איכות**. רק עטיפת ה-WOFF/WOFF2 מוסרת, והפונט עצמו נשאר זהה.
- עובדת **במקביל על כל ליבות המעבד**, עם סרגל התקדמות.
- קובץ פגום אחד לא עוצר את השאר, ובסוף מוצג דוח של מה שנכשל.
- תומכת בהוספת תיקיות שלמות (כולל תתי-תיקיות) ובגרירת קבצים לחלון.

## למה OTF לא הופך ל-TTF

ל-OTF עקומות קוביות, ול-TTF רק ריבועיות. המרה ביניהם היא תמיד קירוב ולא העתק מדויק, וגם ה-hinting המקורי אובד. לכן התוכנה משאירה פונטים כאלה כ-OTF, שהוא פורמט נתמך כמעט בכל מקום.

## הרצה מהקוד

נדרש Python 3.9 ומעלה.

```
pip install fonttools brotli tkinterdnd2
python font2ttf.py
```

`tkinterdnd2` אופציונלי. בלעדיו הכול עובד, רק בלי גרירת קבצים לחלון.

## שימוש

1. לוחצים **הוסף קבצים** או **הוסף תיקייה**, או גוררים קבצים לחלון.
2. (אופציונלי) בוחרים תיקיית פלט. אם לא, ייווצר תת-תיקייה בשם `TTF` ליד הקובץ הראשון.
3. לוחצים **המר ל-TTF**.
4. בסיום מוצג סיכום, למשל `TTF: 62 | OTF (ללא אובדן): 38`.

טיפ: מקש `Delete` מסיר פריטים מסומנים מהרשימה.

## בניית EXE

### מקומית

```
pip install fonttools brotli tkinterdnd2 pyinstaller
pyinstaller --onefile --noconsole --collect-all tkinterdnd2 font2ttf.py
```

הקובץ המוכן יופיע בתיקייה `dist`.

### אוטומטית עם GitHub Actions

מוסיפים את הקובץ `.github/workflows/build.yml`:

```yaml
name: Build EXE

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install fonttools brotli tkinterdnd2 pyinstaller

      - name: Build EXE
        run: pyinstaller --onefile --noconsole --collect-all tkinterdnd2 font2ttf.py

      - uses: actions/upload-artifact@v4
        with:
          name: font2ttf
          path: dist/font2ttf.exe
```

אחרי כל push ל-`main` ייבנה EXE חדש. מורידים אותו מלשונית **Actions** ← הריצה האחרונה ← **Artifacts**.

## הערות

- בהרצה ראשונה של ה-EXE, Windows SmartScreen עלול להזהיר ממפרסם לא מוכר. זה קורה לכל EXE שנבנה ב-PyInstaller. בוחרים "מידע נוסף" ← "הפעל בכל זאת".
- גודל ה-EXE כמה עשרות MB, וזה תקין.
- קובץ שכבר נמצא בפורמט הסופי שלו ובאותה תיקיית פלט לא נדרס, והתוכנה מדלגת עליו.

## תלויות

- [fontTools](https://github.com/fonttools/fonttools): קריאה וכתיבה של פונטים
- [brotli](https://github.com/google/brotli): פענוח WOFF2
- [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2): גרירת קבצים (אופציונלי)

</div>
