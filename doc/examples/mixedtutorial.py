import numpy as np
import pylab	
from scipy import sparse
import regreg.api as R

Y = np.random.standard_normal(500); Y[100:150] += 7; Y[250:300] += 14
loss = R.quadratic.shift(-Y, coef=0.5)

sparsity = R.l1norm(len(Y), lagrange=1.4)
# TODO should make a module to compute typical Ds
D = sparse.csr_matrix((np.identity(500) + np.diag([-1]*499,k=1))[:-1])
fused = R.l1norm.linear(D, lagrange=25.5)
problem = R.container(loss, sparsity, fused)

solver = R.FISTA(problem)
solver.fit(max_its=100, tol=1e-10)
solution = solver.composite.coefs

delta = np.fabs(D * solution).sum()
sparsity = R.l1norm(len(Y), lagrange=1.4)
fused_constraint = R.l1norm.linear(D, bound=delta)
constrained_problem = R.container(loss, fused_constraint, sparsity)
constrained_solver = R.FISTA(constrained_problem)
constrained_solver.composite.lipschitz = 1.01
vals = constrained_solver.fit(max_its=10, tol=1e-06, backtrack=False, monotonicity_restart=False)
constrained_solution = constrained_solver.composite.coefs

constrained_delta = np.fabs(D * constrained_solution).sum()
print delta, constrained_delta

pylab.scatter(np.arange(Y.shape[0]), Y)
pylab.plot(solution, c='y', linewidth=3)	
pylab.plot(constrained_solution, c='r', linewidth=1)
#pylab.plot(conjugate_coefs, c='black', linewidth=3)	
#pylab.plot(conjugate_coefs_gen, c='gray', linewidth=1)		
