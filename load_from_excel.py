import pandas as pd
import os
from collections import namedtuple

def f_load_input_file(input_file_name):
    
    version_name = os.path.splitext(os.path.basename(input_file_name))[0]
    file_path = os.path.join("./inputs",input_file_name) 
    output_dir = os.path.join('./outputs', version_name)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
        

    paths = {
        'output': output_dir,
        'input': file_path,
        'input_file_name': input_file_name
    }
    
    BasicInfo = pd.read_excel(paths["input"], sheet_name='BasicInfo')
    product = BasicInfo['Product'].tolist()
    site = BasicInfo['Site'].tolist()
    quarter = BasicInfo['Quarter'].tolist()
    BasicInfo = {'product': product, 'site': site, 'quarter': quarter}

    priority_weight = pd.read_excel(paths["input"], sheet_name='Priority')
    cost_matrix = pd.read_excel(paths["input"], sheet_name='Cost')
    sht_demand = pd.read_excel(paths["input"], sheet_name='Demand')
    sht_site = pd.read_excel(paths["input"], sheet_name='Site')
    Qmat_base = pd.read_excel(paths["input"], sheet_name='BaseQual')
    Qmat_plan = pd.read_excel(paths["input"], sheet_name='PlanQual')
    Qmat_max = pd.read_excel(paths["input"], sheet_name='MaxQual')
    Rmat = pd.read_excel(paths["input"], sheet_name='Exclusions')
    
    if (Qmat_base.shape == Rmat.shape) and (Qmat_plan.shape == Rmat.shape) and (Qmat_max.shape == Rmat.shape):
        Qmat = {'base': Qmat_base, 'plan': Qmat_plan, 'max': Qmat_max, 'exclusion': Rmat}
    else:
        raise ValueError('Inconsistent matrix found! Please check all input matrix')

    n = sht_demand.shape[0] #number of products
    m = sht_site.shape[0] #num of sites
    numQuarter = sht_demand.shape[1] - 3  #num of quarters
    numOptions = (Rmat[Rmat==0].shape[0]) + (Rmat[Rmat==2].shape[0]) #number of options can be added into qual structure

    Pars = {'num_prod': n, 'num_site': m, 'num_quarter': numQuarter, 'num_option': numOptions}
    
    D_mu = sht_demand.iloc[:,3:] #avg demand
    D_bias = D_mu.mul(sht_demand.iloc[:, 0], axis=0) #fcst bias
    D_mu_Adj = D_mu.sub(D_bias) #unbiased
    D_sig = D_mu.mul(sht_demand.iloc[:, 1], axis=0) #sigma of fcst error
    D_mar = sht_demand.iloc[:, 2] #demand margin (placeholder)

    Demand = {'fcst': D_mu, 'bias': D_bias, 'rv_mean': D_mu_Adj, 'rv_std': D_sig, 'margin': D_mar}
    Capacity = sht_site.iloc[:,1:] 
    MinUtil = sht_site.iloc[:,0] 

    MF = namedtuple(
        "MF",
        (
            "BasicInfo",
            "Pars",
            "Qmat",
            "paths",
            "Demand",
            "MinUtil",
            "Capacity",
            "priority_weight",
            "cost_matrix"
        )
    )(
        BasicInfo,
        Pars,
        Qmat,
        paths,
        Demand,
        MinUtil,
        Capacity,
        priority_weight,
        cost_matrix
    )
    return MF