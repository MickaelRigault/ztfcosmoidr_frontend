__version__ = "0.1.0"
__version__="0.1.0"

from flask import Flask

app = Flask(__name__)

app.config['SECRET_KEY'] = "ztfcosmo_key"
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

import ztfcosmoidr_frontend.main

if __name__ == "__main__":
    app.run(host="127.0.0.1", port="8000")
