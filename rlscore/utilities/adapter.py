'''
Created on May 19, 2011

@author: aatapa
'''
import math

from numpy import mat, multiply, zeros, float64, ones
from scipy.sparse import csr_matrix
from numpy import matrix
from scipy.sparse.base import spmatrix
from math import sqrt
from scipy import sparse as sp
import numpy as np

from rlscore import data_sources
from rlscore.utilities import decomposition
from rlscore import model
from rlscore.utilities import array_tools


class SvdAdapter(object):
    '''
    classdocs
    '''
    
    
    def createAdapter(cls, **kwargs):
        adapter = cls()
        svals, rsvecs, U, Z = adapter.decompositionFromPool(kwargs)
        if data_sources.KERNEL_OBJ in kwargs:
            adapter.kernel = kwargs[data_sources.KERNEL_OBJ]
        adapter.svals = svals
        adapter.rsvecs = rsvecs
        adapter.U = U
        adapter.Z = Z
        if data_sources.BASIS_VECTORS in kwargs:
            adapter.bvectors = kwargs[data_sources.BASIS_VECTORS]
        else:
            adapter.bvectors = None
        return adapter
    createAdapter = classmethod(createAdapter)
    
    
    def decompositionFromPool(self, rpool):
        """Builds decomposition representing the training data from resource pool.
        Default implementation
        builds and decomposes the kernel matrix itself (standard case), or the 
        empirical kernel map of the training data, if reduced set approximation is
        used. Inheriting classes may also re-implement this by decomposing the feature
        map of the data (e.g. linear kernel with low-dimensional data).
        @param rpool: resource pool
        @type rpool: dict
        @return: svals, evecs, U, Z
        @rtype: tuple of numpy matrices
        """
        train_X = rpool[data_sources.TRAIN_FEATURES]
        kernel = rpool[data_sources.KERNEL_OBJ]
        if rpool.has_key(data_sources.BASIS_VECTORS):
            bvectors = rpool[data_sources.BASIS_VECTORS]
            K = kernel.getKM(train_X).T
            svals, evecs, U, Z = decomposition.decomposeSubsetKM(K, bvectors)
        else:
            K = kernel.getKM(train_X).T
            svals, evecs = decomposition.decomposeKernelMatrix(K)
            U, Z = None, None
        return svals, evecs, U, Z
    
    
    def reducedSetTransformation(self, A):
        if self.Z != None:
            AA = mat(zeros(A.shape, dtype = A.dtype))
            #Maybe we could somehow guarantee that Z is always coupled with bvectors?
            #if not svdlearner.resource_pool.has_key(data_sources.BASIS_VECTORS):
            #    raise Exception("Provided decomposition of the reduced set approximation of kernel matrix, but not the indices of the basis vectors")
            A_red = self.Z * (self.U.T * multiply(self.svals.T,  self.rsvecs.T * A))
            #bvecs = svdlearner.resource_pool[data_sources.BASIS_VECTORS]
            #AA[self.bvectors, :] = A_red
            #return csr_matrix(AA)
            return A_red
        else: return csr_matrix(A)
    
    
    def createModel(self, svdlearner):
        A = svdlearner.A
        A = self.reducedSetTransformation(A)
        mod = model.DualModel(A, self.kernel)
        return mod

class LinearSvdAdapter(SvdAdapter):
    '''
    classdocs
    '''
    
    
    def decompositionFromPool(self, rpool):
        kernel = rpool[data_sources.KERNEL_OBJ]
        self.X = rpool[data_sources.TRAIN_FEATURES]
        if rpool.has_key(data_sources.BASIS_VECTORS):
            bvectors = rpool[data_sources.BASIS_VECTORS]
        else:
            bvectors = None
        if "bias" in rpool:
            self.bias = float(rpool["bias"])
        else:
            self.bias = 0.
        if bvectors != None or self.X.shape[1] > self.X.shape[0]:
            K = kernel.getKM(self.X).T
            #First possibility: subset of regressors has been invoked
            if bvectors != None:
                svals, evecs, U, Z = decomposition.decomposeSubsetKM(K, bvectors)
            #Second possibility: dual mode if more attributes than examples
            else:
                svals, evecs = decomposition.decomposeKernelMatrix(K)
                U, Z = None, None
        #Third possibility, primal decomposition
        else:
            #Invoking getPrimalDataMatrix adds the bias feature
            X = getPrimalDataMatrix(self.X,self.bias)
            svals, evecs, U = decomposition.decomposeDataMatrix(X.T)
            U, Z = None, None
        return svals, evecs, U, Z
    
    
    def createModel(self, svdlearner):
        A = svdlearner.A
        A = self.reducedSetTransformation(A)
        #fs = svdlearner.resource_pool[data_sources.TRAIN_FEATURES]
        fs = self.X
        if self.bvectors != None:
            fs = self.X[self.bvectors]
        bias = self.bias
        #if "bias" in svdlearner.resource_pool:
        #    bias = float(svdlearner.resource_pool["bias"])
        #else:
        #    bias = 0.
        X = getPrimalDataMatrix(fs, bias)
        #The hyperplane is a linear combination of the feature vectors of the basis examples
        W = X.T * A
        if bias != 0:
            W_biaz = W[W.shape[0]-1] * math.sqrt(bias)
            W_features = W[range(W.shape[0]-1)]
            mod = model.LinearModel(W_features, W_biaz)
        else:
            mod = model.LinearModel(W, 0.)
        return mod

def getPrimalDataMatrix(X, bias):
    """
    Constructs the feature representation of the data.
    If bias is defined, a bias feature with value
    sqrt(bias) is added to each example. This function
    should be used when making predictions, or training
    the primal formulation of the learner.
    @param X: matrix containing the data
    @type X: scipy.sparse.base.spmatrix
    @param dimensionality: dimensionality of the feature space
    (by default the number of rows in the data matrix)
    @type dimensionality: integer
    @return: data matrix
    @rtype: scipy sparse matrix in csc format
    """
    #if sp.issparse(X):
    #    X = X.todense()
    X = array_tools.as_dense_matrix(X)
    if bias!=0:
        bias_slice = sqrt(bias)*mat(ones((X.shape[0],1),dtype=float64))
        X = np.hstack([X,bias_slice])
    return X

class PreloadedKernelMatrixSvdAdapter(SvdAdapter):
    '''
    classdocs
    '''
    
    
    def decompositionFromPool(self, rpool):
        K_train = rpool[data_sources.KMATRIX]
        if rpool.has_key(data_sources.BASIS_VECTORS):
            svals, rsvecs, U, Z = decomposition.decomposeSubsetKM(K_train, rpool[data_sources.BASIS_VECTORS])
        else:
            svals, rsvecs = decomposition.decomposeKernelMatrix(K_train)
            U, Z = None, None
        return svals, rsvecs, U, Z
    
    
    def createModel(self, svdlearner):
        A = svdlearner.A
        A = self.reducedSetTransformation(A)
        mod = model.LinearModel(A, 0.)
        return mod
