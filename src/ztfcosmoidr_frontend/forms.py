# WhatTheForm
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, EqualTo

# Create a Form Class
class UserForm( FlaskForm ):
    name = StringField("Name", validators=[DataRequired()] )
    email = StringField("Email", validators=[DataRequired()] )

    password_hash = PasswordField("Password", validators=[DataRequired(),
                                                    EqualTo('password_hash_matched',
                                                            "password must match")] )
    newpassword_hash = PasswordField("New password")

    password_hash_matched = PasswordField("Confirm Password",
                                          validators=[DataRequired()]
                                          )
    submit = SubmitField("Submit") # For the button

    # user configuration
    # config__lcplot = StringField("config__lcplot")
    # config__reviewstatus = StringField("config__reviewstatus")


# Create LoginForm
class LoginForm( FlaskForm ):
    email = StringField("email", validators=[DataRequired()] )
    password = PasswordField("password", validators=[DataRequired()] )
    submit = SubmitField("Submit") # For the button
