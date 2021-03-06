from math import sqrt

import numpy as np
import numpy.linalg as la
from scipy.sparse import csc_matrix
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import LinearOperator
from scipy.sparse.linalg import cg
import scipy.sparse as sp

from rlscore.learner.abstract_learner import AbstractSupervisedLearner
from rlscore.learner.abstract_learner import AbstractIterativeLearner
from rlscore import data_sources
from rlscore import model
from rlscore.utilities import array_tools
from rlscore.measure import measure_utilities
from rlscore.measure import sqmprank

class CGRankRLS(AbstractIterativeLearner):
    """Conjugate gradient RankRLS.
    
    Trains linear RankRLS using the conjugate gradient training algorithm. Suitable for
    large high-dimensional but sparse data.
    
    There are three ways to supply the pairwise preferences for the training set, depending
    on the arguments supplied by the user.
    
    1. train_labels: pairwise preferences constructed between all data point pairs
    
    2. train_labels, train_qids: pairwise preferences constructed between all data
    points belonging to the same query.
    
    3. train_preferences: arbitrary pairwise preferences supplied directly by the user.
    
    In order to make training faster, one can use the early stopping technique by
    supplying a separate validationset to be used for determining, when to terminate
    optimization. In this case, training stops once validation set error has failed to
    decrease for ten consequtive iterations. In this case, the caller should
    provide the parameters validation_features, validation_labels and optionally, validation_qids.
    Currently, this option is not supported when learning directly from pairwise
    preferences. 

    Parameters
    ----------
    train_features: {array-like, sparse matrix}, shape = [n_samples, n_features]
        Data matrix
    regparam: float (regparam > 0)
        regularization parameter
    train_labels: {array-like}, shape = [n_samples] or [n_samples, 1], optional
        Training set labels (alternative to: 'train_preferences')
    train_qids: list of n_queries index lists, optional
        Training set qids,  (can be supplied with 'train_labels')
    train_preferences: {array-like}, shape = [n_preferences, 2], optional
        Pairwise preference indices (alternative to: 'train_labels')
        The array contains pairwise preferences one pair per row, i.e. the data point
        corresponding to the first index is preferred over the data point corresponding
        to the second index.
    validation_features:: {array-like, sparse matrix}, shape = [n_samples, n_features], optional
        Data matrix for validation set, needed if early stopping used
    validation_labels: {array-like}, shape = [n_samples] or [n_samples, 1], optional
        Validation set labels, needed if early stopping used
    validation_qids: list of n_queries index lists, optional, optional
        Validation set qids, may be used with early stopping
 
       
    References
    ----------
    
    RankRLS algorithm is described in [1]_, using the conjugate gradient optimization
    together with early stopping was considered in detail in [2]_. 
    
    .. [1] Tapio Pahikkala, Evgeni Tsivtsivadze, Antti Airola, Jouni Jarvinen, and Jorma Boberg.
    An efficient algorithm for learning to rank from preference graphs.
    Machine Learning, 75(1):129-165, 2009.
    
    .. [2] Antti Airola, Tapio Pahikkala, and Tapio Salakoski.
    Large Scale Training Methods for Linear RankRLS
    ECML/PKDD-10 Workshop on Preference Learning, 2010.
    """

    def loadResources(self):
        AbstractIterativeLearner.loadResources(self)
        if data_sources.TRAIN_LABELS in self.resource_pool:
            Y = self.resource_pool[data_sources.TRAIN_LABELS]
            self.Y = array_tools.as_labelmatrix(Y)
            #Number of training examples
            self.size = Y.shape[0]
            if Y.shape[1] > 1:
                raise Exception('CGRankRLS does not currently work in multi-label mode')
            self.learn_from_labels = True
            if (data_sources.VALIDATION_FEATURES in self.resource_pool) and (data_sources.VALIDATION_LABELS in self.resource_pool):
                validation_X = self.resource_pool[data_sources.VALIDATION_FEATURES]
                validation_Y = self.resource_pool[data_sources.VALIDATION_LABELS]
                if data_sources.VALIDATION_QIDS in self.resource_pool:
                    validation_qids = self.resource_pool[data_sources.VALIDATION_QIDS]
                else:
                    validation_qids = None
                self.callbackfun = EarlyStopCB(validation_X, validation_Y, validation_qids)
        elif data_sources.TRAIN_PREFERENCES in self.resource_pool:
            self.pairs = self.resource_pool[data_sources.TRAIN_PREFERENCES]
            self.learn_from_labels = False
        else:
            raise Exception('Neither labels nor preference information found')
        X = self.resource_pool[data_sources.TRAIN_FEATURES]
        self.X = csc_matrix(X.T)
        self.bias = 0.
        if data_sources.TRAIN_QIDS in self.resource_pool:
            qids = self.resource_pool[data_sources.TRAIN_QIDS]
            self.setQids(qids)
        self.results = {}
            
    def setQids(self, qids):
        """Sets the qid parameters of the training examples. The list must have as many qids as there are training examples.
        
        @param qids: A list of qid parameters.
        @type qids: List of integers."""
        
        self.qidlist = [-1 for i in range(self.size)]
        for i in range(len(qids)):
            for j in qids[i]:
                if j >= self.size:
                    raise Exception("Index %d in query out of training set index bounds" %j)
                elif j < 0:
                    raise Exception("Negative index %d in query, query indices must be non-negative" %j)
                else:
                    self.qidlist[j] = i
        if -1 in self.qidlist:
            raise Exception("Not all training examples were assigned a query")
        
        
        self.qidmap = {}
        for i in range(len(self.qidlist)):
            qid = self.qidlist[i]
            if self.qidmap.has_key(qid):
                sameqids = self.qidmap[qid]
                sameqids.append(i)
            else:
                self.qidmap[qid] = [i]
        self.indslist = []
        for qid in self.qidmap.keys():
            self.indslist.append(self.qidmap[qid])
    
    
    def solve(self, regparam):
        """Trains the learning algorithm, using the given regularization parameter.
        
        This implementation simply changes the regparam, and then calls the train method.
        
        Parameters
        ----------
        regparam: float (regparam > 0)
            regularization parameter
        """
        self.resource_pool[data_sources.TIKHONOV_REGULARIZATION_PARAMETER] = regparam
        self.train()
    
    
    def train(self):
        """Trains the learning algorithm.
        
        After the learner is trained, one can call the method getModel
        to get the trained model
        """
        if self.learn_from_labels:
            self.trainWithLabels()
        else:
            self.trainWithPreferences()
    
    
    def trainWithLabels(self):
        regparam = float(self.resource_pool[data_sources.TIKHONOV_REGULARIZATION_PARAMETER])
        #regparam = 0.
        if data_sources.TRAIN_QIDS in self.resource_pool:
            P = sp.lil_matrix((self.size, len(self.qidmap.keys())))
            for qidind in range(len(self.indslist)):
                inds = self.indslist[qidind]
                qsize = len(inds)
                for i in inds:
                    P[i, qidind] = 1. / sqrt(qsize)
            P = P.tocsr()
            PT = P.tocsc().T
        else:
            P = 1./sqrt(self.size)*(np.mat(np.ones((self.size,1), dtype=np.float64)))
            PT = P.T
        X = self.X.tocsc()
        X_csr = X.tocsr()
        def mv(v):
            v = np.mat(v).T
            return X_csr*(X.T*v)-X_csr*(P*(PT*(X.T*v)))+regparam*v
        G = LinearOperator((X.shape[0],X.shape[0]), matvec=mv, dtype=np.float64)
        Y = self.Y
        if not self.callbackfun == None:
            def cb(v):
                self.A = np.mat(v).T
                self.b = np.mat(np.zeros((1,1)))
                self.callback()
        else:
            cb = None
        XLY = X_csr*Y-X_csr*(P*(PT*Y))
        try:
            self.A = np.mat(cg(G, XLY, callback=cb)[0]).T
        except Finished, e:
            pass
        self.b = np.mat(np.zeros((1,1)))
        self.results[data_sources.MODEL] = self.getModel()
    
    
    def trainWithPreferences(self):
        regparam = float(self.resource_pool[data_sources.TIKHONOV_REGULARIZATION_PARAMETER])
        X = self.X.tocsc()
        X_csr = X.tocsr()
        vals = np.concatenate([np.ones((self.pairs.shape[0]), dtype=np.float64), -np.ones((self.pairs.shape[0]), dtype=np.float64)])
        row = np.concatenate([np.arange(self.pairs.shape[0]),np.arange(self.pairs.shape[0])])
        col = np.concatenate([self.pairs[:,0], self.pairs[:,1]])
        coo = coo_matrix((vals, (row, col)), shape=(self.pairs.shape[0], X.shape[1]))
        pairs_csr = coo.tocsr()
        pairs_csc = coo.tocsc()
        def mv(v):
            vmat = np.mat(v).T
            ret = np.array(X_csr * (pairs_csc.T * (pairs_csr * (X.T * vmat))))+regparam*vmat
            return ret
        G = LinearOperator((X.shape[0], X.shape[0]), matvec=mv, dtype=np.float64)
        self.As = []
        M = np.mat(np.ones((self.pairs.shape[0], 1)))
        if not self.callbackfun == None:
            def cb(v):
                self.A = np.mat(v).T
                self.b = np.mat(np.zeros((1,1)))
                self.callback()
        else:
            cb = None
        XLY = X_csr * (pairs_csc.T * M)
        self.A = np.mat(cg(G, XLY, callback=cb)[0]).T
        self.b = np.mat(np.zeros((1,self.A.shape[1])))
        self.results[data_sources.MODEL] = self.getModel()
    
    
    def getModel(self):
        """Returns the trained model, call this only after training.
        
        Returns
        -------
        model : LinearModel
            prediction function
        """
        return model.LinearModel(self.A, self.b)

class EarlyStopCB(object):
    
    def __init__(self, X_valid, Y_valid, qids_valid = None, measure=sqmprank, maxiter=10):
        self.X_valid = array_tools.as_matrix(X_valid)
        self.Y_valid = array_tools.as_labelmatrix(Y_valid)
        self.qids_valid = qids_valid
        self.measure = measure
        self.bestperf = None
        self.bestA = None
        self.iter = 0
        self.last_update = 0
        self.maxiter = maxiter
    
    def callback(self, learner):
        m = model.LinearModel(learner.A, learner.b)
        P = m.predict(self.X_valid)
        if self.qids_valid:
            perfs = []
            for query in self.qids_valid:
                try:
                    perf = self.measure(self.Y_valid[query], P[query])
                    perfs.append(perf)
                except UndefinedPerformance, e:
                    pass
            perf = np.mean(perfs)
        else:
            perf = self.measure(self.Y_valid,P)
        if self.bestperf == None or (self.measure.iserror == (perf < self.bestperf)):
            self.bestperf = perf
            self.bestA = learner.A
            self.last_update = 0
        else:
            self.iter += 1
            self.last_update += 1
        if self.last_update == self.maxiter:
            learner.A = np.mat(self.bestA)
            raise Finished("Done")

        
    def finished(self, learner):
        pass
        

class Finished(Exception):
    """Used to indicate that the optimization is finished and should
    be terminated."""

    def __init__(self, value):
        """Initialization
        
        @param value: the error message
        @type value: string"""
        self.value = value

    def __str__(self):
        return repr(self.value)  

    