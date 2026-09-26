@echo off
echo Компиляция MetadataBot v2.0...
echo Пожалуйста, подождите.

pip install pyinstaller

pyinstaller --noconfirm --onedir --windowed --name "MetadataBot" app.py

echo.
echo Копирование бинарных файлов...
copy /Y ffmpeg.exe dist\MetadataBot\
copy /Y ffprobe.exe dist\MetadataBot\

echo.
echo Сборка завершена! Бот полностью собран в папке dist\MetadataBot\
pause
