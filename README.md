# ncei_accession

Description:
-------------

Python application to read the text from an NCEI Silver Springs email, or NCEI Boulder Excel file,
and extract the file set urls and acession date.  These are then used to generate and execute SQL to 
update the fileset table in the database.

Requirements:
-------------

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
