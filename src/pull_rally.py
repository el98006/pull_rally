'''
Created on Feb 1, 2017

@author: eli
'''
import re
import xml.etree.ElementTree as xt
import os
import urllib2
import json

ROOT_DIR  = os.path.expanduser('~/Downloads/rally_dump')
    
    
INDEX_PAGE_HEADER = '<!DOCTYPE html> \
    <html><head><title>Platform Team User Stories </title> <link rel="stylesheet" href="css/bootstrap.min.css"> </head>\
    <body><p class="title"><b>Platform team User Stories</b></p> \
    <table class="table table-striped">\
    <thead> <tr> <th>ID</th> <th>Desc</th> <th>State</th> <th>CreationDate</th> </tr> <thead>\
    <tbody>' 
INDEX_PAGE_FOOTER = '</tbody> </table> </body> </html>'   
    
XML_FILENAME = 'Rally-Stories.xml'



LINE_CAP = 30

SIMPLE_ELEMENT = ['ObjectID','FormattedID','Name','Description', 'Notes','DirectChildrenCount', 'HasParent', 'c_ECommKanbanState', 'c_ReleaseDate','c_RT','c_ReleasePlan']
ARRAY_ELEMENT = ['Defects',  'Discussion', 'Tasks', 'TestCases', 'Attachments','Projects', 'Children', 'TestCases', 'Tags']
    
INDEX_PAGE_REC_TEMPLATE ='<tr> <td> <a href="{}"> {}</a> </td> <td>{}</td> <td>{}</td> <td>{}</td> </tr>'
SKIP_LIST = ['FormattedID', 'ObjectID', 'Name']

DETAIL_PAGE_HEADER_TEMPLATE = '<html><head><title> {} </title> <link rel="stylesheet" href="css/bootstrap.min.css"> </head> <body> <p class="title"> <h2> {} </h2></p>'
DETAIL_PAGE_STYLE = '<style> panel panel_default { padding-left: 80px; background-color:#f2f2f2}</style>'
DETAIL_PAGE_FOOTER_TEMPLATE = '</body> </html>'

DETAIL_PAGE_SECTION_TEMPLATE = '<h3> {heading} </h3> <div class="panel panel-default"> <div class="panel-body"> {body} </div> </div>'
SECTION_IN_SEQUENCE = [ 'Description', 'Notes', 'Attachments', 'Tasks',  'Defects', 'Discussion', 'Tags', 'Owner', 'c_RT', 'c_ECommKanbanState', 'c_ReleaseDate','c_ReleasePlan', 'TestCase']
DETAIL_BODY_TEMPLATE = {'Defects':'<li> <a href="{}" > {} </a> {} </li>', 'Discussion':'<li> <p class="text-muted"> <small>{} </small> at {} </p> <p> {} </p> </li>',\
                 'Tasks':'<li> <a href="{}" > {} </a> {} </li>', 'Attachments':'<li> <a href="{}"> {} </a> </li>'}
HEADING_MAPPING = {'c_ECommKanbanState':'State', 'c_ReleaseDate':'ReleaseDate', 'c_RT':'RT', 'c_ReleasePlan':'ReleasePlan'}

def non_blank_element(content):
    p = ['NONE', 'False', 'false','0','0.0']
    if content in p  or content == None: 
        return False
    elif re.match(r'\n\s.', content):
        return False
    else:
        return True

def authenticate_http():
    passwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passwd_mgr.add_password(None, BASE_URL, UNAME, PASS)
    handler = urllib2.HTTPBasicAuthHandler(passwd_mgr)
    opener = urllib2.build_opener(handler)
    opener.addheaders = [('Accepted', 'text/xml')]
    urllib2.install_opener(opener)
    '''install the opener, so all the future urllib.urlopen urlib2.request will base on this opener'''



def wrap_section_body_in_html(heading, details):
#heading, SECTION_SERIES
#details array of tuples
    
    
    #create unordered list if body is an array
    if heading is 'Tags':
        html_result = details
    elif heading in ARRAY_ELEMENT:
        result  = ['<ul>']
        for line in details:
            html_line = DETAIL_BODY_TEMPLATE[heading].format(*line)
            result.append(html_line)    
        result.append('</ul>')
        html_result = ''.join(result)
    else:
        html_result =  details
    return html_result      



def download_conversation_details(gen_urls):
    for url in gen_urls:
        authenticate_http()
        ret = urllib2.urlopen(url)
        resp = ret.read()
        root = json.loads(resp)
        p_text = root.get('ConversationPost').get('Text')
        p_user = root.get('ConversationPost').get('User').get('_refObjectName')
        p_timestamp = root.get('ConversationPost').get('CreationDate') 
        yield  p_user, p_timestamp, p_text,
        

    
def download_task_details(gen_url=None):
    
    for url in gen_url:
        authenticate_http()
        ret = urllib2.urlopen(url)
        resp = ret.read()
        root = json.loads(resp)
        ta_id = root.get('Task').get('ObjectID')
        ta_name= root.get('Task').get('FormattedID')
        ta_desc = root.get('Task').get('Name')
        link = os. path.join('./Task', str(ta_id), '.html')       
        yield link, ta_name, ta_desc    



def download_attachment_details(detail_urls):
    
    t_path = os.path.join(ROOT_DIR,'Attachment')
    if os.path.exists(t_path) is False:
        os.mkdir(t_path)

    
    for url in detail_urls:
        authenticate_http()
        ret = urllib2.urlopen(url)
        resp = ret.read()
        root = json.loads(resp)
        t_id = root.get('Attachment').get('ObjectID')
        t_content_url = root.get('Attachment').get('Content').get('_ref')
        t_content_name = unicode(root.get('Attachment').get('Name'))
       
        
        t_path = os.path.join(t_path, str(t_id))
        
        # t_fullpath is used to download attachments.  
        if os.path.exists(t_path) is False:
            os.mkdir(t_path)
        t_fullpath = os.path.join(t_path, t_content_name)       
        
        # download the attachment file using t_content_url, create file with the original filename
        req = urllib2.Request(t_content_url, headers={'User-Agent':'Mozilla/5.0'}, data=None)
        response = urllib2.urlopen(req)
        root = json.loads(response.read()) 
        
        with open(t_fullpath, 'wb') as fh:
            payload = root.get('AttachmentContent').get('Content')
            payload = payload.decode('base64')
            fh.write(payload)
        
        # t_link is used to create link on the user story detailed page, use relative url 
        t_link = os.path.join('./Attachment', str(t_id), t_content_name)
        
        yield  t_link.encode('utf-8'), t_content_name.encode('utf-8') 
        


def download_defect_details(gen_url):
    
    for url in gen_url:
        authenticate_http()
        ret = urllib2.urlopen(url)
        resp = ret.read()
        root = json.loads(resp)
        de_id = root.get('Defect').get('ObjectID')
        de_name= root.get('Defect').get('FormattedID')
        de_desc = root.get('Defect').get('Name')
        link = os. path.join('./Defect', str(de_id), '.html')       
        yield link, de_name, de_desc

def extract_from_itemarray(xml_element):
    for item in xml_element.find('_itemRefArray'):
        url_ref = item.attrib['ref']
        yield url_ref



def get_tags(xml_element):
    tag_list =[]
    tag_num = xml_element.find('Count')
    
    # if number of tags > 0
    if tag_num <> '0':    
        my_tags = xml_element.find('_tagsNameArray')
        for my_tag in my_tags:
            x = my_tag.find('Name').text
            tag_list.append(x)
        tags = ','.join(tag_list)
        
        return tags
    else:
        return None
    
def commmon_array_handler(xml_element):
    SECTION_HANDLING_FUNCTIONS = {'Discussion':download_conversation_details, 'Attachments':download_attachment_details, \
    'Defects':download_defect_details, 'Tasks':download_task_details}

    element_type = xml_element.tag
    
    if element_type == 'Tags':
        tags = get_tags(xml_element)
        return tags
    else:
        generator_urls = extract_from_itemarray(xml_element)
        generator_tuples = SECTION_HANDLING_FUNCTIONS[element_type](generator_urls)
    return generator_tuples


def get_story_details(us_element):
     
    details = {}
    for c in us_element.getchildren():
        if c.tag == 'Owner' and c.attrib['refObjectName']:
            details[c.tag] = c.attrib['refObjectName']
            
        if c.tag in SIMPLE_ELEMENT:
            if non_blank_element(c.text):
                details[c.tag] = c.text
        elif c.tag in  ARRAY_ELEMENT:
         
            try:
                child_num = c.find('Count')
                if  child_num is None: 
                    continue
                elif child_num.text <> '0':
                    # if have of list of items stored in _itemRefArray, based on the element type, route to handler functions.  
                    details[c.tag] = commmon_array_handler(c)
            except KeyError:
                pass

    return details

        

def generate_detail_page_section(fh, details):
# fh: file handle for detail story page
# detail: dict {key= section_heading, value= array of tuples, each tuple is a detail line for complex element_type
    for heading in SECTION_IN_SEQUENCE:
        try:
            
            body = wrap_section_body_in_html(heading, details[heading])
            if heading in HEADING_MAPPING:
                heading = HEADING_MAPPING[heading]
            section_html = DETAIL_PAGE_SECTION_TEMPLATE.format(heading=heading, body=body)          
            fh.writelines(section_html)
        except KeyError:
            print 'heading doesn\'t exist {}, skipping'.format(heading)
            continue



def generate_detail_page(details, out_dir):
    if details['ObjectID']:
        fname = details['ObjectID']
    else:
        fname = 'dummy'
    fp = os.path.join(out_dir,fname+'.html')
        
    with open(fp, 'wt') as fh:
        title = details['FormattedID'] + ':' + details['Name']
        headline = DETAIL_PAGE_HEADER_TEMPLATE.format(title,title) 
        fh.writelines(headline)
        fh.writelines(DETAIL_PAGE_STYLE)
        
        # output by sections
        generate_detail_page_section(fh, details)

        fh.writelines(DETAIL_PAGE_FOOTER_TEMPLATE)


def process_xml(fullpath, indexf):
     
    lc = 0
    xf = xt.parse(fullpath)
    
    output_dir = os.path.dirname(fullpath)
    
    for i in xf.getroot().getchildren():
        if lc >= LINE_CAP:
            break
        else:
            details = get_story_details(i)
            detail_page_name = './' + details['ObjectID'] + '.html'
            line =  INDEX_PAGE_REC_TEMPLATE.format(detail_page_name, details['FormattedID'], i.attrib['refObjectName'], details['c_ECommKanbanState'], i.attrib['CreatedAt'])
            indexf.writelines(line)
            print line
            
            generate_detail_page(details, output_dir)
            
            lc += 1

if __name__ == '__main__':

    index_file = open(os.path.join(ROOT_DIR, 'index.html'),'wt')
    index_file.write(INDEX_PAGE_HEADER)
    xml_path = os.path.join(ROOT_DIR, XML_FILENAME)
    
    process_xml(xml_path, index_file)
    
    index_file.write(INDEX_PAGE_FOOTER)
    index_file.close()
    