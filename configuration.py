from collections import namedtuple

config = {
        "mode":'LP', #or 'MIP'
        "margin":False,
        "load_priority":True,
        "th_value":0.003,
        "alpha":0.8,
        "Obj_tol":0.00001,
        "SL_tol":0.00001,
        "PctOf_SL_full_Target":1,
        "wt_minUObj":0.2
}

CONFIG = namedtuple("CONFIG",config.keys())(**config)

