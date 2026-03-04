from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    SelectField,
    DateField,
)
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Log in")


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    public_booking_slug = StringField(
        "Public booking link ID", validators=[DataRequired(), Length(max=64)]
    )
    submit = SubmitField("Sign up")


class StandardBookingForm(FlaskForm):
    service_type_id = SelectField("Service", coerce=int, validators=[DataRequired()])
    booking_date = DateField("Date", default=date.today, validators=[DataRequired()])
    # Frontend fills options via JS; disable strict choice validation.
    time_slot = SelectField(
        "Time slot",
        coerce=str,
        validators=[DataRequired()],
        validate_choice=False,
    )
    needs_removal = BooleanField("Removal (add-on)")
    needs_builder = BooleanField("Builder / extension (add-on)")
    client_name = StringField("Name", validators=[Optional(), Length(max=100)])
    client_contact = StringField("Contact", validators=[Optional(), Length(max=100)])
    client_notes = TextAreaField("Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Confirm booking")


class CustomQuoteForm(FlaskForm):
    client_notes = TextAreaField("Design request", validators=[Optional(), Length(max=1000)])
    needs_removal = BooleanField("Removal (add-on)")
    needs_builder = BooleanField("Builder / extension (add-on)")
    submit = SubmitField("Submit quote request")


class QuoteRespondForm(FlaskForm):
    service_type_id = SelectField("Service", coerce=int, validators=[DataRequired()])
    quoted_price = StringField("Quoted price", validators=[DataRequired()])
    submit = SubmitField("Send quote")


class WorkScheduleForm(FlaskForm):
    # Simplified: actual inputs live in the template; this is only the submit button.
    submit = SubmitField("Save schedule")

