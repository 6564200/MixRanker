Install

    sudo apt update && sudo apt upgrade -y

    sudo apt install python3 python3-venv python3-pip nginx git ufw htop mc fail2ban unzip -y

CLONE

    cd /var/www && sudo git clone https://github.com/6564200/MixRanker.git

sudo chown -R *user:*user MixRanker

    cd MixRanker

FLAGS

    cd /var/www/MixRanker/static/flags && unzip 4x3.zip

VENV

    python3 -m venv venv

    source venv/bin/activate

    pip install --upgrade pip && pip install -r requirements.txt

SECRET_KEY

    nano ~/.bashrc
  Добавь в конец:

    export SECRET_KEY="тут_любой_случайный_строковый_ключ"
    export FLASK_APP=app.py
    export FLASK_ENV=production

source ~/.bashrc

TEST

    cd /var/www/MixRanker && source venv/bin/activate

    flask run --host=0.0.0.0
http://0.0.0.0:5000

WSGI
sudo nano /etc/systemd/system/mixranker.service

    [Unit]
    Description=Gunicorn instance to serve MixRanker Flask app
    After=network.target
    [Service]
    User=*user
    Group=www-data
    WorkingDirectory=/var/www/MixRanker
    Environment="PATH=/var/www/MixRanker/venv/bin"
    Environment="SECRET_KEY=${SECRET_KEY}"
    ExecStart=/var/www/MixRanker/venv/bin/gunicorn --workers 3 --bind nix:/var/www/MixRanker/mixranker.sock wsgi:app

    [Install]
    WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable mixranker
sudo systemctl start mixranker
sudo systemctl status mixranker

NGINX
sudo nano /etc/nginx/sites-available/mixranker
  
    server {
    listen 80;
    server_name _ ;

    location / {
      include proxy_params;
      proxy_pass http://unix:/var/www/MixRanker/mixranker.sock;
    }

    location /static/ {
        alias /var/www/MixRanker/static/;
    }
    }

sudo ln -s /etc/nginx/sites-available/mixranker /etc/nginx/sites-enabled/

sudo nginx -t

sudo systemctl restart nginx

sudo rm /etc/nginx/sites-enabled/default

sudo systemctl reload nginx

UFW
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status

TEST
sudo journalctl -u mixranker -f
sudo journalctl -u mixranker -n 30 --no-pager

sudo tail -f /var/log/nginx/error.log
sudo systemctl daemon-reload
sudo systemctl restart mixranker
sudo systemctl restart nginx

