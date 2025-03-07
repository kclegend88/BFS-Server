# -*- coding: utf-8 -*-
import re

def barcode_formatcheck(str_barcode,re_exp):
    res = re.search(re_exp,str_barcode)
    print(" checking re_exp=%s,barcode=%s,result = %s"%(re_exp,str_barcode,res))
    if res:
        return True
    else:
        return False

def barcode_formatcheck_bylst(str_barcode,lst_re_exp):
    for i,re_exp in enumerate(lst_re_exp):
        res = re.search(re_exp,str_barcode)
        print(" checking re_exp=%s,barcode=%s,result = %s"%(re_exp,str_barcode,res))
        if res:
            return True
    return False

def barcode_existingcheck(str_barcode,set_barcode):
    if str_barcode in set_barcode:
        print(f"Barcode {str_barcode} belong to current set" )
        return True
    print(f"Barcode {str_barcode} NOT belong to current set")
    return False