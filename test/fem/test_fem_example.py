import numpy as np
import matplotlib.pyplot as plt
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
import ipdb
import pytest


from fealpy.functionspace import LagrangeFESpace as Space

from fealpy.functionspace import LagrangeFiniteElementSpace as OldSpace

from fealpy.fem import ScalarDiffusionIntegrator
from fealpy.fem import ScalarSourceIntegrator

from fealpy.fem import BilinearForm
from fealpy.fem import LinearForm
from fealpy.fem import DirichletBC

@pytest.mark.parametrize("p, n, maxit", 
        [(1, 10, 4), (2, 8, 4), (3, 6, 4), (4, 4, 4)])
def test_interval_mesh(p, n, maxit):
    from fealpy.pde.elliptic_1d import SinPDEData as PDE
    from fealpy.mesh import IntervalMesh

    pde = PDE()
    domain = pde.domain()
    em = np.zeros((2, maxit), dtype=np.float64)

    for i in range(maxit):
        mesh = IntervalMesh.from_interval_domain(domain, nx=n * 2**i)
        space = Space(mesh, p=p)

        
        bform = BilinearForm(space)
        bform.add_domain_integrator(ScalarDiffusionIntegrator())
        bform.assembly()

        lform = LinearForm(space)
        lform.add_domain_integrator(ScalarSourceIntegrator(pde.source))
        lform.assembly()

        A = bform.get_matrix()
        f = lform.get_vector() 

        ospace = OldSpace(mesh, p=p)
        OA = ospace.stiff_matrix()
        ipdb.set_trace()
        Of = ospace.source_vector(pde.source)
        np.testing.assert_allclose(A.toarray(), OA.toarray())
        np.testing.assert_allclose(f, Of)


        bc = DirichletBC(space, pde.dirichlet)
        uh = space.function()
        A, f = bc.apply(A, f, uh)
        uh[:] = spsolve(A, f)

        em[0, i] = mesh.error(pde.solution, uh, q=p+3)
        em[1, i] = mesh.error(pde.gradient, uh.grad_value, q=p+3)

    ratio = em[:, 0:-1]/em[:, 1:]
    print(em)
    print(ratio)
    assert np.abs(ratio[0, -1] - 2**(p+1)) < 0.1
    assert np.abs(ratio[1, -1] - 2**p) < 0.1

@pytest.mark.parametrize("p, n, maxit", 
        [(1, 8, 4), (2, 6, 4), (3, 4, 4), (4, 2, 4)])
def test_triangle_mesh(p, n, maxit):
    from fealpy.pde.elliptic_2d import SinSinPDEData as PDE
    from fealpy.mesh import TriangleMesh 

    pde = PDE()
    domain = pde.domain()
    em = np.zeros((2, maxit), dtype=np.float64)

    for i in range(maxit):
        mesh = TriangleMesh.from_unit_square(nx=n*2**i, ny=n*2**i)
        space = Space(mesh, p=p)

        
        bform = BilinearForm(space)
        bform.add_domain_integrator(ScalarDiffusionIntegrator())
        bform.assembly()
        A = bform.get_matrix()

        lform = LinearForm(space)
        lform.add_domain_integrator(ScalarSourceIntegrator(pde.source))
        lform.assembly()
        f = lform.get_vector() 

        ospace = OldSpace(mesh, p=p)
        OA = ospace.stiff_matrix()
        Of = ospace.source_vector(pde.source)
        np.testing.assert_allclose(A.toarray(), OA.toarray())
        np.testing.assert_allclose(f, Of)

        bc = DirichletBC(space, pde.dirichlet)
        uh = space.function()
        A, f = bc.apply(A, f, uh)

        uh[:] = spsolve(A, f)

        em[0, i] = mesh.error(pde.solution, uh, q=p+3)
        em[1, i] = mesh.error(pde.gradient, uh.grad_value, q=p+3)

    ratio = em[:, 0:-1]/em[:, 1:]
    print(em)
    print(ratio)
    assert np.abs(ratio[0, -1] - 2**(p+1)) < 0.1
    assert np.abs(ratio[1, -1] - 2**p) < 0.1

@pytest.mark.parametrize("p, n, maxit", 
        [(1, 5, 4), (2, 4, 4), (3, 3, 4), (4, 2, 4)])
def test_tetrahedron_mesh(p, n, maxit):
    from fealpy.pde.elliptic_3d import SinSinSinPDEData as PDE
    from fealpy.mesh import TetrahedronMesh 

    pde = PDE()
    domain = pde.domain()
    em =  np.zeros((2, maxit), dtype=np.float64)

    for i in range(maxit):
        mesh = TetrahedronMesh.from_unit_cube(nx=n * 2**i, ny=n * 2**i, nz= n * 2**i)
        space = Space(mesh, p=p)
        
        bform = BilinearForm(space)
        bform.add_domain_integrator(ScalarDiffusionIntegrator())
        bform.assembly()
        A = bform.get_matrix()

        lform = LinearForm(space)
        lform.add_domain_integrator(ScalarSourceIntegrator(pde.source))
        lform.assembly()
        f = lform.get_vector() 

        ospace = OldSpace(mesh, p=p)
        OA = ospace.stiff_matrix()
        Of = ospace.source_vector(pde.source)
        np.testing.assert_allclose(A.toarray(), OA.toarray())
        np.testing.assert_allclose(f, Of)

        bc = DirichletBC(space, pde.dirichlet)
        uh = space.function()
        A, f = bc.apply(A, f, uh)

        uh[:] = spsolve(A, f)

        em[0, i] = mesh.error(pde.solution, uh, q=p+3)
        em[1, i] = mesh.error(pde.gradient, uh.grad_value, q=p+3)

    ratio = em[:, 0:-1]/em[:, 1:]
    print(em)
    print(ratio)
    assert np.abs(ratio[0, -1] - 2**(p+1)) < 0.1
    assert np.abs(ratio[1, -1] - 2**p) < 0.1

if __name__ == "__main__":
    test_interval_mesh(1, 10, 4)
    #test_interval_mesh(2, 8, 4)
    #test_interval_mesh(3, 6, 4)
    #test_interval_mesh(4, 4, 4)
    #test_triangle_mesh()
    #test_tetrahedron_mesh()

