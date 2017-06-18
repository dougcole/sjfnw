Instructions assume you're running linux or mac osx and can use a package manager ([`homebrew`](http://brew.sh/), `apt-get`, etc.) as needed.

#### Code

`git clone https://github.com/aisapatino/sjfnw.git`

#### Python & pip

The project uses python 2.7, which is probably already installed with your OS. Confirm by doing `python --version`. Install using package manager if needed.

You'll also need `pip`, python's package manager. It is included with python 2.7.9 and above, so you should have it already. Try `pip --version`.

If you don't have it, you can upgrade your python installation to 2.7.9 or 2.7.10, or [install pip directly](https://pip.pypa.io/en/stable/installing.html).

#### Git

May be installed already, check with `git --version`. Install/update using package manager if needed.

#### MySQL

Install mysql and a python-mysql adapter.

Linux: `apt-get install mysql-server python-mysqldb`  
OSX: `brew install mysql`, `pip install mysql-python`

If prompted for a password, enter the password from [`sjfnw/settings.py`](https://github.com/aisapatino/sjfnw/blob/master/sjfnw/settings.py#L43).

Create the database:

1. `mysql -uroot -p` to get into the mysql shell. This will prompt you for the password you set when you installed.
    - If you were **not** prompted for a password, your starting password is probably blank.  When prompted for it, just hit enter.  Once you've logged in, change your password to match `settings.py` (linked above):
  `SET PASSWORD FOR 'root'@'localhost' = PASSWORD('password goes here');`
2. `create database sjfdb_multi character set utf8 collate utf8_general_ci;`


#### Google Cloud tools

Install the Google Cloud SDK with App Engine component by following [these directions](https://cloud.google.com/appengine/docs/standard/python/download)

You do not need to do the optional last step of installing extra libraries. We're using a different version of Django than what App Engine provides.

#### Project dependencies

`./scripts/install-libs`

This will install everything listed in `requirements.txt` into the `libs` folder.

#### Update paths

Update your `~/.bashrc` (or other file depending on the shell you use)

```sh
export PYTHONPATH=$PYTHONPATH:[path to GC SDK]/platform/google_appengine
export PYTHONPATH=$PYTHONPATH:[path to GC SDK]/platform/google_appengine/lib/webob-1.2.3
export PYTHONPATH=$PYTHONPATH:[path to GC SDK]/platform/google_appengine/lib/yaml/lib
export PYTHONPATH=$PYTHONPATH:[path to repo]/sjfnw/libs
```

#### Verify

Run `./scripts/verify-install` to verify that you've installed everything successfully. It doesn't verify everything (for instance, database creation), but can check the basics. You should see output like this:

```
Checking installation...

Python: 2.7.6 (required: 2.7.x)
pip: 7.1.2 (required: any)
Mysql: 5.5.44 (required: 5.5.x or 5.6.x)
Google AppEngine SDK: Found in PATH and PYTHONPATH

Checking libs...
  - django: found
  - pytz: found
  - unicodecsv: found

✔ Basic installation checks passed.
```

#### Set up your local database

`./manage.py migrate`

You should see output as tables are created in the local database based on the project's model definitions.

For more info on what this does, see the [django docs](https://docs.djangoproject.com/en/1.8/topics/migrations/) and the [project migration docs](../how-to/database.md).

_If that didn't work, make sure `manage.py` has execute permissions. `chmod u+x manage.py` should work._

#### Create a superuser

`./manage.py createsuperuser`

A superuser is a django user account with the highest access levels - you can use it to log into the admin site on your local server.

Your username should be an email address.

---

Installation complete! Now check out [running a local server](./local-server.md) and [running tests](./running-tests.md).
