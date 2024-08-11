
from typing import Union, Callable, Optional, Any

from ..backend import backend_manager as bm
from ..typing import TensorLike, Index, Number, _S, Shape
from .function import Function
from .utils import zero_dofs


class FunctionSpace():
    r"""The base class of function spaces"""
    ftype: Any
    itype: Any

    # basis
    def basis(self, p: TensorLike, index: Index=_S, **kwargs) -> TensorLike: raise NotImplementedError
    def grad_basis(self, p: TensorLike, index: Index=_S, **kwargs) -> TensorLike: raise NotImplementedError
    def hess_basis(self, p: TensorLike, index: Index=_S, **kwargs) -> TensorLike: raise NotImplementedError

    # values
    def value(self, uh: TensorLike, p: TensorLike, index: Index=_S) -> TensorLike: raise NotImplementedError
    def grad_value(self, uh: TensorLike, p: TensorLike, index: Index=_S) -> TensorLike: raise NotImplementedError

    # counters
    def number_of_global_dofs(self) -> int: raise NotImplementedError
    def number_of_local_dofs(self, doftype='cell') -> int: raise NotImplementedError

    # relationships
    def cell_to_dof(self) -> TensorLike: raise NotImplementedError
    def face_to_dof(self) -> TensorLike: raise NotImplementedError

    # interpolation
    def interpolate(self, source: Union[Callable[..., TensorLike], TensorLike, Number],
                    uh: TensorLike, dim: Optional[int]=None, index: Index=_S) -> TensorLike:
        raise NotImplementedError

    def array(self, batch: Union[int, Shape, None]=None, *, dtype=None):
        """Initialize a Tensor filled with zeros as values of DoFs.

        Parameters:
            batch (int | Shape | None, optional): shape of the batch.

        Returns:
            Tensor: Values of DoFs shaped (batch, GDOF).
        """
        GDOF = self.number_of_global_dofs()
        if (batch is None) or (shape == 0):
            batch = tuple()

        elif isinstance(batch, int):
            batch = (batch, )

        shape = batch + (GDOF, )

        if dtype is None:
            dtype = bm.float64

        return bm.zeros(shape, dtype=dtype)

    def function(self, array: Optional[TensorLike]=None,
                 batch: Union[int, Shape, None]=None, *,
                 coordtype='barycentric', dtype=None):
        """Initialize a Function in the space.

        Parameters:

        Returns:
            Function: A Function object.
        """
        if array is None:
            if dtype is None:
                dtype = bm.float64
            array = self.array(batch=batch, dtype=dtype)

        return Function(self, array, coordtype)
