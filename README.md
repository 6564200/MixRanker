INSTALLATION GUIDE 
====================================
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-venv python3-pip nginx git ufw mc fail2ban unzip -y

sudo mkdir -p /var/www/MixRanker
sudo chown -R $USER:www-data /var/www/MixRanker
cd /var/www/MixRanker
git clone https://github.com .

cd /var/www/MixRanker/static/flags && unzip 4x3.zip

cd /var/www/MixRanker
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install gunicorn flask -r requirements.txt
flask run --host=0.0.0.0
deactivate

sudo nano /etc/systemd/system/mixranker.service
-----------------------------------------------------------
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
-----------------------------------------------------------

sudo systemctl daemon-reload
sudo systemctl enable mixranker
sudo systemctl start mixranker
sudo systemctl status mixranker

sudo chown -R $USER:www-data /var/www/MixRanker/data
sudo chown -R $USER:www-data /var/www/MixRanker/logs
chmod -R 775 /var/www/MixRanker/data
chmod -R 775 /var/www/MixRanker/logs


sudo nano /etc/nginx/sites-available/mixranker
-----------------------------------------------------------
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
-----------------------------------------------------------

sudo ln -s /etc/nginx/sites-available/mixranker /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

-----------------------------------------------------------
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable

-----------------------------------------------------------

sudo journalctl -u mixranker -f
sudo journalctl -u mixranker -n 30 --no-pager
sudo tail -f /var/log/nginx/error.log
tail -f /var/www/MixRanker/logs/vmix_ranker.log # Логи приложения
tail -f /var/www/MixRanker/logs/gunicorn_error.log # Ошибки Gunicorn
tail -f /var/www/MixRanker/logs/gunicorn_access.log # Доступы Gunicorn
