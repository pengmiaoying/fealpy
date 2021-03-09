import numpy as np

from .Mesh3d import Mesh3d, Mesh3dDataStructure

from ..quadrature import GaussLegendreQuadrature, TriangleQuadrature
from ..quadrature import TensorProductQuadrature

# 单纯形网格的多重指标矩阵
from .core import multi_index_matrix
# 单纯形网格的拉格朗日形函数
from .core import lagrange_shape_function
# 单纯形网格拉格朗日形函数关于重心坐标函数的导数
from .core import lagrange_grad_shape_function

from .core import LinearMeshDataStructure

class LinearWedgeMeshDataStructure():

    def __init__(self, mesh, nh, p):
        cell = mesh.entity('cell')
        node = mesh.entity('node')
        edge = mesh.entity('edge')

        NN = mesh.number_of_nodes()
        NC = mesh.number_of_cells()
        NE = mesh.number_of_edges()

        self.itype = mesh.itype

        #构造单元
        I = NN*p*np.tile(np.arange(nh), (NC, 1)).T.flatten()#多层单元
        self.cell = np.zeros([NC*nh, cell.shape[-1]*(p+1)], dtype = cell.dtype)
        self.cell[:, ::p+1] = (np.tile(cell, (nh, 1)).T+I).T
        for i in range(p+1):
            self.cell[:, i::p+1] = self.cell[:, ::p+1]+NN*i
        
        #构建面
        self.face = np.r_[self.cell[:, ::p+1], self.cell[-NC:, p::p+1]]
        self.cell2face = np.c_[np.arange(NC*nh), np.arange(NC, NC*(nh+1))]
        self.face2cell = np.zeros([NC*(nh+1), 2])
        self.face2cell[:, 0] = np.r_[np.arange(NC*nh), np.arange(NC*(nh-1), NC*nh)]
        self.face2cell[:, 1] = np.r_[np.arange(NC), np.arange(NC*nh)]

        #构建边
        I = NN*p*np.tile(np.arange(nh+1), (NE, 1)).T.flatten()
        self.edge = (np.tile(edge, (nh+1, 1)).T+I).T
        
        face2edge = mesh.ds.cell_to_edge()
        I = NE*np.tile(np.arange(nh), (NC, 1)).T.flatten()
        self.cell2edge = np.zeros((NC*nh, 6), dtype = cell.dtype)
        self.cell2edge[:, ::2] = (np.tile(face2edge, (nh, 1)).T+I).T
        self.cell2edge[:, 1::2] = self.cell2edge[:, ::2]+NE
 
        self.face2edge = np.r_[self.cell2edge[:, ::2], self.cell2edge[-NC:, ::2]]
        self.NF = len(self.face)
        self.NN = NN*(nh+1)
        self.NC = NC*nh
        self.NE = NE*(nh+1)
        
class LagrangeWedgeMesh(Mesh3d):
    def __init__(self, mesh, h, nh, p=1, surface=None):

        cell = mesh.entity('cell')
        node = mesh.entity('node')
        edge = mesh.entity('edge')

        self.p = p
        self.h = h

        self.GD = node.shape[1]
        self.TD = 3
        self.ftype = node.dtype
        self.itype = cell.dtype
        self.meshtype = 'lwedge'

        self.surface = surface

        self.ds = LinearWedgeMeshDataStructure(mesh, nh, p) # 线性网格的数据结构
        self.node = self.construct(node, cell, h, nh)

        nc = len(cell)
        NF = self.ds.NF
        self.is_boundary_face = np.zeros(NF, dtype=np.bool_)
        self.is_boundary_face[:nc] = True
        self.is_boundary_face[-nc:] = True

        self.nodedata = {}
        self.edgedata = {}
        self.celldata = {}
        self.multi_index_matrix = multi_index_matrix

    def construct(self, node, cell, h, nh):
        p = self.p
        h = self.h
        v0 = node[cell[:, -1]] - node[cell[:, 0]]
        v1 = node[cell[:, 1]] - node[cell[:, 0]]

        n = np.cross(v1, v0)#每个单元的法向量
        n = (n.T/np.linalg.norm(n, axis=-1)).T#单位化法向量       

        node2n = np.zeros([len(node), 3])
        a = cell.shape[-1]
        np.add.at(node2n, cell.reshape(-1), np.tile(n, (1, a)).reshape(-1, 3))
        node2n = (node2n.T/np.linalg.norm(node2n, axis=-1)).T

        h = np.linspace(0, h, nh*p+1)
        NN = len(node)
        for i in range(nh*p):
                node = np.r_[node, node[:NN]+h[i+1]*node2n]

        return node
    
    def reference_cell_measure(self):
        return 0.5

    def number_of_corner_nodes(self):
        """
        Notes
        -----

        拉格朗日三角形网格中的节点分为单元角点节点, 边内部节节点和单元内部节点.

        这些节点默认的编号顺序也是: 角点节点, 边内部节点, 单元内部节点.

        该函数返回角点节点的个数.
        """
        return self.ds.NCN

    def integrator(self, k, etype='cell'):
        qf0 = TriangleQuadrature(k)
        qf1 = GaussLegendreQuadrature(k)
        if etype in {'cell', 3}:
            return TensorProductQuadrature((qf0, qf1)) 
        elif etype in {'face', 2}:
            return qf0 
        elif etype in {'edge', 1}:
            return qf1 

    def entity_barycenter(self, etype=3, index=np.s_[:]):
        GD = self.geo_dimension()
        if etype in {'cell', 3}:
            qf = self.integrator(1, etype=3)
            bc, ws = qf.get_quadrature_points_and_weights()
            p = self.bc_to_point(bc, index=index).reshape(-1, GD)
        elif etype in {'face', 2}:
            qf = self.integrator(1, etype=2)
            bcs, ws = qf.get_quadrature_points_and_weights()
            p = self.bc_to_point(bc, index=index, etype='face').reshape(-1, GD)
        elif etype in {'edge', 1}:
            qf = self.integrator(1, etype=1)
            bc, ws = qf.get_quadrature_points_and_weights()
            p = self.bc_to_point(bc, index=index, etype='edge').reshape(-1, GD)
        elif etype in {'node', 0}:
            p = node[index]
        else:
            raise ValueError('the entity `{}` is not correct!'.format(entity)) 
        return p 

    def lagrange_dof(self, p, spacetype='C'):
        if spacetype == 'C':
            return CLagrangeWedgeDof2d(self, p)
        elif spacetype == 'D':
            return DLagrangeWedgeDof2d(self, p)
    
    def cell_volume(self, q=None, index=None):
        """
        
        Notes
        -----
        计算单元体积
        """
        p = self.p
        q = p if q is None else q

        qf = self.integrator(q)
        bcs, ws = qf.get_quadrature_points_and_weights()
        G = self.first_fundamental_form(bcs)
        l = np.sqrt(np.linalg.det(G))
        vol = 0.5*np.einsum('i, ij->j', ws, l)
        return vol

    def edge_length(self, q=None, index=np.s_[:]):
        """

        Note
        ----
        计算边的长度
        """
        p = self.p
        q = p if q is None else q

        qf = self.integrator(q, etype='edge')
        bcs, ws = qf.get_quadrature_points_and_weights()

        J = self.jacobi_matrix(bcs, index=index, etype='edge')
        l = np.sqrt(np.sum(J**2, axis=(-1, -2))).reshape(1,-1)
        a = np.einsum('i, ij->j', ws, l)
        return a
    
    def face_area(self, q=None, index=np.s_[:]):
        """

        Notes
        -----
        计算单元的面积.
        """
        p = self.p
        q = p if q is None else q

        qf = self.integrator(q, etype='face')

        # 三角形面积
        bcs, ws = qf.get_quadrature_points_and_weights()
        J = self.jacobi_matrix(bcs, index=index, etype='face')
        n = np.cross(J[..., 0], J[..., 1], axis=-1)
        n = np.sqrt(np.sum(n**2, axis=-1)).reshape(1,-1)
        a = np.einsum('i, ij->j', ws, n)/2.0
        return a

    def jacobi_matrix(self, bc, index=np.s_[:], etype='cell', return_grad=False):
        """
        Notes
        -----
        计算参考单元 （xi, eta, zeta) 到实际 Lagrange 三棱柱 (x) 之间映射的
        Jacobi 矩阵.

        """

        node = self.entity('node')
        cell = self.entity('cell')
        edge = self.entity('edge')
        face = self.entity('face')
        if etype in {'cell', 3}:
            gphi = self.grad_shape_function(bc)
            J = np.einsum(
                    'ijn, ...ijk->...ink', node[cell], gphi)
        elif etype in {'face', 2}:
            gphi = self.grad_shape_function(bc, etype='face')
            J = np.einsum(
                    'ijn, ...ijk->...ink', node[face], gphi)
        elif etype in {'edge', 1}:
            gphi = self.grad_shape_function(bc, etype='edge')
            J = np.einsum(
                    'ijn, ...ijk->...ink', node[edge], gphi)
        else:
            raise ValueError('the jacobi_matrix `{}` is not correct!'.format(entity)) 
        
        shape = (-1, ) + J.shape[-3:]
        if return_grad is False:
            return J
        else:
            return J, gphi

    def bc_to_point(self, bc, index=np.s_[:], etype='cell'):
        node = self.entity('node')
        cell = self.entity('cell')
        edge = self.entity('edge')
        face = self.entity('face')
        phi = self.shape_function(bc)
        
        if etype in {'cell', 3}:
            p = np.einsum('...jk, jkn->...jn', phi, node[cell])
        elif etype in {'face', 2}:
            p = np.einsum('...jk, jkn->...jn', phi, node[face])
        elif etype in {'edge', 1}:
            p = np.einsum('...jk, jkn->...jn', phi, node[edge])
        else:
            raise ValueError('the bc_to_point `{}` is not correct!'.format(entity)) 
        return p

    def shape_function(self, bc, p=None):
        p = self.p if p is None else p

        TD = len(bc)
        if TD == 1:
            phi = lagrange_shape_function(bc, p)
            shape = phi.shape[:-1] + (-1, )
        elif TD == 2:
            phi0 = lagrange_shape_function(bc[0], p)
            phi1 = lagrange_shape_function(bc[1], p)
            # i 是积分点
            # j 是单元
            # m 是基函数
            phi = np.einsum('im, kn->ikmn', phi0, phi1)
            shape = phi.shape[:-2] + (-1, )
        phi = phi.reshape(shape) # 展平自由度
        shape = (-1, 1) + phi.shape[-1:] # 增加一个单元轴，方便广播运算
        phi = phi.reshape(shape) # 展平积分点
        return phi 


    def grad_shape_function(self, bc, p=None, index=np.s_[:],
            etype='cell', variables='u'):
        """

        Notes
        -----
        计算单元形函数关于参考单元变量 u=(xi, eta, zeta) 或者实际变量 x 梯度.
        lambda_0 = 1 - xi
        lambda_1 = xi

        lambda_2 = 1 - eta - zeta
        lambda_3 = eta
        lambda_4 = zeta

        """
        p = self.p if p is None else p

        Dlambda0 = np.array([[-1, -1], [1, 0], [0, 1]], dtype=self.ftype)
        Dlambda1 = np.array([[-1], [1]], dtype=self.ftype)

        if etype in {'cell', 3}:
            phi0 = lagrange_shape_function(bc[0], p)
            phi1 = lagrange_shape_function(bc[1], p)

            R0 = lagrange_grad_shape_function(bc[0], p)
            R1 = lagrange_grad_shape_function(bc[1], p)

            gphi0 = np.einsum('...ij, jn->...in', R0, Dlambda0) # (..., ldof, 1)
            gphi1 = np.einsum('...ij, jn->...in', R1, Dlambda1) # (..., ldof, 2)

            Gphi0 = np.einsum('imt, kn->ikmnt', gphi0, phi1)
            Gphi1 = np.einsum('kn, imt->kinm', phi0, gphi1)
            n = Gphi0.shape[0]*Gphi0.shape[1]
            shape = (n, (p+1)*(p+1)*(p+2)//2, 3)
            gphi = np.zeros(shape, dtype=self.ftype)
            gphi[..., 0:2].flat = Gphi0.flat
            gphi[..., -1].flat = Gphi1.flat
        elif etype in {'face', 2}:
            R = lagrange_grad_shape_function(bc, p)
            gphi = np.einsum('...ij, jn->...in', R, Dlambda0) # (..., ldof, 1)
        elif etype in {'edge', 1}:
            R = lagrange_grad_shape_function(bc, p)
            gphi = np.einsum('...ij, jn->...in', R, Dlambda1) # (..., ldof, 1)
        else:
            raise ValueError('the grad_shape_function `{}` is not correct!'.format(entity)) 

        if variables == 'u':
            return gphi[..., None, :, :] #(..., 1, ldof, 3) 增加一个单元轴
        elif variables == 'x':
            G, J = self.first_fundamental_form(bc, index=index,
                    return_jacobi=True)
            G = np.linalg.inv(G)
            gphi = np.einsum('...ikm, ...imn, ...ln->...ilk', J, G, gphi)
            return gphi
    
    def first_fundamental_form(self, bc, index=np.s_[:], return_jacobi=False, 
            return_grad=False):
        """
        Notes
        -----
            计算拉格朗日网格在积分点处的第一基本形式。
        """

        TD = 3
        J = self.jacobi_matrix(bc, index=index,
                return_grad=return_grad)
        
        if return_grad:
            J, gphi = J

        shape = J.shape[0:-2] + (TD, TD)
        G = np.zeros(shape, dtype=self.ftype)
        for i in range(TD):
            G[..., i, i] = np.sum(J[..., i]**2, axis=-1)
            for j in range(i+1, TD):
                G[..., i, j] = np.sum(J[..., i]*J[..., j], axis=-1)
                G[..., j, i] = G[..., i, j]
        if (return_jacobi is False) & (return_grad is False):
            return G
        elif (return_jacobi is True) & (return_grad is False): 
            return G, J
        elif (return_jacobi is False) & (return_grad is True): 
            return G, gphi 
        else:
            return G, J, gphi

    def vtk_cell_type(self, etype='cell'):
        """

        Notes
        -----
            返回网格单元对应的 vtk 类型。
        """
        if etype in {'cell', 3}:
            VTK_LAGRANGE_WEDGE = 73
            return VTK_LAGRANGE_WEDGE
        elif etype in {'face', 2}:
            VTK_LAGRANGE_QUADRILATERAL = 70
            VTK_LAGRANGE_TRIANGLE = 69
            return VTK_LAGRANGE_TRIANGLE, VTK_LAGRANGE_QUADRILATERAL
        elif etype in {'edge', 1}:
            VTK_LAGRANGE_CURVE = 68
            return VTK_LAGRANGE_CURVE

    def to_vtk(self, etype='cell', index=np.s_[:], fname=None):
        """
        Parameters
        ----------

        Notes
        -----
        把网格转化为 VTK 的格式
        """
        from .vtk_extent import vtk_cell_index, write_to_vtu

        node = self.entity('node')
        GD = self.geo_dimension()
        if GD == 2:
            node = np.concatenate((node, np.zeros((node.shape[0], 1), dtype=self.ftype)), axis=1)

        cell = self.entity(etype)[index]
        cellType = self.vtk_cell_type(etype)
        idx = vtk_cell_index(self.p, cellType) # 转化为 vtk 编号顺序
        NV = cell.shape[-1]

        cell = np.r_['1', np.zeros((len(cell), 1), dtype=cell.dtype), cell[:, idx]]
        # 这里cell的编号顺序与vtk默认顺序一致
        cell[:, 0] = NV

        NC = len(cell)
        if fname is None:
            return node, cell.flatten(), cellType, NC 
        else:
            print("Writting to vtk...")
            write_to_vtu(fname, node, NC, cellType, cell.flatten(),
                    nodedata=self.nodedata,
                    celldata=self.celldata)
    
class CLagrangeWedgeDof2d():
    """

    Notes
    -----
    拉格朗日三棱柱网格上的自由度管理类。
    """
    def __init__(self, mesh, p):
        self.mesh = mesh
        self.p = p
        self.itype = mesh.itype
        self.ftype = mesh.ftype

    def is_boundary_dof(self, threshold=None):
        if type(threshold) is np.ndarray:
            index = threshold
        else:
            index = np.where(self.mesh.is_boundary_face)[0]
            if callable(threshold):
                bc = self.mesh.entity_barycenter('face', index=index)
                flag = threshold(bc)
                index = index[flag]

        gdof = self.number_of_global_dofs()
        face2dof = self.face_to_dof()
        isBdDof = np.zeros(gdof, dtype=np.bool)
        isBdDof[face2dof[index]] = True
        node = self.mesh.entity('node')
        return isBdDof

    def edge_to_dof(self):
        """

        TODO
        ----
        1. 只取一部分边上的自由度
        """
        p = self.p
        mesh = self.mesh
        edge = mesh.entity('edge')

        if p == mesh.p:
            return edge

        NN = mesh.number_of_corner_nodes()
        NE = mesh.number_of_edges()
        edge2dof = np.zeros((NE, p+1), dtype=np.int)
        edge2dof[:, [0, -1]] = edge[:, [0, -1]] # edge 可以是高次曲线
        if p > 1:
            NN = mesh.number_of_corner_nodes() # 注意这里只是单元角点的个数
            NE = mesh.number_of_edges()
            edge2dof[:, 1:-1] = NN + np.arange(NE*(p-1)).reshape(NE, p-1)
        return edge2dof


    @property
    def edge2dof(self):
        return self.edge_to_dof()

    @property
    def face2dof(self):
        return self.face_to_dof()

    def face_to_dof(self):
        """

        TODO
        ----
        1. 只取一部分面上的自由度
        """
        p = self.p
        mesh = self.mesh
        face = mesh.entity('face')

        if p == mesh.p:
            return face
        else:
            pass

    @property
    def cell2dof(self):
        """
        
        Notes
        -----
            把这个方法属性化，保证程序接口兼容性
        """
        return self.cell_to_dof()


    def cell_to_dof(self):
        """

        TODO
        ----
        1. 只取一部分单元上的自由度。
        2. 用更高效的方式来生成单元自由度数组。
        """

        p = self.p
        mesh = self.mesh
        cell = mesh.entity('cell') # cell 可以是高次单元
        if p == mesh.p:
            return cell 
        else:
            pass


    def interpolation_points(self):
        p = self.p
        mesh = self.mesh
        cell = mesh.entity('cell')
        node = mesh.entity('node')
        if p == mesh.p:
            return node
        
        NC = mesh.number_of_cells()
        cell2dof = self.cell_to_dof()
        GD = mesh.geo_dimension()
        gdof = self.number_of_global_dofs()
        ipoint = np.zeros((gdof, GD), dtype=np.float64)
        bc0 = multi_index_matrix[0](p)/p
        bc1 = multi_index_matrix[1](p)/p
        ipoint[cell2dof] = mesh.bc_to_point((bc0, bc1)).reshape(-1, NC,
                GD).swapaxes(0, 1)
        return ipoint

    def number_of_global_dofs(self):
        p = self.p
        mesh = self.mesh

        if p == mesh.p:
            return mesh.number_of_nodes()
        else:
            pass

    def number_of_local_dofs(self, doftype='cell'):
        p = self.p
        if doftype in {'cell', 3}:
            return (p+1)*(p+1)*(p+1)//2
        elif doftype in {'face',  2}:
            return (p+1)*(p+2)//2
        elif doftype in {'edge',  1}:
            return p + 1
        elif doftype in {'node', 0}:
            return 1

class DLagrangeQuadrangleDof2d():
    """

    Notes
    -----
    拉格朗日三棱柱网格上的自由度管理类。
    """
    def __init__(self, mesh, p):
        self.mesh = mesh
        self.p = p
        self.itype = mesh.itype
        self.ftype = mesh.ftype

    @property
    def face2dof(self):
        return None 

    def face_to_dof(self):
        return None 

    @property
    def edge2dof(self):
        return None 

    def edge_to_dof(self):
        """

        TODO
        ----
        1. 只取一部分边上的自由度
        """
        return None

    @property
    def cell2dof(self):
        """
        
        Notes
        -----
            把这个方法属性化，保证程序接口兼容性
        """
        return self.cell_to_dof()


    def cell_to_dof(self):
        """

        TODO
        ----
        1. 只取一部分单元上的自由度。
        2. 用更高效的方式来生成单元自由度数组。
        """

        p = self.p
        NC = self.mesh.number_of_cells()
        cell2dof = np.arange(NC*(p+1)*(p+1)*(p+2)//2).reshape(NC,
                (p+1)*(p+1)*(p+2)//2)
        return cell2dof

    def interpolation_points(self):
        p = self.p
        mesh = self.mesh
        cell = mesh.entity('cell')
        node = mesh.entity('node')

        NC = mesh.number_of_cells()
        GD = mesh.geo_dimension()
        bc0 = multi_index_matrix[2](p)/p
        bc1 = multi_index_matrix[1](p)/p
        ipoint = mesh.bc_to_point((bc0, bc1)).reshape(-1, NC,
                GD).swapaxes(0, 1).reshape(-1, GD)
        return ipoint

    def number_of_global_dofs(self):
        p = self.p
        mesh = self.mesh
        NC = mesh.number_of_cells()
        return NC*(p+1)*(p+1)*(p+2)//2

    def number_of_local_dofs(self, doftype='cell'):
        p = self.p
        if doftype in {'cell', 3}:
            return (p+1)*(p+1)*(p+2)//2
        elif doftype in {'face', 2}:
            return (p+1)*(p+2)//2
        elif doftype in {'edge',  1}:
            return p + 1
        elif doftype in {'node', 0}:
            return 1
