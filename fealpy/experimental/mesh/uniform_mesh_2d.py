import numpy as np 
from typing import Union, Optional, Sequence, Tuple, Any

from .utils import entitymethod

from ..backend import backend_manager as bm 
from ..typing import TensorLike, Index, _S
from .. import logger

from .mesh_base import StructuredMesh

class UniformMesh2d(StructuredMesh):
    def __init__(self,
                 extent: Tuple[int, int, int, int],
                 h: Tuple[float, float] = (1.0, 1.0),
                 origin: Tuple[float, float] = (0.0, 0.0)):
        super().__init__(TD=2)
        # Mesh properties
        self.extent: Tuple[int, int, int, int] = extent
        self.h: Tuple[float, float] = h
        self.origin: Tuple[float, float] = origin

        # Mesh dimensions
        self.nx = self.extent[1] - self.extent[0]
        self.ny = self.extent[3] - self.extent[2]
        self.NN = (self.nx + 1) * (self.ny + 1)
        self.NE = self.ny * (self.nx + 1) + self.nx * (self.ny + 1)
        self.NF = self.NE
        self.NC = self.nx * self.ny

        self.nodedata = {}
        self.edgedata = {}
        self.facedata = self.edgedata
        self.celldata = {}
        self.meshdata = {}

        self.meshtype = 'UniformMesh2d'

        self.face_to_ipoint = self.edge_to_ipoint


    @entitymethod(0)
    def _get_node(self):
        GD = 2
        nx = self.nx
        ny = self.ny
        box = [self.origin[0], self.origin[0] + nx * self.h[0],
               self.origin[1], self.origin[1] + ny * self.h[1]]
        x = bm.linspace(box[0], box[1], nx + 1)
        y = bm.linspace(box[2], box[3], ny + 1)
        xx, yy = bm.meshgrid(x, y, indexing='ij')
        node = bm.zeros((nx + 1, ny + 1, GD), dtype=bm.float64)
        node[..., 0] = xx
        node[..., 1] = yy

        return node
    
    @entitymethod(1)
    def _get_edge(self):
        nx = self.nx
        ny = self.ny

        NN = self.NN
        NE = self.NE

        idx = bm.arange(NN, dtype=self.itype).reshape(nx + 1, ny + 1)
        edge = bm.zeros((NE, 2), dtype=bm.int32)

        NE0 = 0
        NE1 = nx * (ny + 1)
        edge[NE0:NE1, 0] = idx[:-1, :].reshape(-1)
        edge[NE0:NE1, 1] = idx[1:, :].reshape(-1)
        edge[NE0 + ny:NE1:ny + 1, :] = bm.flip(edge[NE0 + ny:NE1:ny + 1], axis=[1])

        # edge[NE0 + ny:NE1:ny + 1, :] = edge[NE0 + ny:NE1:ny + 1, -1::-1]

        NE0 = NE1
        NE1 += ny * (nx + 1)
        edge[NE0:NE1, 0] = idx[:, :-1].reshape(-1)
        edge[NE0:NE1, 1] = idx[:, 1:].reshape(-1)
        edge[NE0:NE0 + ny, :] = bm.flip(edge[NE0:NE0 + ny], axis=[1])

        # edge[NE0:NE0 + ny, :] = edge[NE0:NE0 + ny, -1::-1]
        
        return edge
    
    @entitymethod(2)
    def _get_cell(self):
        nx = self.nx
        ny = self.ny

        NN = self.NN
        NC = self.NC
        cell = bm.zeros((NC, 4), dtype=bm.int32)
        idx = bm.arange(NN).reshape(nx + 1, ny + 1)
        c = idx[:-1, :-1]
        cell[:, 0] = c.reshape(-1)
        cell[:, 1] = cell[:, 0] + 1
        cell[:, 2] = cell[:, 0] + ny + 1
        cell[:, 3] = cell[:, 2] + 1

        return cell

    

    # entity
    def entity_measure(self, etype: Union[int, str], index: Optional[Index]=None) -> TensorLike:

        if etype == 0:
            return bm.tensor([0,], dtype=self.ftype)
        elif etype == 1:
            edge = self.entity(1, index)
            return self.h[0], self.h[1]
        elif etype == 2:
            cell = self.entity(2, index)
            return self.h[0] * self.h[1]
        else:
            raise ValueError(f"Unsupported entity or top-dimension: {etype}")
