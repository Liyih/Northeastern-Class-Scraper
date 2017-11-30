#Original Script written by Professor Cooperman and Modified by Jason Brooks, Yihang Li, and Wilson Liew
import sys
import os
import re
import mechanize
from bs4 import BeautifulSoup
from unidecode import unidecode
# import cookielib

# Modify these global variables:
URL = "https://wl11gp.neu.edu/udcprod8/NEUCLSS.p_disp_dyn_sched"
CourseLinkUrl = "https://wl11gp.neu.edu"
TERM = "Fall 2017 Semester"
os.umask(0133) # Read-write permission for user, read-only for others

profd = {}
majord = {}
coursed = {}
mcoded = {} #Maps the major code to its name
courses = []
sections = []

#Performs a lookup based on name (string) and td (the dictionary)
#Returns the key mapped to that name
def dict_lookup(name, td):
  if (td.has_key(name)):
    return td.get(name)
  else:
    td[name] = str(len(td)+1)
    return td.get(name)

#Looksup based on name(string) and pmc (Professor/Major/Course as one char)
def lookup(name, pmc):
  if (pmc == 'p'):
    return dict_lookup(name, profd)
  elif (pmc == 'm'):
    return dict_lookup(name, majord)
  elif (pmc == 'c'):
    return dict_lookup(name, coursed)
  else:
    print ("Hey, that's not a valid name to map!")

# Gets all the majors in the DB
def get_all_majors(URL, TERM):
  # Browser
  browser = mechanize.Browser()
  browser.open(URL)
  
  # for f in browser.forms(): print f # find forms, control names for each form
  TERM_ID = ""
  for line in browser.response().readlines():
    keyword = 'VALUE="'
    if keyword in line and TERM in line:
      start_idx = line.find(keyword) + len(keyword)
      TERM_ID = line[start_idx : line.find('"', start_idx)]
      break
  assert TERM_ID, '"'+TERM+'" not found'
  browser.select_form(nr=0)
  browser.form["STU_TERM_IN"] = [TERM_ID]
  browser.submit()
  
  browser.select_form(nr=0)
  # METHOD TO CREATE AN ARRAY OF MAJOR CODES
  control = browser.form.find_control('sel_subj', kind='list')
  depts = []
  for item in control.items:
    if (len(item.name) > 1):
      cd = unidecode(item.name)
      depts += [cd]
      n = str([label.text for label in item.get_labels()])
      n = n[3:n.rfind("-")-1]
      m = lookup(cd, 'm') #adds the major to the dictionary
      mcoded[m] = n #adds code and major name to their dictionary
  return depts
        

def web_to_rawhtml(URL, TERM, DEPT):
  # Browser
  browser = mechanize.Browser()
  browser.open(URL)
  
  # for f in browser.forms(): print f # find forms, control names for each form
  TERM_ID = ""
  for line in browser.response().readlines():
    keyword = 'VALUE="'
    if keyword in line and TERM in line:
      start_idx = line.find(keyword) + len(keyword)
      TERM_ID = line[start_idx : line.find('"', start_idx)]
      break
  assert TERM_ID, '"'+TERM+'" not found'
  
  browser.select_form(nr=0)
  browser.form["STU_TERM_IN"] = [TERM_ID]
  browser.submit()
  
  browser.select_form(nr=0)
  # For the values of kind, list includes subtypes singlelist and multilist.
  # browser.form.controls exists if there is more than one such control.
  try:
    browser.form.find_control('sel_subj', kind='list').value = [DEPT]
  except mechanize._form.ItemNotFoundError:
    sys.exit('Department "'+DEPT+'" not found\n')
  browser.submit()
  
  return str( browser.response().read() )

def rawhtml_to_courses(text, TERM, DEPT):
  text = text.replace(' (<ABBR title= "Primary">P</ABBR>)', '') # del this part
  text = text.replace('<ABBR title = "To Be Announced">TBA</ABBR>', 'TBA')
  text = text.replace('TBA &nbsp;', 'TBA')
  text = text.replace('&nbsp;', 'TBA')
  pattern = r'<TH CLASS="ddtitle"[^>]*>'
  raw_courses = re.split(pattern, text)[1:] # using regular expressions here
  # Skip 7900-, 8000- 9900-level courses
  raw_courses = [ course for course in raw_courses
                  if DEPT+" 99" not in course and DEPT+" 8" not in course
                                              and DEPT+" 79" not in course
                ]
  for course in raw_courses:
    sectionFields = []
    courseFields = []
    majorID = majord.get(DEPT)
    soup = BeautifulSoup(course, "html5lib")
    title = soup.find('a')
    header = title.text.split(' - ')
    if not(coursed.has_key(unidecode(header[0]))):
      courseID = lookup(unidecode(header[0]), 'c')
      courseFields += [courseID]
      courseFields += [unidecode(header[0])]
      courseFields += unidecode(header[len(header)-1][8:9])
      courseFields += [ unidecode(CourseLinkUrl + title['href']) ]
      addedCoreq = False
      addedPrereq = False
      for span in soup.find_all("span"):
        if span.text == 'Prerequisites: ':
          current = span
          prereq = ''
          while current.find_next_sibling().name != 'br' or current.name != 'br':
            current = current.next_sibling
            if current.name != 'br':
              if current.name != 'a':
                prereq += ' ' + str(current).strip()
              else:
                prereq += ' ' + current.text
          addedPrereq = True
        if span.text == 'Corequisites: ':
          current = span
          coreq = ''
          while current.find_next_sibling().name != 'br' or current.name != 'br':
            current = current.find_next_sibling()
            if current.name == 'a':
              coreq += ' ' + current.text
          addedCoreq = True
        
      if not(addedCoreq) and not(addedPrereq):
        courseFields += ['None']
        courseFields += ['None']
      elif addedCoreq and not(addedPrereq):
        courseFields += ['None']
        courseFields += [coreq]
      elif not(addedCoreq) and addedPrereq:
        courseFields += [prereq]
        courseFields += ['None']
      else:
        courseFields += [prereq]
        courseFields += [coreq]
      courseFields += [str(majorID)]
    else:
      courseID = lookup(unidecode(header[0]), 'c')
    
    instructorID = '-1'
    if 'Instructors:' in course:
      instructorName = course.split('Instructors: </SPAN>')[1].split(' \n')[:1]
      instructorID = lookup(instructorName[0], 'p')
    else:
      instructorID = lookup('TBA', 'p')
    if not(len(header) > 5):
      sectionFields += [unidecode(header[1])]
      sectionFields += [courseID]
      sectionFields += [instructorID]
      if len(soup.find_all("table", "datadisplaytable")) != 0:
        sectionFields += course.split('</TD>\n<TD CLASS="dddefault">')
        sectionFields = [ sectionFields[i] for i in [0,1,2,4,5,6,8,9] ]
      else:
        sectionFields += ['TBA']
        sectionFields += ['TBA']
        sectionFields += ['TBA']
        sectionFields += ['0']
        sectionFields += ['0']
      sections.append(sectionFields)
      if len(courseFields) > 0:
        courses.append(courseFields)




def td_array_to_csv(lists, header):
  for course in lists:
    header += ','.join(['"'+field.strip().replace(',', ' &')+'"' for field in course])+ ',' + '0' + '\n'
  return header

def dic_to_csv(dic, header):
  for tup in dic.items():
    (key, value) = tup
    header += key.strip().replace(',', ' &') + ',' + value.strip().replace(',', ' &') + ',' + '0' '\n'
  return header

def reverse_dic_to_csv(dic, header):
  for tup in dic.items():
    (key, value) = tup
    header += value.strip().replace(',', ' &') + ',' + key.strip().replace(',', ' &') + ',' + '0' '\n'
  return header

def create_file(data, filename):
  file = open(filename, 'w'); file.write(data); file.close()
  print ("Created:  " + filename)

def create_csv(DEPT):
  rawhtml = web_to_rawhtml(URL, TERM, DEPT)
  rawhtml_to_courses(rawhtml, TERM, DEPT)
  section = '' #'"CRN","CourseID","InstructorId","Time","Days","Location","Capacity","Enrolled","Saved"\n'
  course = '' #'"CourseID","CourseTitle","Credits","CourseLink","Prerequisites","Corequisites","MajorID","Saved"\n'
  for output in [('Section', td_array_to_csv(sections, section),".csv"), ('Course', td_array_to_csv(courses, course),".csv")]:
    (table, data, filetype) = output
    filename = ( DEPT + " " + table + " "+ TERM + filetype).replace(' ', '_')
    DEPT = DEPT
    create_file(data, filename)

def all_majors_to_csvs():
  depts = get_all_majors(URL, TERM)
  global courses
  global sections
  for item in depts:
    rawhtml = web_to_rawhtml(URL, TERM, item)
    rawhtml_to_courses(rawhtml, TERM, item)
    print(item)
  filename = ( "Professor " + TERM + '.csv').replace(' ', '_')
  professor = '' #'"InstructorId","Instructor(s)","Saved"\n'
  create_file(reverse_dic_to_csv(profd, professor), filename)
  filename = ( "Major " + TERM + '.csv').replace(' ', '_')
  major = '' #'"MajorID","MajorName","Saved"\n'
  create_file(dic_to_csv(mcoded, major), filename)
  filename = ( "Course " + TERM + '.csv').replace(' ', '_')
  course = '' #'"CourseID","CourseTitle","Credits","CourseLink","Prerequisites","Corequisites","MajorID","Saved"\n'
  create_file(td_array_to_csv(courses, course), filename)
  filename = ( "Section " + TERM + '.csv').replace(' ', '_')
  section = '' #'"CRN","CourseID","InstructorId","Time","Days","Location","Capacity","Enrolled","Saved"\n'
  create_file(td_array_to_csv(sections, section), filename)
  print ("Finished writing all files. Thanks for being patient!")

all_majors_to_csvs() 
