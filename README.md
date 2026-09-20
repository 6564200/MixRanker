# MixRanker

Flask-приложение, работающее на связке Gunicorn + Nginx.

## 1. Установка зависимостей

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-venv python3-pip nginx git ufw htop mc fail2ban unzip -y
```

## 2. Клонирование и подготовка

```bash
cd /var/www && sudo git clone https://github.com/6564200/MixRanker.git
sudo chown -R $USER:$USER MixRanker
cd MixRanker
```

Распаковка флагов:
```bash
cd /var/www/MixRanker/static/flags && unzip 4x3.zip
cd /var/www/MixRanker
```

## 3. Виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
```

## 4. Переменные окружения

Добавьте переменные в конец файла `~/.bashrc`:
```bash
nano ~/.bashrc
```

```bash
export SECRET_KEY="ваш_случайный_строковый_ключ"
export FLASK_APP=app.py
export FLASK_ENV=production
```

Примените изменения:
```bash
source ~/.bashrc
```

## 5. Первый безопасный запуск (Создание администратора)

Выполняется вручную для первичной инициализации базы данных и учетной записи:

```bash
# 1. Генерация ключа
python3 - - Обязательные переменные
export SECRET_KEY="сгенерированный_ключ"
export FLASK_CONFIG=production

# 3. Переменные для создания первого администратора
export BOOTSTRAP_ADMIN_USERNAME="admin"
export BOOTSTRAP_ADMIN_PASSWORD="сложный_пароль"

# 4. Запуск Gunicorn вручную
gunicorn --workers 3 --bind unix:/var/www/MixRanker/mixranker.sock wsgi:app
```

*После этого зайдите в интерфейс под созданной учетной записью, смените пароль и удалите временные переменные из сессии:*
```bash
unset BOOTSTRAP_ADMIN_USERNAME
unset BOOTSTRAP_ADMIN_PASSWORD
```

## 6. Настройка Systemd (Демонизация)

Создайте файл сервиса:
```bash
sudo nano /etc/systemd/system/mixranker.service
```

Конфигурация:
```ini
[Unit]
Description=Gunicorn instance to serve MixRanker Flask app
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/MixRanker
Environment="PATH=/var/www/MixRanker/venv/bin"
Environment="SECRET_KEY=ваш_секретный_ключ"
ExecStart=/var/www/MixRanker/venv/bin/gunicorn --workers 3 --bind unix:/var/www/MixRanker/mixranker.sock wsgi:app

[Install]
WantedBy=multi-user.target
```

Управление сервисом:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mixranker
sudo systemctl start mixranker
sudo systemctl status mixranker
```

## 7. Настройка Nginx

Создайте конфигурационный файл хоста:
```bash
sudo nano /etc/nginx/sites-available/mixranker
```
Генерация сертификата на сервере:
```bash
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/mixranker.key \
  -out /etc/nginx/ssl/mixranker.crt \
  -subj "/CN=mixranker.ru" \
  -addext "subjectAltName=DNS:mixranker.ru,DNS:www.mixranker.ru"
```
Конфигурация:
```nginx
server {
    # Говорим Nginx слушать оба порта
    listen 80;
    listen 443 ssl;
    
    server_name mixranker.ru www.mixranker.ru;

    # Пути к вашему самоподписанному сертификату (будут работать только при заходе через 443 порт)
    ssl_certificate /etc/nginx/ssl/mixranker.crt;
    ssl_certificate_key /etc/nginx/ssl/mixranker.key;

    # Настройки безопасности SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Проксирование на ваше приложение (работает для обоих портов)
    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/MixRanker/mixranker.sock;
    }

    # Статика (работает для обоих портов)
    location /static/ {
        alias /var/www/MixRanker/static/;
    }
}
```
Скачивание сертификата
```bash
cat /etc/nginx/ssl/mixranker.crt
```
Скопируйте весь текст. Создайте у себя на компьютере текстовый файл, вставьте туда текст и сохраните как mixranker.crt
Установить сертификат -> Текущий пользователь -> Доверенные корневые центры сертификации
Активация конфигурации и перезапуск:
```bash
sudo ln -s /etc/nginx/sites-available/mixranker /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl restart nginx
```

## 8. Настройка UFW (Фаервол)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

## 9. Диагностика и логи

Просмотр логов приложения:
```bash
sudo journalctl -u mixranker -f
sudo journalctl -u mixranker -n 30 --no-pager
```

Просмотр логов Nginx:
```bash
sudo tail -f /var/log/nginx/error.log
```

Перезапуск компонентов при обновлении:
```bash
sudo systemctl daemon-reload
sudo systemctl restart mixranker
sudo systemctl restart nginx
```

---

## Важные примечания
* Без установленной переменной `SECRET_KEY` приложение не запустится.
* Если база данных пуста и при первом старте не переданы переменные `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD`, администратор создан не будет.
* При переносе переменных в systemd (`Environment=`), указывайте их явные текстовые значения, так как системные демоны не считывают ваш `~/.bashrc`.

---

## Запуск на Windows (PowerShell)

Разработка ведется через WSL/Linux. Для локального запуска в среде Windows:

```powershell
cd C:\WORK\programming\mixranker
.\venv\Scripts\Activate.ps1

# Генерация ключа
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Установка окружения для текущей сессии
\$env:SECRET_KEY = "сгенерированный_ключ"
\$env:FLASK_CONFIG = "production"
\$env:BOOTSTRAP_ADMIN_USERNAME = "admin"
\$env:BOOTSTRAP_ADMIN_PASSWORD = "сложный_пароль"

# Запуск
python app.py

# Удаление bootstrap-переменных после создания админа
Remove-Item Env:BOOTSTRAP_ADMIN_USERNAME
Remove-Item Env:BOOTSTRAP_ADMIN_PASSWORD
```
