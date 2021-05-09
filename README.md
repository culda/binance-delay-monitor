```
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create a .env file and fill in your details

```
#Api details
PUBLIC=
SECRET=

#Delay threshold for alerts (ms) 
DELAY=10000 

#yes or no. If yes, a task will be scheduled to place orders periodically
MOCK=no
```


```
python monitor.py
```
