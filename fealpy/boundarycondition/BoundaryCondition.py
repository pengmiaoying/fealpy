import numpy as np
from scipy.sparse import coo_matrix, csc_matrix, csr_matrix, spdiags, eye

class BoundaryCondition():

    def __init__(self, space, dirichlet=None, neuman=None, robin=None):
        self.space = space
        self.dirichlet = dirichlet
        self.neuman = neuman
        self.robin = robin

    def apply_neuman_bc(self, b, dim=None, is_neuman_boundary=None):
        if self.neuman is not None:
            space = self.space
            TD = space.top_dimension()
            mesh = space.mesh

            face = mesh.entity('face')
            face2cell = mesh.ds.face_to_cell()
            face2dof = space.boundary_dof()

            # find the index of all neuman boundary 
            idx = mesh.ds.boundary_face_index()
            if is_neuman_boundary is not None:
                bc = mesh.entity_barycenter('face', index=idx)
                flag = is_neuman_boundary(bc)
                idx = idx[flag]

            measure = mesh.entity_measure('face', index=idx)
            qf = mesh.integrator(etype='face')
            bcs, ws = qf.get_quadrature_points_and_weights()
            phi = space.face_basis(bcs)
            p = mesh.bc_to_point(bcs, etype='face', index=idx)
            n = mesh.face_unit_normal(index=idx)
            val = self.neuman(p, n) # (NQ, NF, ...)
            bb = np.einsum('m, mi..., mk, i->ik...', ws, val, phi, measure)
            b
            np.add.at(b, (face2dof[idx], np.s_[:]), bb)
            

    def apply_dirichlet_bc(self, A, b, uh, is_dirichlet_boundary=None):
        if self.dirichlet is not None:
            isDDof = self.space.set_dirichlet_bc(
                    uh, self.dirichlet,
                    is_dirichlet_boundary=is_dirichlet_boundary)
            dim = 1 if len(uh.shape) == 1 else uh.shape[1]
            isDDof = np.tile(isDDof, dim)

            x = uh.reshape(-1, order='F')
            b -= A@x
            bdIdx = np.zeros(dim*gdof, dtype=np.int)
            bdIdx[isDDof] = 1
            Tbd = spdiags(bdIdx, 0, dim*gdof, dim*gdof)
            T = spdiags(1-bdIdx, 0, dim*gdof, dim*gdof)
            A = T@A@T + Tbd
            b[isDDof] = x[isDDof]
            return A, b


class DirichletBC:
    def __init__(self, V, g0, is_dirichlet_dof=None):
        self.V = V
        self.g0 = g0

        if is_dirichlet_dof == None:
            isBdDof = V.boundary_dof()
        else:
            ipoints = V.interpolation_points()
            isBdDof = is_dirichlet_dof(ipoints)

        self.isBdDof = isBdDof

    def apply(self, A, b):
        """ Modify matrix A and b
        """
        g0 = self.g0
        V = self.V
        isBdDof = self.isBdDof

        gdof = V.number_of_global_dofs()
        x = np.zeros((gdof,), dtype=np.float)
        ipoints = V.interpolation_points()
        # the length of ipoints and isBdDof maybe different
        idx, = np.nonzero(isBdDof)
        x[isBdDof] = g0(ipoints[idx])
        b -= A@x
        bdIdx = np.zeros(gdof, dtype=np.int)
        bdIdx[isBdDof] = 1
        Tbd = spdiags(bdIdx, 0, gdof, gdof)
        T = spdiags(1-bdIdx, 0, gdof, gdof)
        A = T@A@T + Tbd

        b[isBdDof] = x[isBdDof]
        return A, b

    def apply_on_matrix(self, A):

        V = self.V
        isBdDof = self.isBdDof
        gdof = V.number_of_global_dofs()

        bdIdx = np.zeros((A.shape[0], ), np.int)
        bdIdx[isBdDof] = 1
        Tbd = spdiags(bdIdx, 0, A.shape[0], A.shape[0])
        T = spdiags(1-bdIdx, 0, A.shape[0], A.shape[0])
        A = T@A@T + Tbd

        return A

    def apply_on_vector(self, b, A):
        
        g0 = self.g0
        V = self.V
        isBdDof = self.isBdDof

        gdof = V.number_of_global_dofs()
        x = np.zeros((gdof,), dtype=np.float)

        ipoints = V.interpolation_points()
        x[isBdDof] = g0(ipoints[isBdDof,:])
        b -= A@x

        b[isBdDof] = x[isBdDof] 

        return b



        


