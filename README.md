knesset_forcast
===============
This is an AI project that produces forecasts got party members in the Israeli
Knesset.

Running the project
===================
The project is using the framework of Django, and uses Weka.

So, first step, install django on your machine.
When done, run the following commands from the main project directory:

```
python ./setup.py
python ./manage.py syncdb # Follow the instructions
python ./manage.py runserver
```

in your browser, go to localhost:8000
and follow the instructions until a data file is downloaded, then open it with Weka.
