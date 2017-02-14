'''
Created on Feb 1, 2017

@author: eli
'''
import re
import xml.etree.ElementTree as xt
import os
import urllib2
import json




skip_list = ['FormattedID', 'ObjectID', 'Name']
field_name_mapping = {'c_ECommKanbanState':'State', 'c_ReleaseDate':'ReleaseDate', 'c_RT':'RT', 'c_ReleasePlan':'ReleasePlan'}
field_seq = [ 'Description', 'Notes', 'Attachments', 'Tasks',  'Defects', 'Discussion', 'Owner', 'c_RT', 'c_ECommKanbanState', 'c_ReleaseDate','c_ReleasePlan', 'TestCase']
html_template = {'Defects':'<li> <a href="{}" > {} </a> {} </li>', 'Discussion':'<li> <p class="text-muted"> {}  at {} </p> <p> {} </p> </li>',\
                 'Tasks':'<li> <a href="{}" > {} </a> {} </li>', 'Attachments':'<li> <a href="{}"> {} </a> </li>'}

DETAIL_PAGE_HEADER_TEMPLATE = '<html><head><title> {} </title> <link rel="stylesheet" href="css/bootstrap.min.css"> </head> <body> <p class="title"> <h2> {} </h2></p>'
DETAIL_PAGE_FOOTER_TEMPLATE = '</body> </html>'
DETAIL_PAGE_SECTION_HEADER_TEMPLATE = '<p class="lead"> <h3> {} </h3></p> {}'


    

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


def pack_in_html(gen_tuples, element_type):
    
    for value_tuple in gen_tuples:
        line = html_template[element_type].format(*value_tuple)    
        yield line
        
        
def write_detail_line(fh, details):   
    for field in field_seq:
        try:
            html_body = details[field]
            if field in field_name_mapping:
                field = field_name_mapping[field]
            line = DETAIL_PAGE_SECTION_HEADER_TEMPLATE.format(field, html_body)
        except KeyError:
            continue
        fh.writelines(line)
        

def generate_detail_page(details, out_dir):
    if details['ObjectID']:
        fname = details['ObjectID']
    else:
        fname = 'dummy'
    fp = os.path.join(out_dir,fname+'.html')
        
    with open(fp, 'wt') as fh:
        title = details['FormattedID'] + ':' + details['Name']
        line = DETAIL_PAGE_HEADER_TEMPLATE.format(title,title) 
        fh.writelines(line)
        write_detail_line(fh, details)
        fh.writelines(DETAIL_PAGE_FOOTER_TEMPLATE)



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
        
        
        
def conversation_handler(xml_element):

    authenticate_http()
    
    generator_url = extract_from_itemarray(xml_element)
    generator_tuples = download_conversation_details(generator_url)
    element_type = xml_element.tag
    html_lines = pack_in_html(generator_tuples, element_type)
    
    array_list = ['<ul>']
    for line in html_lines:
        array_list.append(line)
    array_list.append('</ul>')
    return array_list
    
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

def tasks_handler(xml_element):
    generator_details_url = extract_from_itemarray(xml_element)
    generator_task_tuples = download_task_details(generator_details_url)
    element_type = xml_element.tag
    html_lines = pack_in_html(generator_task_tuples, element_type)

    array_list = ['<ul>']
    for line in html_lines:
        array_list.append(line)
    array_list.append('</ul>')
    return array_list


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
        
def attachment_handler(xml_element):
    
    generator_detail_urls = extract_from_itemarray(xml_element)
    generator_attachment_tuples = download_attachment_details(generator_detail_urls)
    element_type = xml_element.tag
    html_lines = pack_in_html(generator_attachment_tuples, element_type)
    
    array_html_lines = []
    array_html_lines.append('<ul>')
    for  line in html_lines:
        array_html_lines.append(line) 
    array_html_lines.append('</ul>')
    return array_html_lines
    

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


        
def defect_handler(xml_element):

    generator_details_url = extract_from_itemarray(xml_element)
    generator_defect_tuples = download_defect_details(generator_details_url)
    element_type = xml_element.tag
    html_lines = pack_in_html(generator_defect_tuples, element_type)
    
    #current the routing of handler functions return an array of html, instead of generator
    array_html_lines = []
    array_html_lines.append('<ul>')
    for  line in html_lines:
        array_html_lines.append(line) 
    array_html_lines.append('</ul>')
    return array_html_lines



def commmon_handler(xml_element):
    SECTION_HANDLING_FUNCTIONS = {'Discussion':download_conversation_details, 'Attachments':download_attachment_details, \
                               'Defects':download_defect_details, 'Tasks':download_task_details}

    element_type = xml_element.tag
    generator_urls = extract_from_itemarray(xml_element)
    generator_tuples = SECTION_HANDLING_FUNCTIONS[element_type](generator_urls)
    
    return generator_tuples

def default_handler(item):
    array_list = []
    for item in item.find('_itemRefArray'):
        url_ref = item.attrib['ref']
        array_list.append('<p>' + url_ref + '</p>')
    return array_list

def get_story_details(us_element):
    simple_elements = ['ObjectID','FormattedID','Name','Description', 'Notes','DirectChildrenCount', 'HasParent', 'c_ECommKanbanState', 'c_ReleaseDate','c_RT','c_ReleasePlan']
    complex_elements = ['Defects',  'Discussion', 'Tasks', 'TestCases', 'Attachments','Projects', 'Children', 'TestCases']
    
    # routing is used to dispatch to handler function based on tag 
    handler_routing = {'Discussion':conversation_handler, 'Attachments':attachment_handler, 'TestCases':default_handler, 'Defects':defect_handler, 'Tasks':tasks_handler}
    
    details = {}
    for c in us_element.getchildren():
        if c.tag == 'Owner' and c.attrib['refObjectName']:
            details[c.tag] = c.attrib['refObjectName']
            
        if c.tag in simple_elements:
            if non_blank_element(c.text):
                details[c.tag] = c.text
        elif c.tag in  complex_elements:
         
            try:
                child_num = c.find('Count')
                if  child_num is None: 
                    continue
                elif child_num.text <> '0':
                    # if have of list of items stored in _itemRefArray, based on the element type, route to handler functions.  
                    if c.find('_itemRefArray'):
                        array_html_line = handler_routing[c.tag](c)

                    details[c.tag] = ''.join(array_html_line)
            except KeyError:
                pass
        if c.tag == 'Tags':
            try:
                    child_c = c.find('Count')
                    if child_c.text <> '0':
                        tag_list =[]
                        my_tags = c.find('_tagsNameArray')
                        for my_tag in my_tags:
                            x = my_tag.find('Name').text
                            tag_list.append(x)
                        details['Tags'] = ','.join(tag_list)
            except KeyError:
                pass
                
    return details

def parse_xml(fullpath, indexf):
    
    LINE_CAP = 30
    lc = 0
    xf = xt.parse(fullpath)
    
    output_dir = os.path.dirname(fullpath)
    
    for i in xf.getroot().getchildren():
        if lc >= LINE_CAP:
            break
        else:
            details = get_story_details(i)
            detail_page_name = './' + details['ObjectID'] + '.html'
            line =  '<p> <a href="{}"> {}</a>: {}, {}, {} </p>'.format(detail_page_name, details['FormattedID'], i.attrib['refObjectName'], details['c_ECommKanbanState'], i.attrib['CreatedAt'])
            indexf.writelines(line)
            print line
            generate_detail_page(details, output_dir)
            lc += 1

if __name__ == '__main__':
    
    ROOT_DIR = os.path.expanduser('~/Downloads/rally_dump')
    
    
    html_header = '<!DOCTYPE html> \
    <html><head><title>Platform Team User Stories </title> <link rel="stylesheet" href="css/bootstrap.min.css"> </head>\
    <body><p class="title"><b>Platform team User Stories</b></p>'
   
    filename = 'Rally-Stories.xml'
    index_file = open(os.path.join(ROOT_DIR, 'index.html'),'wt')
    index_file.write(html_header)
    xml_path = os.path.join(ROOT_DIR, filename)
    
    parse_xml(xml_path, index_file)
    
    index_file.close()
    '''
    download_defect_details()
    '''