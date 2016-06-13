#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# coding=utf-8

from ghost import Ghost
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
from bs4 import NavigableString
from optparse import OptionParser
from urllib.request import urlopen
from urllib.parse import urljoin
from datetime import datetime
from tqdm import tqdm
import codecs
import urllib
import os
import sys
import csv
import re
import math
import time
import json
import logging

only_a_tags = SoupStrainer("a")

base_action_url = "http://nalus.usoud.cz/Search/"
search_url = urljoin(base_action_url, "Search.aspx")
results_url = urljoin(base_action_url, "Results.aspx")
html_dir = "HTML"
screens_dir = "screens"
txt_dir = "TXT"

def set_logging():
	# settings of logging
	global logger
	logger = logging.getLogger(__file__)
	logger.setLevel(logging.DEBUG)
	hash_id = datetime.now().strftime("%d-%m-%Y")
	fh_d = logging.FileHandler(os.path.join(out_dir,__file__[0:-3]+"_"+hash_id+"_log_debug.txt"),mode="w",encoding='utf-8')
	fh_d.setLevel(logging.DEBUG)
	fh_i = logging.FileHandler(os.path.join(out_dir,__file__[0:-3]+"_"+hash_id+"_log.txt"),mode="w",encoding='utf-8')
	fh_i.setLevel(logging.INFO)
	# create console handler
	ch = logging.StreamHandler()
	ch.setLevel(logging.INFO)
	# create formatter and add it to the handlers
	formatter = logging.Formatter(u'%(asctime)s - %(funcName)-15s - %(levelname)-8s: %(message)s')
	ch.setFormatter(formatter)
	fh_d.setFormatter(formatter)
	fh_i.setFormatter(formatter)
	# add the handlers to logger
	logger.addHandler(ch)
	logger.addHandler(fh_d)
	logger.addHandler(fh_i)

def parameters():
	usage = "usage: %prog [options]"
	parser = OptionParser(usage)
	parser.add_option("-l","--last-days",action="store",type="int", dest="interval",default=None,help="number of days to checking")
	parser.add_option("-d","--output-directory",action="store",type="string", dest="dir",default="output_data",help="Path to output directory")
	parser.add_option("-f","--date-from",action="store",type="string", dest="date_from",default='1. 1. 1992',help="Start date of range (d. m. yyyy)")
	parser.add_option("-t","--date-to",action="store",type="string", dest="date_to",default=None,help="End date of range (d. m. yyyy)")
	parser.add_option("-c","--capture",action="store_true",dest="screens",default=False,help="Capture screenshots?")
	parser.add_option("-o","--output-file",action="store",type="string",dest="filename",default="us_csv",help="Name of output CSV file")
	parser.add_option("-e","--extraction",action="store_true",dest="extraction",default=False,help="Make only extraction without download new data")
	(options, args) = parser.parse_args()
	options = vars(options)

	print(args,options,type(options))
	return options

def view_data(date_from,records_per_page,date_to=None):
	"""
	set form for searching
	:param date_from: start date for searching
	:return: Bool
	"""
	if session.exists("#ctl00_MainContent_decidedFrom"):
		logger.debug("Set date_from '%s'" % date_from)
		session.set_field_value("#ctl00_MainContent_decidedFrom", date_from)
		if date_to is not None:
			session.set_field_value("#ctl00_MainContent_decidedTo", date_to)
		logger.debug("Set sorting criteria")
		session.set_field_value("#ctl00_MainContent_razeni","3")
		logger.debug("Set counter records per page")
		session.set_field_value("#ctl00_MainContent_resultsPageSize", str(records_per_page))
	# session.capture_to(screen_dir_path+"/set_form.png")
	try:
		logger.debug("Click to search button")
		session.click("#ctl00_MainContent_but_search", expect_loading=True)
	except Exception:
		logger.warning("Exception")
		return False
	
	return True

def how_many(response,records_per_page):
	soup = BeautifulSoup(response, "html.parser")
	# print(soup.prettify())
	result_table = soup.select_one("#Content")
	info = result_table.select_one("table > tbody > tr:nth-of-type(1) > td > table > tbody > tr > td")
	pages = info.text
	m = re.compile("\w+ (\d+) - (\d+) z \w+ (\d+).*").search(pages)
	#print(m.group(3))
	number_of_records = m.group(3)
	count_of_pages = math.ceil(int(number_of_records) / records_per_page)
	# print(count_of_pages)
	if pages is not None:
		pages = int(count_of_pages)
	return (pages,number_of_records)

def make_soup(path):
	soup = BeautifulSoup(codecs.open(path,encoding="utf-8"),"html.parser")
	return soup

def make_record(soup,id):
	ecli = ""
	# for record in tqdm(links):
	txt_file = id+"-text.txt"
	
	table = soup.find("div", id="recordCardPanel")
	if "NALUS" in soup.title.text:
		logger.debug("%s, %s, %s" % (soup.title.text,id,type(table)))
		return
	if (table is not None) and (table.tbody is not None):
		try:
			ecli = table.select_one("table > tbody > tr:nth-of-type(1) > td:nth-of-type(2)").text
		except Exception:
			print("\ntable is not None ->",table is not None,id,"table.tbody is not None ->",table.tbody is not None)
			return
		mark = table.select_one("table > tbody > tr:nth-of-type(3) > td:nth-of-type(2)").text
		date = table.select_one("table > tbody > tr:nth-of-type(7) > td:nth-of-type(2)").text
		date = datetime.strptime(date, '%d. %m. %Y').strftime('%Y-%m-%d')
		court = table.select_one("table > tbody > tr:nth-of-type(2) > td:nth-of-type(2)").text
		link =  table.select_one("table > tbody > tr:nth-of-type(26) > td:nth-of-type(2)").text
		# extract decisions
		decision_result_element = table.select_one("table > tbody > tr:nth-of-type(18) > td:nth-of-type(2)")
		decisions = []
		for child in decision_result_element.contents:
			if "<br>" in str(child):
				clear_child = str(child).replace("</br>","").strip()
				items = [item.strip() for item in clear_child.split("<br>") if len(item) > 1]
				decisions.extend(items)
			else:
				decisions.append(child)
		decision_result = json.dumps(dict(zip(range(1,len(decisions)+1),decisions)),sort_keys = True,ensure_ascii = False)


		form_decision = table.select_one("table > tbody > tr:nth-of-type(11) > td:nth-of-type(2)").text
		item = {
			"registry_mark" : mark,
			"decision_date" : date,
			"court_name" : court,
			"web_path" : link,
			"local_path" : os.path.join(txt_dir_path,txt_file),
			"decision_result" : decision_result,
			"form_decision" : form_decision,
			"ecli" : ecli
		}
		logger.debug(item)
		writer_records.writerow(item) # write item to CSV
		#print (item)
	text = ""
	if not os.path.exists(os.path.join(txt_dir_path,txt_file)):
		try:
			text = soup.find("td",id="uc_vytah_cellContent").text
		except Exception:
			logger.debug("%s" % soup.prettify())
		# print (text.text.split("takto:")[0])
		# session.capture_to(path+"/detail_text_"+str(i)+".png",None,selector="#uc_vytah_cellContent")
		with codecs.open(os.path.join(txt_dir_path,txt_file),"w",encoding="utf-8") as f:
			f.write(text)

def extract_information():
	html_files = [os.path.join(html_dir_path,fn) for fn in next(os.walk(html_dir_path))[2]]
	print(len(html_files))

	fieldnames= ['court_name','registry_mark','decision_date','web_path','local_path', 'decision_result','form_decision','ecli']

	global writer_records


	csv_records = open(os.path.join(out_dir,output_file),'w',newline='',encoding="utf-8")

	writer_records = csv.DictWriter(csv_records,fieldnames=fieldnames,delimiter=";")
	writer_records.writeheader()

	from tqdm import tqdm
	i = 0
	t = tqdm(html_files)
	for html_f in t:
		id = os.path.basename(html_f)[0:-5]
		make_record(make_soup(html_f),id)
		#t.update()
		#print(i)
		"""i += 1
		if i==30:
			break"""
	#t.close()
	csv_records.close()

def extract_data(html_file,response):
	logger.debug("Saving file '%s'" % html_file)
	with codecs.open(os.path.join(html_dir_path,html_file),"w",encoding="utf-8") as f:
		f.write(response)

def get_links(response):
	list_of_links = []
	soup = BeautifulSoup(response, "html.parser", parse_only=only_a_tags)

	links = soup.find_all("a", class_=re.compile("resultData[0,1]"))
	# print("page=" + str(page - 1), len(links))
	
	if len(links) > 0:
		logger.debug("Found links on page")
		for link in links:
			# list_of_links.append(urljoin(base_action_url, link.get('href')))
			list_of_links.append(link.get('href'))
		# session.open(urljoin(results_url, "?page="+str(page)))
	else:
		logger.warning("Not found links on page")
	# print(".")

	# print(len(list_of_links), "==", i)
	return list_of_links

def walk_pages(page_from,pages):
	t = tqdm(range(page_from,pages))
	for page in t:
		t.set_description("(%s/%s => %.3f%%)"% (page + 1,  pages,  (page + 1)/pages*100))
		logger.debug("-------------------------")
		logger.debug("Page: %s" % page)
		response = session.content
		links_to_info = get_links(response)
		# print(path+"/"+links_to_info[-1].split("?")[1].split("&")[0]+".html") # last anchor of list
		#logger.debug(links_to_info)
		# session.capture_to(screen_dir_path+"/current_page.png")
		if len(links_to_info) > 0:
			"""if os.path.exists(html_dir_path+"/"+links_to_info[-1].split("?")[1].split("&")[0]+".html"):
				#sys.stdout.write(".")
				session.open(urljoin(results_url, "?page="+str(page + 1))) # go to next page
				continue"""
			#logger.info("page number: %s => %4s%%",page,str(page/pages*100))
			for link in tqdm(links_to_info):
				element = "a[href=\""+link+"\"]"
				# print(element)
				id=link.split("?")[1].split("&")[0]
				html_file = id+".html"
				if not os.path.exists(os.path.join(html_dir_path,html_file)):
					try:
						if session.exists(element):
							logger.debug("Click on link to detail")
							session.click(element, expect_loading=True)
						else:
							print("Save file with nonexist element")
							with codecs.open("real.html"+str(time.time()),"w",encoding="utf-8") as e_f:
								e_f.write(response)
					except Exception:
						logger.error("ERROR - click to detail (%s)" % element)
						logger.info(response)
						session.capture_to(screen_dir_path+"/error%s.png" % str(page))
						sys.exit(-1)
					# print(session.content)
					title, resources = session.evaluate("document.title")
					if not "NALUS" in title:
						extract_data(html_file,response=session.content)
						#print(ecli)
						#f.write(ecli+"\n")
						logger.debug("Back to result page")
						#
						#
						session.evaluate("window.history.back()", expect_loading=True) # back to results
						#
						#
			session.open(urljoin(results_url, "?page="+str(page + 1))) # got to next page
			with codecs.open(os.path.join(out_dir,"current_page.ini"), "w",encoding="utf-8") as f:
				f.write(str(page))


def main():
	print(U"Start US")
	global ghost
	ghost = Ghost()
	global session
	session = ghost.start(download_images=False, show_scrollbars=False, wait_timeout=999,display=False,plugins_enabled=False)
	session.open(search_url)
	#print(session.content)
	records_per_page = 20
	if view_data(date_from,records_per_page):
		session.capture_to(os.path.join(screens_dir_path,"_find_screen.png"))
		response = session.content
		if not session.exists("#ctl00_MainContent_lbError"):
			pages, records = how_many(response,records_per_page)
			# print(pages)
			logger.info("Pages: %s",pages)
			
			page_from = 0
			# pages = 790
			
			if os.path.exists(os.path.join(out_dir,"current_page.ini")):
				with codecs.open(os.path.join(out_dir,"current_page.ini"),"r") as cr:
					page_from = int(cr.read().strip())
				logger.debug("Start on page %d" % page_from)
				logger.info("pages: %s, records %s" % (pages,records))
			if (page_from + 1) > pages:
				logger.debug("Loaded page number is greater than count of pages")
				page_from = 0
			if pages != (page_from + 1): # parametr page is from zero
				walk_pages(page_from,pages)
				logger.info("DONE - download")
			else:
				logger.debug("I am complete!")
		else:
			logger.info("Not found new records")
		logger.info("Extract information...")
		extract_information()
		logger.info("DONE - extraction")
		with codecs.open(os.path.join(out_dir,"current_page.ini"), "w",encoding="utf-8") as f:
			f.write("0")

		return True

if __name__ == "__main__":
	options = parameters()
	out_dir = options["dir"]
	days = options["interval"]
	date_from = options["date_from"]
	date_to = options["date_to"]
	b_screens = options["screens"]
	output_file = options["filename"]

	if ".csv" not in output_file:
		output_file += ".csv"

	txt_dir_path = os.path.join(out_dir,txt_dir)
	html_dir_path = os.path.join(out_dir,html_dir)
	screens_dir_path = os.path.join(out_dir,screens_dir)
	set_logging()
	# create project directories
	if not os.path.exists(out_dir):
		os.mkdir(out_dir)
		print("Folder was created '"+out_dir+"'")
	for directory in [html_dir_path, txt_dir_path]:
		if not os.path.exists(directory):
			os.mkdir(directory)
			print("Folder was created '"+directory+"'")	
	if b_screens:
		if not os.path.exists(screens_dir_path):
			os.mkdir(screens_dir_path)
			print("Folder was created '"+screens_dir_path+"'")
		logger.debug("Erasing old screens")
		#os.system("rm -rf "+screens_dir_path)
	if options["extraction"]:
		logger.info("Only extract informations")
		extract_information()
		logger.info("DONE - extraction")
	else:
		if main():
			sys.exit(42)
		else:
			sys.exit(-1)