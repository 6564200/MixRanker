# MixRanker Installation Guide

### 1. Подготовка системы
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-venv python3-pip nginx git ufw mc fail2ban unzip -y
```

### 2. Клонирование и настройка прав
```bash
sudo mkdir -p /var/www/MixRanker
sudo chown -R \$USER:www-data /var/www/MixRanker
cd /var/www/MixRanker
# Замени ссылку на актуальную, если она изменится
git clone https://github.com .

# Подготовка структуры папок
mkdir -p /var/www/MixRanker/data /var/www/MixRanker/logs
cd /var/www/MixRanker/static/flags && unzip 4x3.zip
```

### 3. Виртуальное окружение
```bash
cd /var/www/MixRanker
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install gunicorn flask -r requirements.txt
deactivate
```

### 4. Настройка прав (важно для SQLite и логов)
```bash
sudo chown -R \$USER:www-data /var/www/MixRanker/data /var/www/MixRanker/logs
chmod -R 775 /var/www/MixRanker/data /var/www/MixRanker/logs
```

### 5. Systemd Service
Создайте файл: `sudo nano /etc/systemd/system/mixranker.service`
```ini
[Unit]
Description=Gunicorn instance to serve MixRanker Flask app
After=network.target

[Service]
User=kazarinov_maksim
Group=www-data
WorkingDirectory=/var/www/MixRanker
Environment="PATH=/var/www/MixRanker/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="SECRET_KEY=ChtoToOchenSecretnoe123"
Environment="BOOTSTRAP_ADMIN_USERNAME=admin"
Environment="BOOTSTRAP_ADMIN_PASSWORD=********"
ExecStart=/var/www/MixRanker/venv/bin/gunicorn --workers 1 --threads 4 --timeout 300 --umask 007 --bind unix:/var/www/MixRanker/mixranker.sock --capture-output --log-level info --error-logfile /var/www/MixRanker/logs/gunicorn_error.log --access-logfile /var/www/MixRanker/logs/gunicorn_access.log wsgi:app

[Install]
WantedBy=multi-user.target
```

Запуск сервиса:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mixranker
sudo systemctl start mixranker
sudo systemctl status mixranker
```

### 6. Nginx
Создайте конфиг: `sudo nano /etc/nginx/sites-available/mixranker`
```nginx
server {
    listen 80;
    server_name _;

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/MixRanker/mixranker.sock;
    }

    location /static/ {
        alias /var/www/MixRanker/static/;
    }
}
```

Активация:
```bash
sudo ln -s /etc/nginx/sites-available/mixranker /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Firewall
```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

### 8. Мониторинг и логи
```bash
# Логи системы
sudo journalctl -u mixranker -f

# Логи приложения и Gunicorn
tail -f /var/www/MixRanker/logs/gunicorn_error.log
tail -f /var/www/MixRanker/logs/gunicorn_access.log
```
