import os
import base64
from io import BytesIO

import numpy as np
from matplotlib.figure import Figure
from astropy.time import Time


import flask
from flask import render_template, redirect, url_for, request, flash


app = flask.Flask(__name__)

# =============== #
#    DataAccess   #
# =============== #
import ztfcosmoidr
sample = ztfcosmoidr.Sample.load_release("dr3")
rng = np.random.default_rng()

# =============== #
#     Routes      #
# =============== #
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/classify/<name>", methods=["GET", "POST"])
def classify(name):


    if request.method == "POST":
        which = list(request.form.keys())[0]
        if which == "favorite":
            print("TO BE ADDED TO FAVORITE LIST")
        elif which == "classification":
            classification = list(request.form.values())[0].lower().strip()
            print(f"Classification becomes: {classification}")
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
def targetlist():
    return render_template("targetlist.html", data=sample.data)

@app.route("/target/<name>")
#@login_required | blinded inside
def target_page(name):
    """ """

    #   data    ------- #
    lc = sample.get_target_lightcurve(name, as_dataframe=False)
    spectra = sample.get_target_spectra(name)
    this_data = sample.data.loc[name]

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
