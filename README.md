# the-constitutional-court-
Crawler of Czech Republic The Constitutional Court
Downloads HTML files and produces CSV file with results

## Requirements
* beautifulsoup4==4.4.1
* Ghost.py==0.2.3
* pandas==0.18.1
* PySide==1.2.4
* tqdm==4.8.4


##Usage
```
Usage: us-crawler.py [options]

Options:
  -h, --help            show this help message and exit
  -n, --not-delete      Not delete working directory
  -d DIR, --output-directory=DIR
                        Path to output directory
  -f DATE_FROM, --date-from=DATE_FROM
                        Start date of range (d. m. yyyy)
  -t DATE_TO, --date-to=DATE_TO
                        End date of range (d. m. yyyy)
  -c, --capture         Capture screenshots?
  -o FILENAME, --output-file=FILENAME
                        Name of output CSV file
  -e, --extraction      Make only extraction without download new data
  ```