import numpy as np
import pandas as pd
import scipy.optimize as opt
from scipy.sparse import csc_matrix
from typing import List, Dict, Tuple

from configuration import CONFIG

class TyingTheRope:
    def __init__(self, input_file_name:str, sl_target:float, max_round:int = 20, num_scenario: int = 1000):
        self.CONFIG = CONFIG
        self.sl_target = sl_target
        self.max_round = max_round
        self.num_scenario = num_scenario
        self.input_file_name = input_file_name

    def _load_input_file(self):
        
        pass

    
    class Result:
        def __init__(self, obj_value: float, x: List[float], y: List[float], dual_x: List[float], dual_y: List[float]):
            self.Obj_value = obj_value
            self.x = x
            self.y = y
            self.dual_x = dual_x
            self.dual_y = dual_y
    
    class Objective:
        def __init__(self, m: int, n: int, W_x: np.ndarray, W_y: np.ndarray, c: np.ndarray):
            self.m = m
            self.n = n
            self.W_x = W_x
            self.W_y = W_y
            self.c = c
        
        def func(self, z: List[float]) -> float:
            x = np.reshape(z[:self.m*self.n], (self.m, self.n))
            y = np.reshape(z[self.m*self.n:], (self.n, 1))
            return np.sum(np.multiply(self.W_x, x)) + np.sum(np.multiply(self.W_y, y)) + np.dot(self.c.T, x)
        
        def grad(self, z: List[float]) -> np.ndarray:
            x = np.reshape(z[:self.m*self.n], (self.m, self.n))
            y = np.reshape(z[self.m*self.n:], (self.n, 1))
            grad_x = self.W_x + self.c
            grad_y = self.W_y
            grad = np.concatenate((grad_x.flatten(), grad_y.flatten()))
            return grad
    
    class Constraint:
        def __init__(self, A: np.ndarray, b: np.ndarray):
            self.A = A
            self.b = b
        
        def func(self, z: List[float]) -> float:
            x = np.reshape(z[:self.A.shape[1]], (self.A.shape[1], 1))
            return np.dot(self.A, x) - self.b
        
        def jac(self, z: List[float]) -> np.ndarray:
            jac = np.concatenate((self.A, np.zeros((self.A.shape[0], 1))), axis=1)
            return csc_matrix(jac)
    
    class LP:
        def __init__(self, A: np.ndarray, b: np.ndarray, intcon: np.ndarray):
            self.A = A
            self.b = b
            self.intcon = intcon
    
    def PrepareLP(self, mat_name: str, q: int, rv_mean: np.ndarray) -> LP:
        M = len(self.Demand.product_list)
        N = self.Demand.mat_dict[mat_name].shape[0]
        Aeq = np.zeros((M+1, M*N+N+1))
        Aeq[0, 0:M*N] = 1
        Aeq[1:M+1, M*N:M*N+N] = np.eye(M)
        Aeq[1:M+1, -1] = -rv_mean[:, q]
        beq = np.zeros((M+1, 1))
        beq[0, 0] = np.sum(self.Demand.mat_dict[mat_name][:, q])
        beq[1:, 0] = self.Demand.rv_mean[:,
