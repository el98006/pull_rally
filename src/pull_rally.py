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
BASE_URL = ''
UNAME = ''
PASS = ''

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
    '''install the open, so all the future urllib.urlopen urlib2.request will base on this opener'''


def write_detail_line(fh, details):
    skip_list = ['FormattedID', 'ObjectID', 'Name']
    field_name_mapping = {'c_ECommKanbanState':'State', 'c_ReleaseDate':'ReleaseDate', 'c_RT':'RT'}
    for k in details:
        if k in skip_list:
            continue
        if k in field_name_mapping:
            n = field_name_mapping[k]
        else:
            n = k
        line = '<p> <h2>{}: </h2>{} </p>'.format(n, details[k])
        fh.writelines(line)
        
def generate_detail_page(details, out_dir):
    if details['ObjectID']:
        fname = details['ObjectID']
    else:
        fname = 'dummy'
    fp = os.path.join(out_dir,fname+'.html')
        
    with open(fp, 'wt') as fh:
        title = details['FormattedID'] + ':' + details['Name']
        line = '<html><head><title> {} </title></head><body><p class="title"><h1> {}</h1></p>'.format(title,title )
        fh.writelines(line)
        
        write_detail_line(fh, details)
        
        fh.writelines('</body></html>')

def get_us_details(us_element):
    simple_elements = ['ObjectID','FormattedID','Name','Description', 'Notes','DirectChildrenCount', 'HasParent', 'c_ECommKanbanState', 'c_ReleaseDate','c_RT','c_ReleasePlan']
    complex_elements = ['Defects',  'Discussion', 'Tasks', 'TestCases', 'Attachments','Projects', 'Children', 'TestCases']
    
    # routing is used to dispatch to handler function based on tag 
    routing = {'Discussion':conversation_handler, 'Attachments':attachment_handler, 'TestCases':default_handler, 'Defects':default_handler, 'Tasks':tasks_handler}
    
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
                    if c.find('_itemRefArray'):
                        array_html_line = routing[c.tag](c)
                        '''
                            try:
                                array_list.append( '<p>' + a_item.attrib['refObjectName'] + ' , ' + a_item.attrib['ref'] + '</p>')
                            except KeyError:
                        '''
                            
                                #array_list.append( '<p>'   + a_item.attrib['ref'] + '</p>')
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
            details = get_us_details(i)
            detail_page_name = './' + details['ObjectID'] + '.html'
            line =  '<p> <a href="{}"> {}</a>: {}, {} </p>'.format(detail_page_name, details['FormattedID'], i.attrib['refObjectName'], i.attrib['CreatedAt'])
            indexf.writelines(line)
            print details.items()
            generate_detail_page(details, output_dir)
            lc += 1

def parse_posts(json_payload):
    root = json.loads(json_payload)
    p_text = root.get('ConversationPost').get('Text')
    p_user = root.get('ConversationPost').get('User').get('_refObjectName')
    p_timestamp = root.get('ConversationPost').get('CreationDate')
    
    
    result = ' <p><b> {} </b> at {} </p> <p> {} </p>'.format( p_user, p_timestamp, p_text)    
    return result   

def conversation_handler(items):
    array_list = []
    authenticate_http()
    
    for item in items.find('_itemRefArray'):
        url_ref = item.attrib['ref']
        ret = urllib2.urlopen(url_ref)
        posts = ret.read()
        row = parse_posts(posts)
        array_list.append(row)
    return array_list
    
    

def tasks_handler(xml_component):
    array_list = ['<table>']
    for item in xml_component.find('_itemRefArray'):
        url = item.attrib['ref']
        ret = urllib2.urlopen(url)
        resp = ret.read()
        root = json.loads(resp)
        t_desc= root.get('Task').get('Name')
        t_timestamp = root.get('Task').get('CreationDate')
        t_owner = root.get('Task').get('Owner').get('_refObjectname')
        t_state = root.get('Task').get('State')
        t_index = root.get('Task').get('TaskIndex')
    
        row = '<tr> <td>{}</td> <td>{}</td> <td{}</td> <td>{}</td> <td> {}</td></tr>'.format(t_index,t_desc,t_timestamp, t_owner, t_state)
        array_list.append(row)
    array_list.append('</table>')
    array_list.sort()
    return array_list

def download_attachment(url=None):
    at_url = 'https://rally1.rallydev.com/slm/webservice/v2.x/attachment/42162299667'
    #content_url = 'https://rally1.rallydev.com/slm/webservice/v2.x/attachmentcontent/42162299668'
    
    authenticate_http()
    ret = urllib2.urlopen(at_url)
    resp = ret.read()
    root = json.loads(resp)
    t_creation_date = root.get('Attachment').get('CreationDate')
    t_id = root.get('Attachment').get('ObjectID')
    t_content_url = root.get('Attachment').get('Content').get('_ref')
    #t_content_name = root.get('Attachment').get('Name').encode('utf-8')
    t_content_name = unicode(root.get('Attachment').get('Name'))

    t_length = int(root.get('Attachment').get('Size'))
   
    row = '{} {}'.format(t_content_url, str(t_id) )    
  
    
    t_path = os.path.join(ROOT_DIR,'Attachment')
    if os.path.exists(t_path) is False:
        os.mkdir(t_path)
    t_path = os.path.join(t_path, str(t_id))
    if os.path.exists(t_path) is False:
        os.mkdir(t_path)
    
    #t_fullpath = os.path.join(t_path, t_content_name.encode('utf-8'))    
   
    t_fullpath = os.path.join(t_path, t_content_name)    
     
    req = urllib2.Request(t_content_url, headers={'User-Agent':'Mozilla/5.0'}, data=None)
    response = urllib2.urlopen(req)
    root = json.loads(response.read()) 
    with open(t_fullpath, 'wb') as fh:
        payload = root.get('AttachmentContent').get('Content')
        payload = payload.decode('base64')
        fh.write(payload)
    
    return t_content_name, t_id

def attachment_handler(xml_component):
    array_list = []
    for item in xml_component.find('_itemRefArray'):
        url = item.attrib['ref']
        t_content_name, tid = download_attachment(url)
        link = os.path.join('./Attachment', str(tid), t_content_name)
        line =  '<p> <a href="{}"> {} </a></p>'.format(link.encode('utf-8'), t_content_name.encode('utf-8'))
        array_list.append(line)
    return array_list
        
def default_handler(item):
    array_list = []
    for item in item.find('_itemRefArray'):
        url_ref = item.attrib['ref']
        array_list.append('<p>' + url_ref + '</p>')
    return array_list

if __name__ == '__main__':
    
    ROOT_DIR = os.path.expanduser('~/Downloads/rally_dump')
    

    html_header = '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en" class="bootstrap-CSS">'
   
    filename = 'Rally-Stories.xml'
    index_file = open(os.path.join(ROOT_DIR, 'index.html'),'wt')
    index_file.write(html_header)
    index_file.writelines('<html><head><title>Platform Team User Stories </title></head>\
    <body><p class="title"><b>Platform team User Stories</b></p>')
    xml_path = os.path.join(ROOT_DIR, filename)
    
    parse_xml(xml_path, index_file)
    
    index_file.close()
    '''
    download_attachment()
    '''