"""
Description:
-------------
Python application to read the text from an NCEI Silver Springs email, or NCEI Boulder Excel file,
and extract the file set urls and acession date.  These are then used to generate and execute SQL to 
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
Alternatively, upload the Boulder Excel .xslx file.
As a third option, you can read archive dates from the NCEI Boulder website https://www.ngdc.noaa.gov/mgg/json/
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
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror
from datetime import datetime
import re
import psycopg2
import psycopg2.extras
import json
import pandas as pd
import requests

config = json.loads(open('config.json', 'r').read())
json_base_url = 'https://www.ngdc.noaa.gov/mgg/json/'
json_files = ['mb-archive.json', 'wcsd-archive.json', 'trackline_survey_table.json']

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
        urls += re.findall('https://www.ncei.noaa.gov/archive/accession/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
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
                elif int(fileset_id) >= 600000 and int(fileset_id) < 6100000:
                   sql += "UPDATE product_set SET url = '%s', submit_date = '%s' WHERE id = %s;\n" % (url, accession_date, fileset_id) 
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


def load_excel_file():
    fname = askopenfilename(title = "Select file",filetypes = (("Excel files","*.xlsx"),("all files","*.*")))
    if fname:
        sql = ""
        sql_text.delete("1.0","end-1c")
        try:
            data = pd.read_excel(fname)
            df = pd.DataFrame(data, columns = ['Package Date', 'Package', 'Landing page'])
            for index, line in df.iterrows():
                try:
                    accession_date = line['Package Date'].strftime('%Y-%m-%d')
                except:
                    sql += "-- NO DATE FOUND IN EMAIL - USING TODAY'S DATE FOR accession_date\n"
                    accession_date = datetime.now().strftime('%Y-%m-%d')
                
                try:
                    fileset_id = line['Package'].split('_')[1]
                except:
                    sql += "-- WARNING: UNABLE TO EXTRACT FILESET ID FROM PACKAGE %s\n" % line['Package']
                    continue

                url = line['Landing page']

                if int(fileset_id) < 600000:
                    if 'http' in str(url):
                        sql += "UPDATE fileset SET url = '%s', accession_date = '%s' WHERE id = %s;\n" % (url, accession_date, fileset_id)
                    else:
                        sql += "-- WARNING: NO VALID URL FOUND FOR FILESET %s\n" % fileset_id 
                elif int(fileset_id) >= 600000 and int(fileset_id) < 6100000:
                    if 'http' in str(url):
                        sql += "UPDATE product_set SET url = '%s', submit_date = '%s' WHERE id = %s;\n" % (url, accession_date, fileset_id) 
                    else:
                        sql += "-- WARNING: NO VALID URL FOUND FOR PRODUCT SET %s\n" % fileset_id 

            sql += "COMMIT;"
        except Exception as e:                    
            sql += "-- ERROR: Unable to read urls from Excel file %s." % fname
            messagebox.showerror("Error", "Error updating database: \n%s" % str(e))
        show_sql(sql)


def read_website():

    data_device_map = {'SB': "'singlebeam'", 'G': "'gravimeter'", 'B': "'bathymetry'", 'MB': "'multibeam'"}
    conn, cur = connect_to_db()
    sql = ""
    for json_file in json_files:
        url = json_base_url + json_file
        r = requests.get(url)
        if r.status_code == 200: 
            sql += '-- READING FROM %s\n' % json_file          
            data = r.json()['data']
            for entry in data:
                if entry['Source'] == 'Rolling Deck to Repository':

                    if json_file == 'trackline_survey_table.json':
                        data_types = entry['Data Type'].split(',')
                        device_types = ','.join(data_device_map[d] for d in data_types)
                        query = """SELECT fileset_id, accession_date FROM fileset_service_view_v2 fsv
                                   JOIN fileset f ON f.id = fsv.fileset_id
                                   WHERE fsv.cruise_id='%s' AND device_type in (%s);""" % (entry['Survey'], device_types)
                        cur.execute(query)
                        res = cur.fetchall()

                        if len(res) == 0 and entry['Survey'] != 'EW0001':
                            sql += '-- WARNING: NO FILE SETS FOUND FOR %s, DEVICE TYPES %s\n' % (entry['Survey'], device_types)
                            print('WARNING: NO FILE SETS FOUND FOR %s, DEVICE TYPES %s\n' % (entry['Survey'], device_types))
                        else:
                            for r in res:
                                old_acc_date = r['accession_date']
                                new_acc_date = datetime.strptime(entry['Archived'], '%Y-%m-%d').date()
                                if (not old_acc_date or new_acc_date > old_acc_date):
                                    fileset_id = r['fileset_id']
                                    sql += "UPDATE fileset SET accession_date = '%s' WHERE id = %s;\n" % (entry['Archived'], fileset_id)

                    else:
                        instruments = re.split('; |, ', entry['Instrument'])
                        for instrument in instruments:
                            instrument = instrument.replace(' 710', ' EM710')
                            if instrument[0:2] in ['EM', 'EK']: 
                                instrument = 'Kongsberg ' + instrument

                            query = """SELECT fileset_id, accession_date, make_model_name FROM fileset_service_view_v2 fsv
                                    JOIN fileset f ON f.id = fsv.fileset_id
                                    WHERE fsv.cruise_id='%s' AND make_model_name ~* '%s';""" % (entry['Survey'], instrument)
                            cur.execute(query)
                            res = cur.fetchall()

                            if len(res) > 1:
                                for r in res:
                                    if json_file == 'mb-archive.json' and r['make_model_name'] == instrument:
                                        this_res = r
                                    elif json_file == 'wcsd-archive.json' and r['make_model_name'] == (instrument + ' [water column]'):
                                        this_res = r
                                res = [this_res]

                            if len(res) != 1:
                                sql += '-- WARNING: NUMBER OF FILE SETS FOUND FOR %s %s = %s\n' % (entry['Survey'], instrument, len(res))
                                # print('NUMBER OF FILE SETS FOUND FOR %s %s = %s' % (entry['Survey'], instrument, len(res)))
                            else:
                                old_acc_date = res[0]['accession_date']
                                new_acc_date = datetime.strptime(entry['Archived'], '%Y-%m-%d').date()
                                if (not old_acc_date or new_acc_date > old_acc_date):
                                    fileset_id = res[0]['fileset_id']
                                    sql += "UPDATE fileset SET url = '%s', accession_date = '%s' WHERE id = %s;\n" % (entry['Data Access'], entry['Archived'], fileset_id)
                    
        else:
            sql += "-- ERROR: Unable to access URL %s." % url
    show_sql(sql)


master = tk.Tk()
master.title("NCEI Email Ingestor")
tk.Label(master, text="Paste Silver Spring email text:").pack()

# e1 = tk.Entry(master).pack()
email_text = tk.Text(master, width = 160, height = 25, padx=5, pady=5,  borderwidth=2, relief="groove")
email_text.pack(padx=5)

tk.Button(master, text='Generate SQL from email text', command=generate_sql).pack(padx=5)

tk.Button(master, text='Or Generate SQL from Boulder Excel file', command=load_excel_file).pack(padx=5)

tk.Button(master, text='Or Generate SQL from Boulder JSON website', command=read_website).pack(padx=5)

tk.Label(master, text="SQL:").pack()
sql_text = tk.Text(master, width = 160, height = 10, padx=5, pady=5,  borderwidth=2, relief="groove")
sql_text.pack(padx=5)

run_sql_btn = tk.Button(master, text='Execute SQL', command=run_sql, state="disabled")
run_sql_btn.pack(padx=5)

tk.Button(master, 
          text='Quit', 
          command=master.quit).pack(side=tk.RIGHT, padx=5)
master.mainloop()

