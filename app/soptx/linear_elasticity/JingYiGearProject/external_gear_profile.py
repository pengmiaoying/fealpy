"""
外齿轮 15 个载荷点的算例
"""
from fealpy.backend import backend_manager as bm
from fealpy.mesh import HexahedronMesh
from fealpy.functionspace import LagrangeFESpace, TensorFunctionSpace
from fealpy.sparse import COOTensor
from fealpy.fem.linear_elastic_integrator import LinearElasticIntegrator
from fealpy.material.elastic_material import LinearElasticMaterial
from fealpy.fem.bilinear_form import BilinearForm
from fealpy.fem.dirichlet_bc import DirichletBC
from fealpy.solver import cg, spsolve

from soptx.utils import timer

from app.soptx.linear_elasticity.JingYiGearProject.utils import export_to_inp
from app.gearx.gear import ExternalGear, InternalGear
import json

def compute_strain_stress(tensor_space, uh, B_BBar, D):
    cell2tdof = tensor_space.cell_to_dof()
    cuh = uh[cell2tdof]  # (NC, TLDOF) 
    strain = bm.einsum('cqil, cl -> cqi', B_BBar, cuh) # (NC, NQ, 6)
    stress = bm.einsum('cqij, cqi -> cqj', D, strain)  # (NC, NQ, 6)
    
    return strain, stress

bm.set_backend('numpy')

with open('/home/heliang/FEALPy_Development/fealpy/app/soptx/linear_elasticity/JingYiGearProject/json/external_gear_data.json', 'r') \
        as file:data = json.load(file)
m_n = data['mn']  # 法向模数
z = data['z']  # 齿数
alpha_n = data['alpha_n']  # 法向压力角
beta = data['beta']  # 螺旋角
x_n = data['xn']  # 法向变位系数
hac = data['hac']  # 齿顶高系数
cc = data['cc']  # 顶隙系数
rcc = data['rcc']  # 刀尖圆弧半径
jn = data['jn']  # 法向侧隙
n1 = data['n1']  # 渐开线分段数
n2 = data['n2']  # 过渡曲线分段数
n3 = data['n3']
na = data['na']
nf = data['nf']
nw = data['nw']
tooth_width = data['tooth_width']
inner_diam = data['inner_diam']  # 轮缘内径
chamfer_dia = data['chamfer_dia']  # 倒角高度（直径）

external_gear = ExternalGear(m_n, z, alpha_n, beta, x_n, hac, cc, rcc, jn, n1, n2, n3, na, nf, nw, chamfer_dia,
                                inner_diam, tooth_width)
hex_mesh = external_gear.generate_hexahedron_mesh()
target_hex_mesh = external_gear.set_target_tooth([0, 1, 18])

hex_cell = target_hex_mesh.cell
hex_node = target_hex_mesh.node
# 寻找内圈上节点
node_r = bm.sqrt(hex_node[:, 0] ** 2 + hex_node[:, 1] ** 2)
is_inner_node = bm.abs(node_r - external_gear.inner_diam / 2) < 1e-11
inner_node_idx = bm.where(bm.abs(node_r - external_gear.inner_diam / 2)<1e-11)[0]
mesh = HexahedronMesh(hex_node, hex_cell)

GD = mesh.geo_dimension()   
NC = mesh.number_of_cells()
print(f"NC: {NC}")
NN = mesh.number_of_nodes()
print(f"NN: {NN}")
node = mesh.entity('node')
cell = mesh.entity('cell')

# 创建有限元空间
p = 1
q = 2
space = LagrangeFESpace(mesh, p=p, ctype='C')
sgdof = space.number_of_global_dofs()
print(f"sgdof: {sgdof}")
cell2dof = space.cell_to_dof()
tensor_space = TensorFunctionSpace(space, shape=(-1, 3)) # gd_priority
cell2tdof = tensor_space.cell_to_dof()
tgdof = tensor_space.number_of_global_dofs()
print(f"tgdof: {tgdof}")
tldof = tensor_space.number_of_local_dofs()

# 组装刚度矩阵
E = 206e3
nu = 0.3
lam = (E * nu) / ((1.0 + nu) * (1.0 - 2.0 * nu))
mu = E / (2.0 * (1.0 + nu))
linear_elastic_material = LinearElasticMaterial(name='E_nu', 
                                                elastic_modulus=E, poisson_ratio=nu, 
                                                hypo='3D', device=bm.get_device(mesh))
# B-Bar 修正的刚度矩阵
integrator_K = LinearElasticIntegrator(material=linear_elastic_material, 
                                       q=q, method='C3D8_BBar')
integrator_K.keep_data(True)
_, _, D, B_BBar = integrator_K.fetch_c3d8_bbar_assembly(tensor_space)
bform = BilinearForm(tensor_space)
bform.add_integrator(integrator_K)
K = bform.assembly(format='csr')

# 齿面上的节点索引和坐标
node_indices_tuple, noe_coord_tuple = external_gear.get_profile_node_index(tooth_tag=0)
node_indices_left = node_indices_tuple[0].reshape(-1, 1)
node_indices_right = node_indices_tuple[1].reshape(-1, 1)
node_indices = bm.concatenate([node_indices_left, node_indices_right], axis=0) # (NPN, 1)
node_coord_left = noe_coord_tuple[0].reshape(-1, 3)
node_coord_right = noe_coord_tuple[1].reshape(-1, 3)
node_coord = bm.concatenate([node_coord_left, node_coord_right], axis=0)       # (NPN, GD)
# 齿面上的节点数
NPN = node_indices.shape[0]
# TODO 齿面上节点的内法线方向 
face_normal = bm.ones((NPN, 3), bm.float64)
# 节点载荷值
load_values = 1000
# 所有节点的内法线载荷向量
P = load_values * face_normal  # (NPN, 3)
# 齿面上节点对应的全局自由度编号（跟顺序有关）
if tensor_space.dof_priority:
    dof_indices = bm.stack([sgdof * d + node_indices.reshape(-1) for d in range(GD)], axis=1) # (NPN, GD)
else:
    dof_indices = bm.stack([node_indices.reshape(-1) * GD + d for d in range(GD)], axis=1)    # (NPN, GD)
# inp 文件中需要的固定节点索引
fixed_node_index = bm.where(is_inner_node)[0]
# Dirichlet 边界条件
scalar_is_bd_dof = bm.zeros(sgdof, dtype=bm.bool)
scalar_is_bd_dof[:NN] = is_inner_node
tensor_is_bd_dof = tensor_space.is_boundary_dof(
                                threshold=(scalar_is_bd_dof, scalar_is_bd_dof, scalar_is_bd_dof), 
                                method='interp')
dbc = DirichletBC(space=tensor_space, 
                    gd=bm.zeros(tgdof), 
                    threshold=tensor_is_bd_dof, 
                    method='interp')
# 齿面上所有节点的位移结果
uh_profiles = bm.zeros((NPN, GD), dtype=bm.float64) # (NPN, GD)
for i in range(10):
    # 创建计时器
    t = timer(f"Timing_{i}")
    next(t)  # 启动计时器
    PP = P[i, :]
    # 全局载荷向量
    F = COOTensor(indices = bm.empty((1, 0), dtype=bm.int32, device=bm.get_device(space)),
                values = bm.empty((0, ), dtype=bm.float64, device=bm.get_device(space)),
                spshape = (tgdof, ))
    indices = dof_indices[i].reshape(1, -1)
    F = F.add(COOTensor(indices, PP.reshape(-1), (tgdof, ))).to_dense() # (tgdof, )
    # 处理 Dirichlet 边界条件
    K, F = dbc.apply(K, F)
    t.send('准备时间')
    # 计算位移
    from fealpy import logger
    logger.setLevel('INFO')
    uh = tensor_space.function()
    uh[:] = spsolve(K, F, solver="mumps")
    t.send('求解时间')
    # 获取齿面上节点的位移
    uh_profile = uh[dof_indices[i, :]]
    uh_profiles[i, :] = uh_profile
    # 计算残差向量和范数
    residual = K.matmul(uh[:]) - F  
    residual_norm = bm.sqrt(bm.sum(residual * residual))
    print(f"Final residual norm: {residual_norm:.6e}")
    t.send('后处理时间')
    t.send(None)
    if i == 0:
        # 保存单个节点的位移结果
        if tensor_space.dof_priority:
            uh_show = uh.reshape(GD, NN).T
        else:
            uh_show = uh.reshape(NN, GD)
        uh_magnitude = bm.linalg.norm(uh_show, axis=1)
        mesh.nodedata['uh'] = uh_show[:]
        mesh.nodedata['uh_magnitude'] = uh_magnitude[:]
        mesh.to_vtk('/home/heliang/FEALPy_Development/fealpy/app/soptx/linear_elasticity/JingYiGearProject/vtu/external_gear_profile_fealpy.vtu')

        # 单个节点载荷的索引
        load_node_indices = node_indices[i].reshape(-1) # (1, )
        # 从全局载荷向量中提取单个载荷节点处的值
        F_load_nodes = F[dof_indices[i, :].reshape(1, -1)] # (1, GD)
        export_to_inp(filename=f'/home/heliang/FEALPy_Development/fealpy/app/soptx/linear_elasticity/JingYiGearProject/inp/external_gear_profile_abaqus_{i}.inp', 
                    nodes=node, elements=cell, 
                    fixed_nodes=fixed_node_index, load_nodes=load_node_indices, loads=F_load_nodes, 
                    young_modulus=206e3, poisson_ratio=0.3, density=7.85e-9, 
                    used_app='abaqus', mesh_type='hex')
# 计算齿面上节点的内法线方向位移
uh_normal = bm.sum(uh_profiles * face_normal, axis=1) # (NPN, )
print("-----------")