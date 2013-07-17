import numpy as np
import regreg.api as rr


n, p = (100, 20000)

X_lasso = np.random.standard_normal((n,p))

beta_lasso = np.zeros(p)
beta_lasso[:3] = [0.1,1.5,2.]
Y_lasso = np.random.standard_normal(n) + np.dot(X_lasso, beta_lasso)

# <codecell>

def lasso_knot_CS(X, R, soln, L):
    """
    Find an approximate LASSO knot
    """
    X = rr.astransform(X)
    p = X.input_shape[0]
    soln = soln / np.fabs(soln).sum()
    which = np.nonzero(soln)[0]
    s = np.sign(soln)

    if which.shape[0] > 1:
        tangent_vectors = [signed_basis_vector(v, s[v], p) - soln for v in which[1:]]
    else:
        tangent_vectors = None

    alpha, var = LF.find_alpha(soln, X, tangent_vectors)
    U = X.adjoint_map(R).copy()
    
    # having found alpha, we can 
    # solve for M+, M- explicitly (almost surely)
    Mplus = {}
    Mminus = {}
    keep = np.ones(U.shape[0], np.bool)
    keep[which] = 0

    den = 1 - alpha
    num = U - alpha * L
    Mplus[1] = (num / den * (den > 0))[keep]
    Mminus[1] = (num * keep / (den + (1 - keep)))[den < 0]
    
    den = 1 + alpha
    num =  -(U - alpha * L)
    Mplus[-1] = (num / den * (den > 0))[keep]
    Mminus[-1] = (num * keep / (den + (1 - keep)))[den < 0]
    
    mplus = np.hstack([Mplus[1],Mplus[-1]])
    Mplus = np.max(mplus[mplus < L]) # I think the condition is not necessary
    
    mminus = []
    if Mminus[1].shape:
        mminus.extend(list(Mminus[1]))
    if Mminus[-1].shape:
        mminus.extend(list(Mminus[-1]))
    if mminus:
        mminus = np.array(mminus)
        mminus = mminus[mminus > L]
        if mminus.shape != (0,):
            Mminus = mminus.min()
        else:
            Mminus = np.inf
    else:
        Mminus = np.inf
        
    return (L, Mplus, Mminus, alpha, tangent_vectors, var)


def solve_lasso(X, Y, L, tol=1.e-5):
    """
    Solve the nuclear norm problem with design matrix X, outcome Y
    and Lagrange parameter L.
    """
    n, p = X.shape
    X = rr.astransform(X)
    loss = rr.squared_error(X, Y)
    penalty = rr.l1norm(p, lagrange=L)
    problem = rr.simple_problem(loss, penalty)
    soln = problem.solve(tol=tol)
    resid = Y - X.linear_map(soln).copy()
    return soln, resid

lagrange_lasso = 0.995 * np.fabs(np.dot(X_lasso.T,Y_lasso)).max()
soln_lasso, resid_lasso = solve_lasso(X_lasso, Y_lasso, lagrange_lasso, tol=1.e-10)

# <codecell>

def find_next_knot_lasso(X, R, soln, L, niter=20, verbose=False):
    
    loss = rr.squared_error(X, R)
    grad = loss.smooth_objective(soln, mode='grad')

    L2 = L
    for _ in range(niter):
        grad = loss.smooth_objective(soln, mode='grad')
        Lcandidate = (sorted(np.fabs(grad))[-2] + L2) / 2.
        soln = solve_lasso(X, R, Lcandidate)[0]
        L2 = Lcandidate
    
    return L, L2

find_next_knot_lasso(X_lasso, resid_lasso, soln_lasso, lagrange_lasso)

# <codecell>

def signed_basis_vector(j, sign, p):
    v = np.zeros(p)
    v[j] = sign
    return v

reload(LF)

def lasso_knot(X, R, soln, L, epsilon=[1.e-2] + [1.e-4]*3 + [1.e-5]*3 + [1.e-6]*50 + [1.e-8]*200):
    """
    Find an approximate LASSO knot
    """
    X = rr.astransform(X)
    p = X.input_shape[0]
    soln = soln / np.fabs(soln).sum()
    which = np.nonzero(soln)[0]
    s = np.sign(soln)

    if which.shape[0] > 1:
        tangent_vectors = [signed_basis_vector(v, s[v], p) - soln for v in which[1:]]
        print 'tan', len(tangent_vectors)
    else:
        tangent_vectors = None

    alpha, var = LF.find_alpha(soln, X, tangent_vectors)
    
    # in actually finding M^+ we don't have to subtract the conditional 
    # expectation of the tangent parta, as it will be zero at eta that
    # achieves L1

    p = soln.shape[0]
    epigraph = rr.l1_epigraph(p+1)

    initial_primal = np.zeros(p+1)
    initial_primal[:-1] = soln
    initial_primal[-1] = np.fabs(soln).sum()

    Mplus = LF.linear_fractional_nesta(-(X.adjoint_map(R).copy()-alpha*L), 
                                        alpha, 
                                        epigraph, 
                                        tol=1.e-6,
                                        epsilon=epsilon,
                                        initial_primal=initial_primal,
                                        min_iters=10)

    if np.fabs(alpha).max() > 1.001:
        Mminus = LF.linear_fractional_nesta(-(X.adjoint_map(R).copy()-alpha*L), 
                                             alpha, 
                                             epigraph, 
                                             tol=1.e-6,
                                             sign=-1,
                                             epsilon=epsilon,
                                             initial_primal=initial_primal,
                                             min_iters=10)

    else:
        Mminus = np.inf

    return (L, -Mplus, Mminus, alpha, tangent_vectors, var)



L, Mplus, Mminus, alpha, tv, var = lasso_knot(X_lasso, resid_lasso, soln_lasso, lagrange_lasso)
print Mplus, Mminus
print ((L, Mplus), find_next_knot_lasso(X_lasso, resid_lasso, soln_lasso, lagrange_lasso))
print lasso_knot_CS(X_lasso, resid_lasso, soln_lasso, lagrange_lasso)[:3]

rpy.r.assign('X', X_lasso)
rpy.r.assign('Y', Y_lasso)
L = rpy.r("""
Y = as.numeric(Y)
library(lars)
L = lars(X, Y, type='lasso', intercept=FALSE, normalize=FALSE, max.steps=10)
L$lambda
""")

print L[:2]

def trendD(m, order=1):
    if order == 1:
        return -(np.diag(np.ones(m)) - np.diag(np.ones(m-1),1))[:-1]
    else:
        d = np.identity(m)
        for j in range(order):
            c = trendD(m-j,1)
            d = np.dot(c,d)
        return d

m = 1000
X_lasso = np.linalg.pinv(trendD(m, order=2))
m, p = X_lasso.shape
Y_lasso = np.random.standard_normal(m)

lagrange_lasso = 0.99 * np.fabs(np.dot(X_lasso.T, Y_lasso)).max()
soln_lasso, resid_lasso = solve_lasso(X_lasso, Y_lasso, lagrange_lasso, tol=1.e-13)
L, Mplus, Mminus, alpha, tv, var = lasso_knot(X_lasso, resid_lasso, soln_lasso, lagrange_lasso)
print Mplus, Mminus
print lasso_knot_CS(X_lasso, resid_lasso, soln_lasso, lagrange_lasso)[:3]
# print ((L, Mplus), find_next_knot_lasso(X_lasso, resid_lasso, soln_lasso, lagrange_lasso))
# rpy.r.assign('X', X_lasso)
# rpy.r.assign('Y', Y_lasso)
# L = rpy.r("""
# Y = as.numeric(Y)
# library(lars)
# L = lars(X, Y, type='lasso', intercept=FALSE, normalize=FALSE)
# L$lambda
# """)

# print L[:5]

# soln_lasso2 = solve_lasso(X_lasso, Y_lasso, 0.97*L[1], tol=1.e-13)[0]
# print np.nonzero(soln_lasso2)[0]

# soln_lasso3 = solve_lasso(X_lasso, Y_lasso, 0.97*Mplus, tol=1.e-13)[0]
# print np.nonzero(soln_lasso3)[0]

# soln_lasso4 = solve_lasso(X_lasso, Y_lasso, 1.03*Mplus, tol=1.e-13)[0]
# print np.nonzero(soln_lasso4)[0]


X_lasso = np.random.standard_normal((n,p))

beta_lasso = np.zeros(p)
beta_lasso[:3] = [0.1,1.5,2.]
Y_lasso = np.random.standard_normal(n) + np.dot(X_lasso, beta_lasso)

penalty = rr.group_lasso(np.arange(p), lagrange=1)
dual_penalty = penalty.conjugate

lagrange_lasso = 0.995 * dual_penalty.seminorm(np.dot(X_lasso.T,Y_lasso), lagrange=1.)
print lagrange_lasso, 0.995 * np.fabs(np.dot(X_lasso.T, Y_lasso)).max(), 'huh'

def solve_glasso(X, Y, L, tol=1.e-5):
    """
    Solve the nuclear norm problem with design matrix X, outcome Y
    and Lagrange parameter L.
    """
    n, p = X.shape
    X = rr.astransform(X)
    loss = rr.squared_error(X, Y)
    penalty = rr.group_lasso(np.arange(p), lagrange=L)
    problem = rr.simple_problem(loss, penalty)
    soln = problem.solve(tol=tol)
    resid = Y - X.linear_map(soln).copy()
    return soln, resid

def glasso_knot(X, R, soln, L, epsilon=[1.e-2] + [1.e-4]*3 + [1.e-5]*3 + [1.e-6]*50 + [1.e-8]*200):
    """
    Find an approximate LASSO knot
    """
    X = rr.astransform(X)
    p = X.input_shape[0]
    soln = soln / np.fabs(soln).sum()
    which = np.nonzero(soln)[0]
    s = np.sign(soln)

    if which.shape[0] > 1:
        tangent_vectors = [signed_basis_vector(v, s[v], p) - soln for v in which[1:]]
        print 'tan', len(tangent_vectors)
    else:
        tangent_vectors = None

    alpha, var = LF.find_alpha(soln, X, tangent_vectors)
    
    # in actually finding M^+ we don't have to subtract the conditional 
    # expectation of the tangent parta, as it will be zero at eta that
    # achieves L1

    p = soln.shape[0]
    epigraph = rr.group_lasso_epigraph(np.arange(p))

    Mplus = LF.linear_fractional_nesta(-(X.adjoint_map(R).copy()-alpha*L), 
                                        alpha, 
                                        epigraph, 
                                        tol=1.e-6,
                                        epsilon=epsilon,
                                        min_iters=10)

    if np.fabs(alpha).max() > 1.001:
        Mminus = LF.linear_fractional_nesta(-(X.adjoint_map(R).copy()-alpha*L), 
                                             alpha, 
                                             epigraph, 
                                             tol=1.e-6,
                                             sign=-1,
                                             epsilon=epsilon,
                                             min_iters=10)

    else:
        Mminus = np.inf

    return (L, -Mplus, Mminus, alpha, tangent_vectors, var)




soln_lasso, resid_lasso = solve_glasso(X_lasso, Y_lasso, lagrange_lasso, tol=1.e-10)


L, Mplus, Mminus, alpha, tv, var = glasso_knot(X_lasso, resid_lasso, soln_lasso, lagrange_lasso)
print Mplus, Mminus
print ((L, Mplus), find_next_knot_lasso(X_lasso, resid_lasso, soln_lasso, lagrange_lasso))
print lasso_knot_CS(X_lasso, resid_lasso, soln_lasso, lagrange_lasso)[:3]

rpy.r.assign('X', X_lasso)
rpy.r.assign('Y', Y_lasso)
L = rpy.r("""
Y = as.numeric(Y)
library(lars)
L = lars(X, Y, type='lasso', intercept=FALSE, normalize=FALSE, max.steps=10)
L$lambda
""")

print L[:2]