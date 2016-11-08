# Auxierre

My high school diploma project from 2015. 

Auxierre is a web based audio visualizer. Audio files are uploaded and then FFT is used to get the frequency information, which is sent to the client using AJAX and visualized using D3.
The backend is written in Flask, using PostgreSQL as a database. Celery is used to run the FFT, using Redis as a broker.

Note: Most of the config files, as well as static content (images, etc) has been stripped out.
