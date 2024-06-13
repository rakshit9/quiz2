import pyodbc
from datetime import datetime, timedelta
from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from geopy.distance import geodesic
from wtforms import StringField, IntegerField, FloatField, SubmitField, validators
from wtforms.validators import DataRequired, Length, Optional, NumberRange


import os



app = Flask(__name__)
app.config['SECRET_KEY'] = 'SecureSecretKey'
print(os.environ.get('PYTHONPATH'))


def connection():
    server = 'demodbone.database.windows.net'
    username = 'rakshit'
    password = 'Canada@90'
    database = 'firstdatabase'
    driver = '{ODBC Driver 18 for SQL Server}'
    conn = pyodbc.connect(
        'DRIVER=' + driver + ';SERVER=' + server + ';PORT=1433;DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    return conn


@app.route('/', methods=['GET', 'POST'])
def main():
    try:
        conn = connection()
        cursor = conn.cursor()
        msg = "Database Connected Successfully"
        return render_template('index.html', error=msg)
    except Exception as e:
        return render_template('index.html', error=e)


#Search by Magnitude


class Form1(FlaskForm):
    mag = StringField(label='Enter Magnitude: ', validators=[DataRequired()])
    submit = SubmitField(label='Submit')


@app.route('/form1', methods=['GET', 'POST'])
def magnitudeData():
    form = Form1()
    cnt = 0
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()
            mag = float(form.mag.data)
            if mag <= 5.0:
                return render_template('form1.html', form=form, error="Magnitude must be > 5.0", data=0)

            cursor.execute("SELECT * FROM EarthquakeData where mag > ?", mag)
            result = []
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                result.append(row)
                cnt += 1
            return render_template('form1.html', result=result, cnt=cnt, mag=mag, form=form, data=1)

        except Exception as e:
            print(e)
            return render_template('form1.html', form=form, error=f"Magnitude must be numeric. Error: {e}", data=0)


    return render_template('form1.html', form=form)


#Search by Range & Days


class Form2(FlaskForm):
    r1 = StringField(label='Enter Magnitude Range 1: ', validators=[DataRequired()])
    r2 = StringField(label='Enter Magnitude Range 2: ', validators=[DataRequired()])
    days = StringField(label='Enter Days: ', validators=[DataRequired()])
    submit = SubmitField(label='Submit')


@app.route('/form2', methods=['GET', 'POST'])
def rangeData():
    form = Form2()
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()

            r1 = float(form.r1.data)
            r2 = float(form.r2.data)
            days = int(form.days.data) + 4

            if days - 4 > 30:
                return render_template('form2.html', form=form, error="Days must be less than or equal to 30.", data=0)
            if r1 > r2:
                return render_template('form2.html', form=form, error="Range 1 must be less than Range 2.", data=0)
            if days < 0 or r1 < 0 or r2 < 0:
                return render_template('form2.html', form=form, error="Input must be non-negative.", data=0)

            # Define today as the current date in UTC at the beginning of the day
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            days_ago = today - timedelta(days=days)

            cursor.execute("SELECT * FROM EarthquakeData where time >= ? AND mag BETWEEN ? AND ?", days_ago, r1, r2)

            result = []
            cnt = 0
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                result.append(row)
                cnt += 1

            return render_template('form2.html', result=result, cnt=cnt, r1=r1, r2=r2, days=days - 4, form=form, data=1)

        except Exception as e:
            return render_template('form2.html', form=form, error=f"An error occurred: {e}", data=0)

    return render_template('form2.html', form=form, data=0)


#Search by Location


class Form3(FlaskForm):
    lat = StringField(label='Enter Latitude: ', validators=[DataRequired()])
    lon = StringField(label='Enter Longitude: ', validators=[DataRequired()])
    km = StringField(label='Enter Kilometers: ', validators=[DataRequired()])
    submit = SubmitField(label='Submit')


@app.route('/form3', methods=['GET', 'POST'])
def useLongitudeAndLatitude():
    form = Form3()
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()
            lat = float(form.lat.data)
            lon = float(form.lon.data)
            km = float(form.km.data)
            cnt = 0

            cursor.execute("SELECT time, latitude, longitude, mag, id, place, type FROM EarthquakeData")
            result = []
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                if geodesic((float(row[1]), float(row[2])), (lat, lon)).km <= km:
                    result.append(row)
                    cnt += 1
            return render_template('form3.html', result=result, cnt=cnt, lat=lat, lon=lon, km=km, form=form, data=1)

        except Exception as e:
            print(e)
            return render_template('form3.html', form=form, error=f"Latitude must be in the [-90; 90] range, Latitude must be in [-180; 180] and all input must be numaric. Error: {e}")
    return render_template('form3.html', form=form, data=0)


#Search by Clusters


@app.route('/form4', methods=['GET', 'POST'])
def searchByClusters():
    if request.method == 'POST':
        try:
            conn = connection()
            cursor = conn.cursor()
            clus = request.form['clus']
            cnt = 0

            cursor.execute("SELECT * FROM EarthquakeData where type = ?", clus)
            result = []
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                result.append(row)
                cnt += 1
            return render_template('form4.html', result=result, cnt=cnt, clus=clus, data=1)

        except Exception as e:
            print(e)
            return render_template('form4.html', error=f"Range 1 and Range 2 must be numeric, Range 1 > Range 2 and Days must be integer and less then 31. Error: {e}", data=0)

    return render_template('form4.html', data=0)


#Does given Magnitude occur more often at night?

@app.route('/form5', methods=['GET', 'POST'])
def largeMagnitude():
    cnt = 0
    tot_cnt = 0
    try:
        conn = connection()
        cursor = conn.cursor()

        cursor.execute('select * from EarthquakeData where mag > 4.0')
        result = []
        while True:
            row = cursor.fetchone()
            if not row:
                break
            hour = row[0].hour  # Change this line
            if hour > 18 or hour < 7:
                result.append(row)
                cnt += 1
            tot_cnt += 1
        return render_template('form5.html', result=result, cnt=cnt, tot_cnt=tot_cnt, data=1)

    except Exception as e:
        print(e)  # this will print the error message to the console
        return render_template('form5.html', error=str(e), data=0)  # and this will display it on the webpage


class LatRangeForm(FlaskForm):
    latitude = StringField('Enter Latitude:', validators=[DataRequired()])
    degrees = StringField('Enter Number of Degrees:', validators=[DataRequired()])
    submit = SubmitField('Submit')

@app.route('/latrange', methods=['GET', 'POST'])
def lat_range_search():
    form = LatRangeForm()
    if form.validate_on_submit():
        try:
            latitude = float(form.latitude.data)
            degrees = float(form.degrees.data)
            lower_lat = latitude - degrees
            upper_lat = latitude + degrees

            conn = connection()
            cursor = conn.cursor()
            cursor.execute("SELECT time, latitude, longitude, id FROM testdata WHERE latitude BETWEEN ? AND ?", (lower_lat, upper_lat))
            results = cursor.fetchall()
            return render_template('latrange.html', form=form, results=results)
        except Exception as e:
            return render_template('latrange.html', form=form, error=str(e))

    return render_template('latrange.html', form=form)

class NetForm(FlaskForm):
    net = StringField('Enter Net Value:', validators=[DataRequired()])
    submit = SubmitField('Submit')


@app.route('/net-operation', methods=['GET', 'POST'])
def net_operation():
    form = NetForm()
    if form.validate_on_submit():
        net_value = form.net.data
        conn = connection()
        cursor = conn.cursor()

        # Count occurrences
        cursor.execute("SELECT COUNT(*) FROM testdata WHERE net = ?", (net_value,))
        count = cursor.fetchone()[0]

        # Delete entries
        cursor.execute("DELETE FROM testdata WHERE net = ?", (net_value,))
        conn.commit()

        # Count remaining entries
        cursor.execute("SELECT COUNT(*) FROM testdata")
        remaining_count = cursor.fetchone()[0]

        return render_template('net_operation.html', form=form, count=count, remaining_count=remaining_count, net_value=net_value)
    
    return render_template('net_operation.html', form=form)

class EntryForm(FlaskForm):
    time = IntegerField('Time (smallint):', [validators.InputRequired(), validators.NumberRange(min=0)])
    latitude = FloatField('Latitude:', [validators.InputRequired()])
    longitude = FloatField('Longitude:', [validators.InputRequired()])
    depth = FloatField('Depth:', [validators.InputRequired()])
    mag = FloatField('Magnitude:', [validators.InputRequired()])
    net = StringField('Net:', [validators.InputRequired(), validators.Length(max=50)])
    id = StringField('ID:', [validators.InputRequired(), validators.Length(max=50)])
    submit = SubmitField('Submit')



@app.route('/create-entry', methods=['GET', 'POST'])
def create_entry():
    form = EntryForm()
    if form.validate_on_submit():
        try:
            # Establish connection and cursor
            conn = connection()
            cursor = conn.cursor()

            # Check if ID already exists
            cursor.execute("SELECT id FROM testdata WHERE id = ?", (form.id.data,))
            if cursor.fetchone():
                return render_template('create_entry.html', form=form, message='Error: An entry with this ID already exists.')

            # Insert new record
            insert_query = """
            INSERT INTO testdata (time, latitude, longitude, depth, mag, net, id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (form.time.data, form.latitude.data, form.longitude.data,
                                          form.depth.data, form.mag.data, form.net.data, form.id.data))
            conn.commit()
            return render_template('create_entry.html', form=form, message='New record created successfully.')
        except Exception as e:
            return render_template('create_entry.html', form=form, message=f'Error: {e}')

    return render_template('create_entry.html', form=form)




class ModifyEntryForm(FlaskForm):
    net = StringField('Net ID:', validators=[DataRequired(), validators.Length(max=50)])
    time = IntegerField('Time (smallint):', validators=[Optional(), validators.NumberRange(min=0)])
    latitude = FloatField('Latitude:', validators=[Optional()])
    longitude = FloatField('Longitude:', validators=[Optional()])
    depth = FloatField('Depth:', validators=[Optional()])
    mag = FloatField('Magnitude:', validators=[Optional()])
    submit = SubmitField('Update Record')



@app.route('/modify-entry', methods=['GET', 'POST'])
def modify_entry():
    form = ModifyEntryForm()
    if form.validate_on_submit():
        conn = connection()
        cursor = conn.cursor()

        # Check if record exists
        cursor.execute("SELECT * FROM testdata WHERE id = ?", (form.net.data,))
        record = cursor.fetchone()
        if not record:
            return render_template('modify_entry.html', form=form, message="No record found with that Net ID.")

        # Build the update statement dynamically based on the fields provided by the user
        update_fields = []
        params = []

        if form.time.data is not None:
            update_fields.append("time = ?")
            params.append(form.time.data)
        if form.latitude.data is not None:
            update_fields.append("latitude = ?")
            params.append(form.latitude.data)
        if form.longitude.data is not None:
            update_fields.append("longitude = ?")
            params.append(form.longitude.data)
        if form.depth.data is not None:
            update_fields.append("depth = ?")
            params.append(form.depth.data)
        if form.mag.data is not None:
            update_fields.append("mag = ?")
            params.append(form.mag.data)

        if update_fields:
            params.append(form.net.data)
            update_query = "UPDATE testdata SET " + ", ".join(update_fields) + " WHERE id = ?"
            cursor.execute(update_query, tuple(params))
            conn.commit()

            return render_template('modify_entry.html', form=form, message="Record updated successfully.")

    return render_template('modify_entry.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)
