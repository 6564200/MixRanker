Install

sudo apt update
sudo apt upgrade

sudo apt install mc htop git python3 python3-pip python3-venv

sudo chown 'user':'user' /var/www

sudo chown -R www-data:www-data /var/www
sudo usermod -a -G www-data 'user'

sudo chmod -R 775 /var/www

exit


git clone https://github.com/user/repository.git
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt



