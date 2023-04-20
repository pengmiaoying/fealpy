from typing import Optional, Union

import torch
from torch import Tensor, device

from .mesh_data_structure import Mesh2dDataStructure
from .Mesh import Mesh2d


class TriangleMeshDataStructure(Mesh2dDataStructure):
    # Constants Only
    localEdge = torch.tensor([(1, 2), (2, 0), (0, 1)])
    localFace = torch.tensor([(1, 2), (2, 0), (0, 1)])
    localCell = torch.tensor([
        (0, 1, 2),
        (1, 2, 0),
        (2, 0, 1)])
    ccw = torch.tensor([0, 1, 2])

    NVC = 3
    NVE = 2

    NEC = 3


class TriangleMesh(Mesh2d):
    def __init__(self, node: Tensor, cell: Tensor):
        assert cell.shape[-1] == 3

        self.itype = cell.dtype
        self.ftype = node.dtype
        self.node = node
        self.ds = TriangleMeshDataStructure(NN=node.shape[0], cell=cell)
        self.device = node.device

    def uniform_refine(self, n: int=1):
        pass

    def shape_function(self, bc: Tensor, p: int=1) -> Tensor:
        """
        @brief
        """
        TD = bc.shape[-1] - 1
        multi_idx = self.multi_index_matrix(p=p, device=self.device)
        c = torch.arange(1, p+1, dtype=torch.int, device=self.device)
        P = 1.0/torch.cumprod(c, dim=0)
        t = torch.arange(0, p, dtype=torch.int, device=self.device)

        shape = bc.shape[:-1] + (p+1, TD+1)
        A = torch.ones(shape, dtype=self.ftype, device=self.device)
        A[..., 1:, :] = p*bc[..., None, :] - t.reshape(-1, 1) # TODO: Make the graph linked here!!!
        torch.cumprod(A, dim=-2, out=A)
        A[..., 1:, :] *= P.reshape(-1, 1)

        idx = torch.arange(TD+1, device=self.device)
        phi = torch.prod(A[..., multi_idx, idx], dim=-1)
        return phi

    def grad_shape_function(self, bc: Tensor, p: int, index=...):
        """
        @brief
        """
        pass

    @staticmethod
    def multi_index_matrix(p: int, etype: Union[int, str]=2, device: Optional[device]=None):
        """
        @brief Get p-order multi-index matrix in a triangle.

        @param[in] p: Positive integer.

        @return: Tensor with shape (ldof, 3).
        """
        if etype in {'cell', 2}:
            ldof = (p+1)*(p+2)//2
            idx = torch.arange(0, ldof)
            idx0 = torch.floor((-1 + torch.sqrt(1+8*idx))/2)
            multi_idx = torch.zeros((ldof, 3), dtype=torch.int, device=device)
            multi_idx[:, 2] = idx - idx0*(idx0 + 1)/2
            multi_idx[:, 1] = idx0 - multi_idx[:, 2]
            multi_idx[:, 0] = p - multi_idx[:, 1] - multi_idx[:, 2]
            return multi_idx

        elif etype in {'face', 'edge', 1}:
            ldof = p + 1
            multi_idx = torch.zeros((ldof, 2), dtype=torch.int, device=device)
            multi_idx[:, 0] = torch.arange(p, -1, -1)
            multi_idx[:, 1] = p - multi_idx[:, 0]
            return multi_idx

        raise ValueError(f"Invalid entity type '{etype}'.")

    def number_of_local_ipoints(self, p: int, iptype: Union[int, str] = 'cell') -> int:
        pass

    def number_of_global_ipoints(self, p: int):
        pass

    def interpolation_points(self):
        pass
