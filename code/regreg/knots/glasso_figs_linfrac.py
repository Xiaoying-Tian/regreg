import regreg.knots.group_lasso as GL
import regreg.api as rr
from regreg.affine import fused_lasso 
import regreg.affine as ra
from scipy.stats import chi
import numpy as np, random

def simulate_null(X, groups, weights={}, orthonormal=False):

    if orthonormal:
        for group in np.unique(groups):
            g = groups == group
            X[:,g] = np.linalg.svd(X[:,g], full_matrices=False)[0]

    sigma = 0.1
    n, p = X.shape

    Z = np.random.standard_normal(n) * sigma
    G = np.dot(X.T, Z)
    dual = rr.group_lasso_dual(groups, weights=weights, lagrange=1)
    L = dual.seminorm(G)

    # find something proportional to first nontrivial
    # solution

    loss = rr.squared_error(X, Z)
    penalty = rr.group_lasso(groups, weights=weights, lagrange=L)
    problem = rr.simple_problem(loss, penalty)
    soln = problem.solve()

    (L1, Mplus, Mminus, _, _, 
     var, U, alpha, _, kmax, wmax) = GL.glasso_knot(X, Z, groups, 
                                                    soln,
                                                    method='explicit',
                                                    weights=weights)

    Mminus = max(Mminus, L)
    print Mminus, L, Mplus
    k = kmax
    sd = np.sqrt(var) * sigma
    pval = (chi.cdf(Mminus / sd, k) - chi.cdf(L / sd, k)) / (chi.cdf(Mminus / sd, k) - chi.cdf(Mplus / sd, k))
    print pval
    return pval

def fig(X, fname, groups, nsim=10000, weights={}):
    IP = get_ipython()
    P = []
    for _ in range(nsim):
        pval = simulate_null(X, groups, weights=weights)
        P.append(pval)
        pp = np.array(P)
        mask = ~np.isnan(pp) + np.isfinite(pp)
        print np.mean(pp[mask]), np.std(pp[mask]), 'mean'
    P = np.array(P)
    mask = ~np.isnan(P) + np.isfinite(P)
    P = P[mask]
    P = np.clip(P,0,1)
    IP.magic('load_ext rmagic')
    IP.magic('R -i P')
    IP.run_cell_magic(u'R', u'', '''
pdf('%s')
qqplot(P, runif(%d), xlab='P-value', ylab='Uniform', pch=23, cex=0.5, bg='red')
abline(0,1, lwd=3, lty=2)
dev.off()
''' % (fname, P.shape[0]))

def fig1(nsim=10000):
    X = np.arange(12).reshape((3,4)) + np.random.standard_normal((3,4))
    X = X.T
    np.random.shuffle(X)
    X = X.T
    groups = np.array([0,0,1,1])
    fig(X, 'small_group_lasso.pdf', groups, nsim=nsim, weights={})#{0:0.1})

def fig2(nsim=10000):
    n, p = 100, 10000
    X = np.random.standard_normal((n,p)) + np.random.standard_normal(n)[:,np.newaxis]
    X -= X.mean(0)
    X /= X.std(0)
    groups = np.array(range(1000)*10)
    fig(X, 'fat_group_lasso.pdf', groups, nsim=nsim)

def fig3(nsim=10000):
    n, p = 10000, 100
    X = np.random.standard_normal((n,p)) + np.random.standard_normal(n)[:,np.newaxis]
    X -= X.mean(0)
    X /= X.std(0)
    groups = np.array(range(10)*10)
    fig(X, 'tall_group_lasso.pdf', groups, nsim=nsim)

def fig5(nsim=10000):
    IP = get_ipython()
    IP.magic('load_ext rmagic')
    IP.run_cell_magic('R', '-o X', 
'''
library(lars)
data(diabetes)
X = diabetes$x
''')
    X = IP.user_ns['X']
    groups = [0,0,0,0,1,1,2,2,2,3]
    fig(X, 'lars_diabetes_group.pdf', groups, nsim=nsim)

def produce_figs(seed=0):
    np.random.seed(seed)
    random.seed(seed)
    IP = get_ipython()
    IP.magic('R set.seed(%d)' % seed)

    [f() for f in [fig1, fig2, fig3, fig4, fig5]]
