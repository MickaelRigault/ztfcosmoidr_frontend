import os
from datetime import datetime
import base64
from io import BytesIO

import numpy as np
from matplotlib.figure import Figure
from astropy.time import Time


# - flask basics
import flask
from flask import render_template, redirect, url_for, request, flash
# - flask login and users.
from flask_login import UserMixin, LoginManager, logout_user, login_required, login_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON
from flask_migrate import Migrate


# data access
import ztfcosmoidr
from ztfcosmoidr import io

# internal tools
from .forms import LoginForm, UserForm

# -------------- #
# Let's start   #
# -------------- #
app = flask.Flask(__name__)

# --------------- #
# USER DB & login #
# --------------- #
app.config['SECRET_KEY'] = 'DEFAULT_KEY'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{io.IDR_PATH}/database/dr3.db'
release_db = SQLAlchemy(app)
migrate = Migrate(app, release_db)  # add this line
# with app.app_context():


# share the "current_user" information to all jinja2 templates
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # where to point to log if needed


class Classifications(release_db.Model):
    id = release_db.Column(release_db.Integer, primary_key=True)
    user_name = release_db.Column(release_db.String(100), nullable=False)
    target_name = release_db.Column(release_db.String(100), nullable=False)
    kind = release_db.Column(release_db.String(100), nullable=False)
    value = release_db.Column(release_db.String(100), nullable=False)
    date_added = release_db.Column(release_db.DateTime, default=datetime.utcnow)

# Designing the User model
class User(UserMixin, release_db.Model):
    id = release_db.Column(release_db.Integer, primary_key=True)
    name = release_db.Column(release_db.String(100), unique=True)
    email = release_db.Column(release_db.String(100), nullable=False, unique=True)
    password_hash = release_db.Column(release_db.String(128), nullable=False)
    favorite = release_db.Column(JSON, default=list, server_default='[]')

# this should be set after the definition or the db.Models.
with app.app_context():
    release_db.create_all()  # must come AFTER the model definition

# =============== #
#   DataAccess    #
# =============== #
sample = ztfcosmoidr.Sample.load_release("dr3")
rng = np.random.default_rng()

# =============== #
#     Routes      #
# =============== #
@app.route("/")
def home():
    return render_template("home.html")


# ----------------- #
#  Classification   #
# ----------------- #



# --------- #
#   User    #
# --------- #
# Make sure "current_user is defined."
@login_manager.user_loader
def load_user(user_id):
    return User.query.get( int(user_id) )


# registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = UserForm()
    print("form in")
    if form.validate_on_submit():  # If you submit, this happens
        print("validated on submit")
        # query the Users-Database that have the inout user email and return the first one
        # This should return None if it is indeed unique
        user = User.query.filter_by(name=form.name.data).first()
        if user is None:
            print(f"creating the user: {form.name.data}")
            # create a new db user entry
            hashed_pwd = generate_password_hash(form.password_hash.data, "pbkdf2:sha256")

            user = User(name=form.name.data,
                        email=form.email.data,
                        password_hash=hashed_pwd)

            # add it to the actual db
            release_db.session.add(user)
            # and commit it
            release_db.session.commit()
            flash("User added successfully", category="success")
            return redirect(url_for("home"))
        else:
            flash("User name already used. User not added to the database",
                  category="error")

        # Clearing this out
        form.name.data = ''
        form.email.data = ''
        form.password_hash.data = ''
    else:
        print(f"{form.validate_on_submit()=}")
        print(f"{form.errors=}")

    return render_template("register.html", form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    # entry the if went hit submit from login.html
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password_hash, form.password.data):
                login_user(user)  # Flask login
                return redirect(url_for("home"))
            else:
                flash("Wrong Password - Try again", category="error")
        else:  # no user
            flash("That user doesn't exist - Try again", category="warning")

    return render_template("login.html", form=form)


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

# ---------------- #
# Classification   #
# ---------------- #
@app.route("/classify/<name>", methods=["GET", "POST"])
@login_required
def classify(name):
    print(f"{name=}")
    if request.method == "POST":
        which = list(request.form.keys())[0]

        # Add to favorite
        if which == "favorite":
            if current_user.favorite is None:
                current_user.favorite = [name]

            elif name not in current_user.favorite:
                # does not accept .append
                current_user.favorite = current_user.favorite + [name]
            else:
                # does not accept .remove or .pop
                current_user.favorite = [f_name for f_name in current_user.favorite if f_name != name]

            release_db.session.commit()

        # Classify target
        elif which in ["classification"]:
            new_classification = list(request.form.values())[0].lower().strip()
            classification = Classifications(user_name=current_user.name,
                                             target_name=name,
                                             kind=which,
                                             value=new_classification
                                             )
            release_db.session.add(classification)
            release_db.session.commit()

        # report problem.
        else:
            print("Strange. This should not happen")

    return redirect(url_for(f"target_page", name=name))

# --------- #
# Targets   #
# --------- #
@app.route("/target/random")
def target_random():
    """ """
    name = rng.choice(sample.data.index)
    return redirect( url_for(f"target_page", name=name))

@app.route("/search", methods=["GET", "POST"])
def search():
    """ """
    if request.method == "POST":
        target_name = request.form["name"]
        return redirect( url_for(f"target_page", name=target_name))
    else:
        return redirect( url_for("home") )

@app.route("/targetlist")
@login_required
def targetlist():
    return render_template("targetlist.html", data=sample.data)

@app.route("/target/favorite")
@login_required
def favorite_targets():
    """ """
    list_of_favorite = current_user.favorite
    if list_of_favorite is None:
        list_of_favorite = []
    return render_template("targetlist.html", data=sample.data.loc[list_of_favorite])

@app.route("/target/<name>")
@login_required
def target_page(name):
    """ """
    #   data    ------- #
    lc = sample.get_target_lightcurve(name, as_dataframe=False)
    spectra = sample.get_target_spectra(name)
    this_data = sample.data.loc[name].copy()

    # has this target been over-classified ?
    db_classification = Classifications.query.filter_by(target_name=name).all()
    if db_classification is None:
        this_data['db_typing'] = this_data.classification
    else:
        # if it exist, take the last request.
        this_data['db_typing'] = db_classification[-1].value

    print(f"{this_data['db_typing']=}")
    # figures   ------- #
    # lightcurves
    buflc = BytesIO()
    axlc = Figure(figsize=[7, 2]).add_axes([0.08, 0.25, 0.87, 0.7])
    # generate the figure if any:

    if lc is not None:
        figlc = lc.show(ax=axlc) # 1. do the figure
    else:
        figlc = None

    # spectra   ------- #
    spectraplots = {}
    for ith_spec_, spec_ in enumerate(spectra): # could be a list of 0, 1 or more specta
        # safe out in case spectrum if None for some reason
        if spec_ is None:
            print(f"{spec_} is None")
            continue

        # store the filename to be able to identifying them later on.
        filename = spec_.filename
        if filename is not None:
            basename = os.path.basename(filename)
        else:
            basename = ith_spec_

        # Phase
        datetime = Time(spec_.obsdate, format="mjd").datetime
        axlc.axvline(datetime, ls="--", color="0.6", lw=1)

        # create a new buffer for each spectrum
        buf = BytesIO()
        figspec = Figure(figsize=[7, 2.5])

        # create the spectrum figure
        ax = figspec.add_axes([0.08, 0.25, 0.87, 0.65])
        _ = spec_.show(ax=ax, label=basename)
        _ = figspec.savefig(buf, format="png", dpi=150)
        spectraplots[basename] = base64.b64encode(buf.getbuffer()).decode("ascii")

    # - Store plots    #
    if figlc is not None:
        _ = figlc.savefig(buflc, format="png", dpi=150) # save it in a local variable
        lcplot = base64.b64encode(buflc.getbuffer()).decode("ascii") # encode in web accepted format.
    else:
        lcplot = None

    # build and return the target page.
    return render_template("target.html",
                            data=this_data,
                            # phase_coverage=this_phase_coverage,
                            spectraplots=spectraplots,
                            lcplot=lcplot,
                            )
