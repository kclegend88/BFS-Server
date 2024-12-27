# -*- coding: utf-8 -*-
import re

def barcode_formatcheck(str_barcode,re_exp):
    res = re.search(re_exp,str_barcode)
    print(" checking re_exp=%s,barcode=%s,result = %s"%(re_exp,str_barcode,res))
    if res:
        return True
    else:
        return False
