#!/usr/bin/python3
'''!    	
	@Author: wpx
	@File Name: possion.py
	@Mail: wpx15673207315@gmail.com 
	@Created Time: Wed 07 Aug 2024 10:14:18 AM CST
	@bref 
	@ref 
'''  
import argparse
from matplotlib import pyplot as plt

from fealpy.experimental import logger
logger.setLevel('WARNING')
from fealpy.experimental.mesh import TriangleMesh
from fealpy.experimental.mesh import QuadrangleMesh
from fealpy.experimental.functionspace import LagrangeFESpace
from fealpy.experimental.fem import BilinearForm, ScalarDiffusionIntegrator
from fealpy.experimental.fem import LinearForm, ScalarSourceIntegrator
from fealpy.experimental.fem import DirichletBC
from fealpy.experimental.backend import backend_manager as bm
from fealpy.experimental.sparse.linalg import sparse_cg
from fealpy.pde.poisson_2d import CosCosData 
from fealpy.utils import timer




## 参数解析
parser = argparse.ArgumentParser(description=
        """
        任意次有限元方法求解possion方程
        """)

parser.add_argument('--degree',
        default=1, type=int,
        help='Lagrange 有限元空间的次数, 默认为 1 次.')

parser.add_argument('--n',
        default=4, type=int,
        help='初始网格剖分段数.')

parser.add_argument('--maxit',
        default=2, type=int,
        help='默认网格加密求解的次数, 默认加密求解 4 次')

parser.add_argument('--backend',
        default='numpy', type=str,
        help='默认后端为numpy')

parser.add_argument('--meshtype',
        default='tri', type=str,
        help='默认网格为三角形网格')

args = parser.parse_args()


bm.set_backend(args.backend)
p = args.degree
n = args.n
meshtype = args.meshtype
maxit = args.maxit

tmr = timer()
next(tmr)
pde = CosCosData() 
if meshtype == 'tri':
    mesh = TriangleMesh.from_box([0,1,0,1], n, n)
elif meshtype == 'quad':
    mesh = QuadrangleMesh.from_box([0,1,0,1], n, n)
else: 
    raise ValueError(f"Unsupported : {meshtype} mesh")

errorType = ['$|| u - u_h||_{\\Omega,0}$']
errorMatrix = bm.zeros((1, maxit), dtype=bm.float64)
tmr.send('网格和pde生成时间')


for i in range(maxit):
    space= LagrangeFESpace(mesh, p=p)
    tmr.send(f'第{i}次空间时间') 

    bform = BilinearForm(space)
    bform.add_integrator(ScalarDiffusionIntegrator())
    lform = LinearForm(space)
    lform.add_integrator(ScalarSourceIntegrator(pde.source))
    
    A = bform.assembly()
    F = lform.assembly()
    tmr.send(f'第{i}次矩组装时间') 

    gdof = space.number_of_global_dofs()
    A, F = DirichletBC(space, gd = pde.solution).apply(A, F)
    tmr.send(f'第{i}次边界处理时间') 

    uh = sparse_cg(A, F, maxiter=5000, atol=1e-14, rtol=1e-14)
    tmr.send(f'第{i}次求解器时间') 
    
    value = space.value(uh, bm.array([[1/3, 1/3, 1/3]], dtype=bm.float64))
    real = space.interpolate(pde.solution) 
    errorMatrix[0, i] = bm.max(bm.abs(uh-real))
    
    if i < maxit-1:
        mesh.uniform_refine(n=1)
    tmr.send(f'第{i}次误差计算及网格加密时间') 
next(tmr)
print("最终误差",errorMatrix)


