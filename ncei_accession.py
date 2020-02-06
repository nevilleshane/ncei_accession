"""
Description:
-------------
Python application to read the text from an NCEI Silver Springs email and extract the 
file set urls and acession date.  These are then used to generate and execute SQL to 
update the fileset table in the database.

Requirements:
--------------
Python 3
The python module: psycopg2 (pip install psycopg2)
A JSON config file, named config.json, in the same directory as this python file, that contains
the database connection parameters

To Run:
--------
> python ncei_accession.py
Then paste the whole of the text of the "NCEI receipt confirmation and publication" email in
to the top text box, including the line with the date at the top.  If no date is included, the 
application will use today's date.
Click Generate SQL.  This will generate the SQL commands to update the fileset table in the database.
Check the SQL looks correct.
Click Execute SQL.

Author:
--------
Neville Shane, Lamont Doherty Earth Observatory, Columbia University (ns3131@columbia.edu)
2020-01-22
"""

import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import re
import psycopg2
import psycopg2.extras
import json

config = json.loads(open('config.json', 'r').read())

def connect_to_db():
    info = config['DATABASE']
    conn = psycopg2.connect(host=info['HOST'],
                            port=info['PORT'],
                            database=info['DATABASE'],
                            user=info['USER'],
                            password=info['PASSWORD'])
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return (conn, cur)


def show_sql(sql):
    sql_text.insert("1.0", sql)
    if sql.find("ERROR") < 0:
        run_sql_btn["state"] = "active"
    else:
        run_sql_btn["state"] = "disabled"


def generate_sql():
    text = email_text.get("1.0", "end-1c")
    sql = ""
    sql_text.delete("1.0","end-1c")
    days = ["Mon ", "Tue ", "Wed ", "Thu ", "Fri ", "Sat ", "Sun "]
    accession_date = None

    # extract fileset_id, url and accession_date
    try:
        # try and find date
        lines = text.split('\n')
        for line in lines:
            if line[0:4] in days:
                email_date = line[0:24]
                date = datetime.strptime(email_date, '%a %b %d %X %Y')
                accession_date = date.strftime('%Y-%m-%d')
                break
    except:
        sql += "-- NO VALID DATE FOUND IN EMAIL - USING TODAY'S DATE FOR accession_date\n"
        accession_date = datetime.now().strftime('%Y-%m-%d')
    if not accession_date:
        sql += "-- NO DATE FOUND IN EMAIL - USING TODAY'S DATE FOR accession_date\n"
        accession_date = datetime.now().strftime('%Y-%m-%d')

    try:
        urls = re.findall('https://accession.nodc.noaa.gov/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        if len(urls) == 0:
            sql += "ERROR: No URLs found in email text.  Please ensure you paste entire email.\n"
        else:
            for url in urls[1:]:
                url_end = url.rfind('/')
                url = url[0:url_end]
                ids = url.split('/')[-1]
                fileset_id = ids.split('_')[1]
                if int(fileset_id) < 600000:
                    sql += "UPDATE fileset SET url = '%s', accession_date = '%s' WHERE id = %s;\n" % (url, accession_date, fileset_id)
            sql += "COMMIT;"
    except:
        sql += "ERROR: Unable to read urls from email text.  Please ensure you paste entire email.\n"


    show_sql(sql)

def run_sql():
    try:
        sql = sql_text.get("1.0", "end-1c")
        conn, cur = connect_to_db()
        cur.execute(sql)
        messagebox.showinfo("Success", "Database successfully updated")
    except Exception as e:
        messagebox.showerror("Error", "Error updating database: \n%s" % str(e))

         

master = tk.Tk()
master.title("NCEI Email Ingestor")
tk.Label(master, text="Paste email text:").pack()

# e1 = tk.Entry(master).pack()
email_text = tk.Text(master, width = 160, height = 25, padx=5, pady=5,  borderwidth=2, relief="groove")
email_text.pack(padx=5)

tk.Button(master, text='Generate SQL', command=generate_sql).pack(padx=5)

tk.Label(master, text="SQL:").pack()
sql_text = tk.Text(master, width = 160, height = 10, padx=5, pady=5,  borderwidth=2, relief="groove")
sql_text.pack(padx=5)

run_sql_btn = tk.Button(master, text='Execute SQL', command=run_sql, state="disabled")
run_sql_btn.pack(padx=5)

tk.Button(master, 
          text='Quit', 
          command=master.quit).pack(side=tk.RIGHT, padx=5)
master.mainloop()

