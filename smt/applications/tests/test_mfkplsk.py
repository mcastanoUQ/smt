# -*- coding: utf-8 -*-
"""
Created on Mon May 07 14:20:11 2018

@author: m.meliani

Adapted to new SMT version in march 2020 by Nathalie Bartoli
"""

try:
    import matplotlib

    matplotlib.use("Agg")
    NO_MATPLOTLIB = False
except ImportError:
    NO_MATPLOTLIB = True

import unittest
from copy import deepcopy

import numpy as np

from smt.applications.mfkplsk import MFKPLSK
from smt.problems import Sphere, TensorProduct
from smt.sampling_methods import LHS, FullFactorial
from smt.utils.misc import compute_relative_error
from smt.utils.silence import Silence
from smt.utils.sm_test_case import SMTestCase

print_output = False


class TestMFKPLSK(SMTestCase):
    def setUp(self):
        self.nt = 100
        self.ne = 100
        self.ndim = 3
        self.n_comp = 2

    def test_mfkplsk(self):
        self.problems = ["exp", "tanh", "cos"]

        for fname in self.problems:
            prob = TensorProduct(ndim=self.ndim, func=fname)
            sampling = FullFactorial(xlimits=prob.xlimits, clip=True)

            np.random.seed(0)
            xt = sampling(self.nt)
            yt = prob(xt)
            for i in range(self.ndim):
                yt = np.concatenate((yt, prob(xt, kx=i)), axis=1)

            y_lf = 2 * prob(xt) + 2
            x_lf = deepcopy(xt)
            np.random.seed(1)
            xe = sampling(self.ne)
            ye = prob(xe)

            # Modif MM
            sm = MFKPLSK()

            if sm.options.is_declared("xlimits"):
                sm.options["xlimits"] = prob.xlimits
            sm.options["print_global"] = False

            # to test some options
            sm.options["eval_noise"] = True
            sm.options["optim_var"] = True

            # modif MM
            sm.options["n_comp"] = self.n_comp
            sm.options["theta0"] = [1e-2] * self.n_comp

            sm.set_training_values(xt, yt[:, 0])
            sm.set_training_values(x_lf, y_lf[:, 0], name=0)
            sm.set_training_values(xt, yt[:, 0])
            sm.set_training_values(x_lf, y_lf[:, 0], name=0)

            with Silence():
                sm.train()

            t_error = compute_relative_error(sm)
            e_error = compute_relative_error(sm, xe, ye)

            self.assert_error(t_error, 0.0, 1.5)
            self.assert_error(e_error, 0.0, 1.5)

    def test_mfkplsk_derivs(self):
        if self.ndim < 2:
            print("To try test_mfkplsk_derivs the dimension must be greater than 1")

        prob = Sphere(ndim=self.ndim)
        sampling = LHS(xlimits=prob.xlimits)

        # Modif MM
        nt = 100
        np.random.seed(0)
        xt = sampling(nt)
        yt = prob(xt)
        dyt = {}
        for kx in range(prob.xlimits.shape[0]):
            dyt[kx] = prob(xt, kx=kx)

        y_lf = 2 * prob(xt) + 2
        x_lf = deepcopy(xt)

        np.random.seed(1)
        xe = sampling(self.ne)
        ye = prob(xe)
        dye = {}
        for kx in range(prob.xlimits.shape[0]):
            dye[kx] = prob(xe, kx=kx)

        # modif MM
        sm = MFKPLSK()

        if sm.options.is_declared("xlimits"):
            sm.options["xlimits"] = prob.xlimits
        sm.options["print_global"] = False

        # to test some options
        sm.options["eval_noise"] = False

        # modif MM
        sm.options["n_comp"] = self.n_comp
        sm.options["theta0"] = [1e-2] * self.n_comp
        sm.set_training_values(xt, yt)
        sm.set_training_values(x_lf, y_lf, name=0)

        with Silence():
            sm.train()

        _t_error = compute_relative_error(sm)
        _e_error = compute_relative_error(sm, xe, ye)
        e_error0 = compute_relative_error(sm, xe, dye[0], 0)
        e_error1 = compute_relative_error(sm, xe, dye[1], 1)

        self.assert_error(e_error0, 0.0, 1e-1)
        self.assert_error(e_error1, 0.0, 1e-1)

    @staticmethod
    def run_mfkplsk_example():
        import matplotlib.pyplot as plt
        import numpy as np

        from smt.applications.mfk import NestedLHS
        from smt.applications.mfkplsk import MFKPLSK

        # low fidelity modelk
        def lf_function(x):
            import numpy as np

            return (
                0.5 * ((x * 6 - 2) ** 2) * np.sin((x * 6 - 2) * 2)
                + (x - 0.5) * 10.0
                - 5
            )

        # high fidelity model
        def hf_function(x):
            import numpy as np

            return ((x * 6 - 2) ** 2) * np.sin((x * 6 - 2) * 2)

        # Problem set up
        xlimits = np.array([[0.0, 1.0]])
        xdoes = NestedLHS(nlevel=2, xlimits=xlimits, random_state=0)
        xt_c, xt_e = xdoes(7)

        # Evaluate the HF and LF functions
        yt_e = hf_function(xt_e)
        yt_c = lf_function(xt_c)

        # choice of number of PLS components
        ncomp = 1
        sm = MFKPLSK(n_comp=ncomp, theta0=ncomp * [1.0])

        # low-fidelity dataset names being integers from 0 to level-1
        sm.set_training_values(xt_c, yt_c, name=0)
        # high-fidelity dataset without name
        sm.set_training_values(xt_e, yt_e)

        # train the model
        sm.train()

        x = np.linspace(0, 1, 101, endpoint=True).reshape(-1, 1)

        # query the outputs
        y = sm.predict_values(x)
        _mse = sm.predict_variances(x)
        _derivs = sm.predict_derivatives(x, kx=0)

        plt.figure()

        plt.plot(x, hf_function(x), label="reference")
        plt.plot(x, y, linestyle="-.", label="mean_gp")
        plt.scatter(xt_e, yt_e, marker="o", color="k", label="HF doe")
        plt.scatter(xt_c, yt_c, marker="*", color="g", label="LF doe")

        plt.legend(loc=0)
        plt.ylim(-10, 17)
        plt.xlim(-0.1, 1.1)
        plt.xlabel(r"$x$")
        plt.ylabel(r"$y$")

        plt.show()

    # run scripts are used in documentation as documentation is not always rebuild
    # make a test run by pytest to test the run scripts
    @unittest.skipIf(NO_MATPLOTLIB, "Matplotlib not installed")
    def test_run_mfkplsk_example(self):
        self.run_mfkplsk_example()


if __name__ == "__main__":
    unittest.main()
