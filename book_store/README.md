# Full Stack Nanodegree Item Catalog

This is a web application developed using Python, flask, OAuth2 APIs, HTML, jQuery.

Using this applicaiton, user can get all the wonderful information about his/her favourite books. User can also write, modify and delete his/her reviews for various books along with reading reviews of other users. On top of that, if user wishes, he/she can directly buy the book from amazon.


## Requirements

### Server side

If your server and client are going to run on same machine, you need to install
- Vagrant
- Oracle Virtual bol

You will need a Python 2.x language installed in your server system with some libraries:

- python-sqlalchemy
- python-flask
- python-requests
- Flask-Login
- oauth2client
- requests

### Client side

To run this Web Application you will need a browser which should be in specific versions that fully supports the JavaScript language, which those browsers and versions are:

- Chrome: 4.0+
- IE(Internet Explorer): 9.0+
- Firefox: 2.0+
- Safari: 3.1+
- Opera: 9.0+

## Instructions

To Test this application you will need to following those steps:

### Server side

#### Make sure you've install Oracle VirtualBox and Vagrant and after cloning this project
Run vagrant up
Run vagrant ssh
These 2 commands will make sure to install required dependencies.


#### Run database_setup.py
This will create the required database file on server side.

```
$ python database_setup.py
``` 

#### Run create_records.py
This will make sure that the server is having all the data about various books, reviews by users on books etc.
```
$ python create_records.py
```

#### Run yourreads.py
This kicks in our web-server. Then  server will be running on port 8080.

```
$ python yourreads.py
```

### Client side
...
After this point, user can open his/her favourite web-browser and visti http://localhost:8080. This will present the home page and user can easily navigate to other pages of site.
...


## Licence

It's Completely Free. But, Do whatever you like to do on your own full responsibility;