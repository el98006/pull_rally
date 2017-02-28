'''
Created on Feb 16, 2017

@author: eli
'''

import time
from functools import wraps
import logging
import urllib2


MAX_RETRIES = 5
POOL_SIZE = 5

def retry_on_exception(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        my_logger = init_logging(logging.INFO,'root')
        num_retries = 0
        ret = None 
        while num_retries < MAX_RETRIES:
            try:
                ret = func(*args, **kwargs)
                break
            except urllib2.HTTPError as e:
                if num_retries < MAX_RETRIES:
                    time.sleep(50)
                    ret = func(*args, **kwargs)
                    num_retries += 1
                else:
                    print 'maxed out HTTPError retries'
            except urllib2.URLError as e:
                if num_retries < MAX_RETRIES:
                    time.sleep(50)
                    ret = func(*args, **kwargs)
                    my_logger(logging.INFO, 'retry exception {}'.format(e.code))
                else:
                    print 'maxed out retries'
                num_retries += 1    
            except:
                print "unhandled error" 
                my_logger.log(logging.INFO, 'unhandled error')  
                num_retries += 1 
                 
        return ret
    
    return wrapper 

def init_logging(level=logging.ERROR, mod_name = 'root'):
    logger = logging.getLogger(mod_name)
    logger.setLevel(level)
    
    fh = logging.FileHandler('pull_rally.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger
    

        