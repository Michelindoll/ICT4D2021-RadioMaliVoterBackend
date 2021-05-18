from flask import Flask, request, jsonify, Response
import mysql.connector
import re
import time
app = Flask(__name__)


def db_connector(f):
    def wrapper():
        try:
            mydb = mysql.connector.connect(
                host="",
                database="",
                user="",
                password="")
            cur = mydb.cursor()
            returnal_val = f(cur)
        finally:
            mydb.commit()
            cur.close()
            mydb.close()

        return returnal_val

    wrapper.__name__ = f.__name__
    return wrapper


@app.route('/vote.xml', methods=['GET','POST'])
def vote():
    #This retrieves the http session referrer. This contains the code the caller selected and the phone number they are calling from.
    param = request.form.get('phone_number')
    print(param)
    param = request.referrer
    #Safely extract all needed info from the request referrer
    try:
        p = re.search("session.callerid=([1234567890]+)", param)
        print(p.group())
        phoneNo = str.split(p.group(), "=")[1]
    except:
        phoneNo = 00000000

    try:
        p2 = re.search("session.calledid=([1234567890]+)", param)
        print(p2.group())
        sessionId = str.split(p2.group(), "=")[1]
    except:
        sessionId = 00000000

    print(phoneNo)
    print(sessionId)

    #Create a session with the sql server
    mydb = mysql.connector.connect(
        host="",
        database="",
        user="",
        password=""
    )

    print(mydb)
    #Retrieve the id corresponding to the phone number that was called
    cur = mydb.cursor()
    sql = "SELECT pn.Id from PhoneNumber pn WHERE pn.Number = %s"
    val = [(sessionId)]
    cur.execute(sql, val)
    rows = cur.fetchall()
    phoneId = rows[0][0]
    print(phoneId)
    #Insert the new vote into the database.
    sql = "INSERT INTO Vote (SourcePhoneNumber, PhoneNumber, Timestamp) VALUES (%s, %s, %s);"
    val = (phoneNo, phoneId, time.strftime('%Y-%m-%d %H:%M:%S'))

    cur.execute(sql, val)
    mydb.commit()
    #This is a snippet of random XML to return to Voxeo, so it will think the data request was succesful.
    data = """<?xml version="1.0"?>
    <?access-control allow="*"?>
            <payee>
                <name>John Smith</name>
                <address>
                    <street>My street</street>
                    <city>My city</city>
                    <state>My state</state>
                    <zipCode>90210</zipCode>
                </address>
                <phoneNumber>0123456789</phoneNumber>
                <accountNumber>12345</accountNumber>
            </payee>
            """
    if param:
        return Response(data, mimetype='text/xml')
    else:
        return Response(data, mimetype='text/xml')


def datetime_parse(timestamps):
    res = []
    for timestamp in timestamps:
        if len(str(timestamp)) == 3:
            first = '0' + str(timestamp)[0]
            second = str(timestamp)[1:]
        else:
            first = str(timestamp)[0:2]
            second = str(timestamp)[2:]
        res.append(first)
        res.append(second)

    return res


@app.route('/new_poll', methods=['GET', 'POST'])
@db_connector
def new_poll(cur):
    params = request.args

    # deal with time zones
    start_date = params.get("start_date")
    start_time = params.get("start_time")
    end_date = params.get("end_date")
    end_time = params.get("end_time")
    radio_id = params.get("radioID")

    parse = datetime_parse([start_date, start_time, end_date, end_time])
    sd = f"{parse[1]}-{parse[0]}"
    st = f"{parse[2]}:{parse[3]}"
    ed = f"{parse[5]}-{parse[4]}"
    et = f"{parse[6]}:{parse[7]}"
    if parse[1] == '12' and parse[5] == '01':
        sy = time.strftime('%Y', time.gmtime())
        ey = time.strftime(f'{sy.tm_year + 1}', '%Y')
    else:
        sy = time.strftime('%Y', time.gmtime())
        ey = time.strftime('%Y', time.gmtime())

    name_query = f"IF (Select Id from Poll where RadioStation = {radio_id} " \
                 f"AND Name = (SELECT COUNT(DISTINCT(Id)) + 1 FROM Poll WHERE RadioStation = {radio_id})) is NULL " \
                 f"THEN SELECT COUNT(DISTINCT(Id)) + 1 FROM Poll WHERE RadioStation = {radio_id}; " \
                 f"ELSE SELECT MAX(Name) + 1 FROM Poll WHERE RadioStation = {radio_id} AND Name REGEXP('^[0-9]+$'); " \
                 f"END IF;"

    print(f"Going to execute query: {name_query}")

    cur.execute(name_query)

    poll_name = cur.fetchall()[0][0]

    query = f"INSERT INTO Poll(Name,StartDate,EndDate,RadioStation) " \
            f"VALUES('{poll_name}'," \
            f"'{sy}-{sd} {st}:00','{ey}-{ed} {et}:00',{radio_id});"

    print(f"Going to execute query: {query}")

    cur.execute(query)

    data = f"""<?xml version="1.0"?>
             <polldata><name>{poll_name}</name></polldata>"""
    if params:
        return Response(data, mimetype='text/xml')
    else:
        return Response(data, mimetype='text/xml')


@app.route('/get_count', methods=['GET', 'POST'])
@db_connector
def get_count(cur):
    params = request.args
    radio_id = params.get("radioID")

    query = f"""SELECT Name, `Number`, `Count` 
                FROM Results WHERE `Radio Id` = {radio_id} 
                AND StartDate < '{time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}' 
                ORDER by EndDate DESC LIMIT 2;"""

    print(f"Going to execute query: {query}")

    cur.execute(query)

    try:
        res = cur.fetchall()
        poll_name, c1, n1, c2, n2 = res[0][0], res[0][2], res[0][1], res[1][2], res[1][1]
    except:
        poll_name, c1, n1, c2, n2 = -1, 0, 0, 0, 0

    data = f"""<?xml version="1.0"?>
         <countdata><name>{poll_name}</name>
         <count1>{c1}</count1>
         <num1>{n1}</num1>
         <count2>{c2}</count2>
         <num2>{n2}</num2></countdata>"""
    if params:
        return Response(data, mimetype='text/xml')
    else:
        return Response(data, mimetype='text/xml')


@app.route('/get_code', methods=['GET', 'POST'])
@db_connector
def get_code(cur):
    params = request.args
    code = params.get("authCode")

    query = f"SELECT Id FROM RadioStation WHERE Code={code};"

    print(f"Going to execute query: {query}")

    cur.execute(query)

    try:
        res = cur.fetchall()
        radio_id = res[0][0]
    except:
        res = True
        radio_id = -1

    data = f"""<?xml version="1.0"?><authdata><radioStation>{radio_id}</radioStation></authdata>"""

    if res:
        return Response(data, mimetype='text/xml')
    else:
        return Response(data, mimetype='text/xml')


@app.route('/check_datetime', methods=['GET', 'POST'])
@db_connector
def check_datetime(cur):
    params = request.args
    start_date = params.get("start_date")
    start_time = params.get("start_time")
    end_date = params.get("end_date")
    end_time = params.get("end_time")
    radio_id = params.get("radioID")
    poll_name = 'tempName'
    start_date_status = 'OK'
    start_time_status = 'OK'
    end_date_status = 'OK'
    end_time_status = 'OK'

    if not start_time and not end_date and not end_time:
        parse = datetime_parse([start_date])
        day = parse[0]
        month = parse[1]
        year = time.strftime('%Y', time.gmtime())
        try:
            s_date = time.strptime(f"{day} {month} {year}", "%d %m %Y")
        except ValueError:
            start_date_status = 'WrongFormat'
        if start_date_status == 'OK':
            date = time.gmtime()
            cur_date = time.strptime(f"{date.tm_mday} {date.tm_mon} {date.tm_year}", "%d %m %Y")
            if s_date < cur_date:
                start_date_status = 'PastStart'
        if start_date_status == 'OK':
            try:
                next = time.strptime(f"{s_date.tm_mday + 1} {month} {year}", "%d %m %Y")
            except ValueError:
                try:
                    next = time.strptime(f"1 {s_date.tm_mon + 1} {year}", "%d %m %Y")
                except ValueError:
                    next = time.strptime(f"1 1 {s_date.tm_year + 1}", "%d %m %Y")
            n_mon = '0' + str(next.tm_mon) if len(str(next.tm_mon)) == 1 else str(next.tm_mon)
            n_day = '0' + str(next.tm_mday) if len(str(next.tm_mday)) == 1 else str(next.tm_mday)

            query = f"""SELECT Name FROM Poll 
                        WHERE RadioStation = {radio_id} 
                        AND StartDate <= '{year}-{month}-{day} 00:00:00' 
                        AND EndDate >= '{next.tm_year}-{n_mon}-{n_day} 00:00:00';"""

            print(f"Going to execute query: {query}")

            cur.execute(query)

            try:
                res = cur.fetchall()
                poll_name = res[0][0]
                start_date_status = 'DateTaken'
            except:
                pass
    elif start_time and not end_date and not end_time:
        parse = datetime_parse([start_date, start_time])
        day = parse[0]
        month = parse[1]
        hour = parse[2]
        min = parse[3]
        year = time.strftime('%Y', time.gmtime())
        s_date = time.strptime(f"{day} {month} {year} {hour}:{min}", "%d %m %Y %H:%M")
        date = time.gmtime()
        cur_date = \
            time.strptime(f"{date.tm_mday} {date.tm_mon} {date.tm_year} {date.tm_hour}:{date.tm_min}",
                          "%d %m %Y %H:%M")
        if s_date < cur_date:
            start_time_status = 'PastStart'
        if start_time_status == 'OK':
            query = f"""SELECT Name FROM Poll 
                        WHERE RadioStation = {radio_id} 
                        AND '{year}-{month}-{day} {hour}:{min}:00' BETWEEN StartDate AND EndDate;"""

            print(f"Going to execute query: {query}")

            cur.execute(query)

            try:
                res = cur.fetchall()
                poll_name = res[0][0]
                start_time_status = 'DatetimeTaken'
            except:
                pass
    elif start_time and end_date and not end_time:
        parse = datetime_parse([start_date, end_date])
        s_day = parse[0]
        s_month = parse[1]
        day = parse[2]
        month = parse[3]

        if s_month == '12' and month == '01':
            s_year = time.strftime('%Y', time.gmtime())
            year = time.strftime(f'{s_year.tm_year + 1}', '%Y')
        else:
            s_year = time.strftime('%Y', time.gmtime())
            year = time.strftime('%Y', time.gmtime())

        try:
            e_date = time.strptime(f"{day} {month} {year}", "%d %m %Y")
        except ValueError:
            end_date_status = 'WrongFormat'

        if end_date_status == 'OK' \
                and e_date < time.strptime(f"{s_day} {s_month} {s_year}", "%d %m %Y"):
            end_date_status = 'EndBeforeStart'
    else:
        parse = datetime_parse([start_date, start_time, end_date, end_time])
        s_day, s_month, s_hour, s_min = parse[0], parse[1], parse[2], parse[3]
        day, month, hour, min = parse[4], parse[5], parse[6], parse[7]
        if s_month == '12' and month == '01':
            s_year = time.strftime('%Y', time.gmtime())
            year = time.strftime(f'{s_year.tm_year + 1}', '%Y')
        else:
            s_year = time.strftime('%Y', time.gmtime())
            year = time.strftime('%Y', time.gmtime())

        if time.strptime(f"{day} {month} {year} {hour}:{min}", "%d %m %Y %H:%M") \
                < time.strptime(f"{s_day} {s_month} {s_year} {s_hour}:{s_min}", "%d %m %Y %H:%M"):
            end_time_status = 'EndBeforeStart'

        if end_time_status == 'OK':
            query = f"""SELECT Name FROM Poll
                        WHERE RadioStation = {radio_id}
                        AND (('{s_year}-{s_month}-{s_day} {s_hour}:{s_min}:00' BETWEEN StartDate AND EndDate)
                        OR ('{year}-{month}-{day} {hour}:{min}:00' BETWEEN StartDate AND EndDate)
                        OR ((StartDate BETWEEN '{s_year}-{s_month}-{s_day} {s_hour}:{s_min}:00' 
                        AND '{year}-{month}-{day} {hour}:{min}:00') 
                        AND (EndDate BETWEEN '{s_year}-{s_month}-{s_day} {s_hour}:{s_min}:00'
                        AND '{year}-{month}-{day} {hour}:{min}:00')));"""

            print(f"Going to execute query: {query}")
            cur.execute(query)

            try:
                res = cur.fetchall()
                poll_name = res[0][0]
                start_time_status = 'DatetimeTaken'
            except:
                pass

    data = f"""<?xml version="1.0"?>
             <polldata><name>{poll_name}</name>
             <startDate>{start_date_status}</startDate>
             <startTime>{start_time_status}</startTime>
             <endDate>{end_date_status}</endDate>
             <endTime>{end_time_status}</endTime></polldata>"""
    if params:
        return Response(data, mimetype='text/xml')
    else:
        return Response(data, mimetype='text/xml')


# A welcome message to test our server
@app.route('/')
def index():
    return "<h1>Welcome to our server !!</h1>"


if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
