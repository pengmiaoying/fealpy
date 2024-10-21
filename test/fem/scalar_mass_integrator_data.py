import numpy as np
from fealpy.decorator import cartesian


triangle_mesh_one_box = [
    {
        ##input
        "args": ([0,1,0,1], 1, 1),


        ##result
        "assembly_cell_matrix": np.array([[[ 1.66666667e-02,  7.49400542e-16,  7.51135265e-16, -2.77777778e-03,
                                        -1.11111111e-02, -2.77777778e-03],
                                        [ 7.49400542e-16,  8.88888889e-02,  4.44444444e-02,  7.50267903e-16,
                                            4.44444444e-02, -1.11111111e-02],
                                        [ 7.50267903e-16,  4.44444444e-02,  8.88888889e-02, -1.11111111e-02,
                                            4.44444444e-02,  7.50267903e-16],
                                        [-2.77777778e-03,  7.50701584e-16, -1.11111111e-02,  1.66666667e-02,
                                            7.50267903e-16, -2.77777778e-03],
                                        [-1.11111111e-02,  4.44444444e-02,  4.44444444e-02,  7.50267903e-16,
                                            8.88888889e-02,  7.49400542e-16],
                                        [-2.77777778e-03, -1.11111111e-02,  7.51135265e-16, -2.77777778e-03,
                                            7.49400542e-16,  1.66666667e-02]],

                                        [[ 1.66666667e-02,  7.49400542e-16,  7.51135265e-16, -2.77777778e-03,
                                        -1.11111111e-02, -2.77777778e-03],
                                        [ 7.49400542e-16,  8.88888889e-02,  4.44444444e-02,  7.50267903e-16,
                                            4.44444444e-02, -1.11111111e-02],
                                        [ 7.50267903e-16,  4.44444444e-02,  8.88888889e-02, -1.11111111e-02,
                                            4.44444444e-02,  7.50267903e-16],
                                        [-2.77777778e-03,  7.50701584e-16, -1.11111111e-02,  1.66666667e-02,
                                            7.50267903e-16, -2.77777778e-03],
                                        [-1.11111111e-02,  4.44444444e-02,  4.44444444e-02,  7.50267903e-16,
                                            8.88888889e-02,  7.49400542e-16],
                                        [-2.77777778e-03, -1.11111111e-02,  7.51135265e-16, -2.77777778e-03,
                                            7.49400542e-16,  1.66666667e-02]]]),   

 }
    ]