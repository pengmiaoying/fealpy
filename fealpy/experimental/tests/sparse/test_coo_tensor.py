# test_coo_tensor.py
import pytest

from fealpy.experimental.sparse.coo_tensor import COOTensor
from fealpy.experimental.backend import backend_manager as bm

ALL_BACKENDS = ['numpy', 'pytorch']


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_dims_and_shape(backend):
    bm.set_backend(backend)
    indices = bm.tensor([[0, 0, 1, 2, 0], [1, 2, 0, 0, 2]])
    values = bm.tensor([[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]], dtype=bm.float64)
    sparse_shape = bm.tensor([3, 3])
    coo = COOTensor(indices, values, sparse_shape, is_coalesced=False)

    assert coo.ndim == 3
    assert coo.sparse_ndim == 2
    assert coo.dense_ndim == 1

    assert coo.shape == (2, 3, 3)
    assert coo.sparse_shape == (3, 3)
    assert coo.dense_shape == (2, )


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_coalesce_with_values(backend):
    bm.set_backend(backend)
    # 创建一个未合并的COOTensor对象
    indices = bm.tensor([[0, 0, 1, 2, 0, 1], [1, 2, 0, 0, 2, 0]])
    values = bm.tensor([1, 2, 3, 4, 5, 6], dtype=bm.float64)
    sparse_shape = bm.tensor([3, 3])
    coo = COOTensor(indices, values, sparse_shape, is_coalesced=False)

    # 调用coalesce方法
    coalesced_coo = coo.coalesce()

    # 验证结果是否已合并
    assert coalesced_coo.is_coalesced

    # 验证值是否正确累积
    expected_indices = bm.tensor([[1, 2, 0, 0], [0, 0, 1, 2]])
    expected_values = bm.tensor([9, 4, 1, 7], dtype=bm.float64)
    assert bm.allclose(coalesced_coo._indices, expected_indices)
    assert bm.allclose(coalesced_coo._values, expected_values)


# @pytest.mark.parametrize("backend", ALL_BACKENDS)
# def test_coalesce_without_values_accumulate(backend):
#     bm.set_backend(backend)
#     # 创建一个未合并的COOTensor对象，但没有值
#     indices = bm.tensor([[0, 0, 1, 2, 0], [1, 2, 0, 0, 2]])
#     values = None
#     sparse_shape = bm.tensor([3, 3])
#     coo = COOTensor(indices, values, sparse_shape, is_coalesced=False)

#     # 调用coalesce方法，设置accumulate为True
#     coalesced_coo = coo.coalesce(accumulate=True)

#     # 验证结果是否已合并
#     assert coalesced_coo.is_coalesced

#     # 验证输出的值是否正确
#     expected_indices = bm.tensor([[0, 0, 1, 2], [1, 2, 0, 0]])
#     expected_values = bm.tensor([1, 2, 1, 1])
#     assert bm.allclose(coalesced_coo._indices, expected_indices)
#     assert bm.allclose(coalesced_coo._values, expected_values)


# @pytest.mark.parametrize("backend", ALL_BACKENDS)
# def test_coalesce_without_values_not_accumulate(backend):
#     bm.set_backend(backend)
#     # 创建一个未合并的COOTensor对象，但没有值
#     indices = bm.tensor([[0, 0, 1, 2], [1, 2, 0, 0]])
#     values = None
#     sparse_shape = bm.tensor([3, 3])
#     coo = COOTensor(indices, values, sparse_shape, is_coalesced=False)

#     # 调用coalesce方法，设置accumulate为False
#     coalesced_coo = coo.coalesce(accumulate=False)

#     # 验证结果是否已合并
#     assert coalesced_coo.is_coalesced

#     # 验证输出的值是否为None
#     assert coalesced_coo._values is None


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_to_dense(backend):
    bm.set_backend(backend)
    indices = bm.tensor([[0, 0, 1, 2], [1, 2, 0, 0]])
    values = bm.tensor([[1, 2, 3, 4], [6, 7, 8, 9]], dtype=bm.float64)
    sparse_shape = bm.tensor([3, 3])
    coo = COOTensor(indices, values, sparse_shape)

    arr = coo.to_dense()
    assert arr.dtype == bm.float64
    bm.allclose(
        arr,
        bm.tensor([[[0, 1, 2],
                       [3, 0, 0],
                       [4, 0, 0]],
                      [[0, 6, 7],
                       [8, 0, 0],
                       [9, 0, 0]]], dtype=bm.float64)
    )
    coo2 = COOTensor(indices, None, sparse_shape)
    arr2 = coo2.to_dense(fill_value=1.22)
    bm.allclose(
        arr2,
        bm.tensor([[[0, 1.22, 1.22],
                    [1.22, 0, 0],
                    [1.22, 0, 0]],
                   [[0, 1.22, 1.22],
                    [1.22, 0, 0],
                    [1.22, 0, 0]]], dtype=bm.float64)
    )


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_ravel(backend):
    bm.set_backend(backend)
    indices = bm.tensor([[0, 2], [1, 1]])
    values = bm.tensor([[1.0, 2.0], [3.0, 4.0]])
    sparse_shape = (3, 4) # strides = (4, 1)
    coo_tensor = COOTensor(indices, values, sparse_shape)

    raveled_coo_tensor = coo_tensor.ravel()

    expected_indices = bm.tensor([[1, 9]])
    expected_sparse_shape = (12, )

    assert bm.allclose(raveled_coo_tensor.indices(), expected_indices)
    assert raveled_coo_tensor.values() is coo_tensor.values() # must be the same object
    assert raveled_coo_tensor.sparse_shape == expected_sparse_shape
    # make sure the COOTensor is shaped (*dense_shape, 1)
    assert raveled_coo_tensor.indices().shape[0] == 1


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_T_2d(backend):
    bm.set_backend(backend)
    # 创建一个 2 稀疏维度的 COOTensor 实例
    indices = bm.tensor([[0, 1], [1, 2]])
    values = bm.tensor([[1, 2]], dtype=bm.float64)
    spshape = (3, 4)
    coo_tensor = COOTensor(indices, values, spshape)
    trans_tensor = coo_tensor.T

    # 验证结果是否正确
    expected_indices = bm.tensor([[1, 2], [0, 1]])
    assert bm.all(bm.equal(trans_tensor._indices, expected_indices))
    assert trans_tensor._values is values
    assert trans_tensor._spshape == (4, 3)


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_T_3d(backend):
    bm.set_backend(backend)
    # 创建一个 3 稀疏维度的 COOTensor 实例
    indices = bm.tensor([[0, 1], [1, 2], [2, 0]])
    values = bm.tensor([1, 2], dtype=bm.float32)
    spshape = (5, 4, 3)
    coo_tensor = COOTensor(indices, values, spshape)
    trans_tensor = coo_tensor.T

    # 验证结果是否正确
    expected_indices = bm.tensor([[0, 1], [2, 0], [1, 2]])
    assert bm.all(bm.equal(trans_tensor._indices, expected_indices))
    assert trans_tensor._values is values
    assert trans_tensor._spshape == (5, 3, 4)


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_tril(backend):
    bm.set_backend(backend)
    indices = bm.tensor([[0, 1, 0, 1], [2, 3, 1, 1], [3, 2, 2, 1]])
    values = bm.tensor([1, 2, 3, 4], dtype=bm.float32)
    spshape = (5, 4, 4)
    coo_tensor = COOTensor(indices, values, spshape)
    tril_tensor = coo_tensor.tril(k=0)

    expected_indices = bm.tensor([[1, 1], [3, 1], [2, 1]])
    expected_values = bm.tensor([2, 4], dtype=bm.float32)

    assert bm.all(bm.equal(tril_tensor._indices, expected_indices))
    assert bm.allclose(tril_tensor._values, expected_values)


def create_coo_tensor(indices, values, shape):
    return COOTensor(indices=indices, values=values, spshape=shape)


# COOTensor.add 测试用例
class TestCOOTensorAdd:
    @pytest.mark.parametrize("backend", ALL_BACKENDS)
    def test_add_coo_tensor(self, backend):
        bm.set_backend(backend)
        # 初始化两个 COOTensors
        coo1 = create_coo_tensor(
            indices=bm.tensor([[0, 2], [1, 3]]), values=bm.tensor([1, 2]),
            shape=(4, 4)
        )
        coo2 = create_coo_tensor(
            indices=bm.tensor([[0, 1], [2, 3]]), values=bm.tensor([3, 4]),
            shape=(4, 4)
        )
        coo3 = create_coo_tensor(
            indices=bm.tensor([[0, 1], [2, 3]]), values=None,
            shape=(4, 4)
        )
        coo4 = create_coo_tensor(
            indices=bm.tensor([[0, 2], [1, 3]]), values=None,
            shape=(4, 4)
        )

        # 执行 add 操作
        result1 = coo1.add(coo2, alpha=2)
        result2 = coo3.add(coo4, alpha=2)

        with pytest.raises(ValueError):
            coo1.add(coo3)

        # 验证结果
        expected_indices1 = bm.tensor([[0, 2, 0, 1], [1, 3, 2, 3]])
        expected_values1 = bm.tensor([1, 2, 6, 8])
        assert bm.allclose(result1._indices, expected_indices1)
        assert bm.allclose(result1._values, expected_values1)
        expected_indices2 = bm.tensor([[0, 1, 0, 2], [2, 3, 1, 3]])
        assert bm.allclose(result2._indices, expected_indices2)
        assert result2.values() is None

    @pytest.mark.parametrize("backend", ALL_BACKENDS)
    def test_add_tensor(self, backend):
        bm.set_backend(backend)
        # 初始化一个 COOTensor 和一个 dense Tensor
        coo = create_coo_tensor(indices=bm.tensor([[0], [2]]),
                                values=bm.tensor([[1]], dtype=bm.float64),
                                shape=(4, 4))
        tensor = bm.zeros((1, 4, 4), dtype=bm.float64)

        # 执行 add 操作
        result = coo.add(tensor)

        # 验证结果
        expected_tensor = bm.tensor([[[0., 0., 1., 0.],
                                         [0., 0., 0., 0.],
                                         [0., 0., 0., 0.],
                                         [0., 0., 0., 0.]]], dtype=bm.float64)
        assert bm.allclose(result, expected_tensor)

    @pytest.mark.parametrize("backend", ALL_BACKENDS)
    def test_add_number(self, backend):
        bm.set_backend(backend)
        # 初始化一个 COOTensor 和一个数值
        coo = create_coo_tensor(indices=bm.tensor([[0], [2]]), values=bm.tensor([[1], [2]]), shape=(4, 4))
        number = 2

        # 执行 add 操作
        result = coo.add(number)

        # 验证结果的值（注意，这里只是演示，实际上 result 仍然是 COOTensor 类型）
        assert bm.allclose(result._values, bm.tensor([[3], [4]]))

    @pytest.mark.parametrize("backend", ALL_BACKENDS)
    def test_add_type_error(self, backend):
        bm.set_backend(backend)
        # 初始化一个 COOTensor
        coo = create_coo_tensor(indices=bm.tensor([[0], [2]]), values=bm.tensor([1]), shape=(4, 4))

        # 尝试添加不支持的类型，期望抛出 TypeError
        with pytest.raises(TypeError):
            coo.add("a string", alpha=1.0)
