import operator
import numpy as np

from rlscore.measure.measure_utilities import UndefinedPerformance
from measure_utilities import multitask
from rlscore.utilities import array_tools

def auc_singletask(Y, P):
    #the implementation has n(log(n)) time complexity
    #P: predicted labels
    #Y: true labels, y_i \in {-1,1} for each y_i \in Y
    #
    Y = np.array(Y).T[0]
    P = np.array(P).T[0]
    size = len(P)
    #form a list of prediction-label pairs
    I = np.argsort(P)
    Y = Y[I]
    P = P[I]
    poscount = 0.
    #The number of positive labels that have the same prediction
    #as the current P[i] value
    posties = 0.
    #Number of pairwise mistakes this far
    errors = 0.
    j = 0
    for i in range(size):
        #j points always to the next entry in P for which 
        #P[j] > P[i]. In the end j will point outside of P
        if j == i:
            poscount += posties
            posties = 0.
            while j< size and P[i]==P[j]:
                if Y[j]==1:
                    posties += 1
                j+=1
        if Y[i] == -1:
            #every pairwise inversion of positive-negative pair
            #incurs one error, except for ties where it incurs 0.5
            #errors
            errors += poscount+0.5*posties
    poscount += posties
    #the number of positive-negative pairs
    paircount = poscount*(size-poscount)
    #AUC is 1 - number of pairwise errors
    if paircount == 0:
        raise UndefinedPerformance("AUC undefined if both classes not present")
    AUC = 1. - errors/paircount
    return AUC

def auc_multitask(Y, P):
    return multitask(Y, P, auc_singletask)

def auc(Y, P):
    """Area under the ROC curve (AUC).
    
    A performance measure for binary classification problems.
    Can be interpreted as an estimate of the probability, that
    the classifier is able to discriminate between a randomly
    drawn positive and negative training examples. An O(n*log(n))
    time implementation, with correction for tied predictions.
    
    If 2-dimensional arrays are supplied as arguments, then AUC
    is separately computed for each column, after which the AUCs
    are averaged.
    
    Parameters
    ----------
    Y: {array-like}, shape = [n_samples] or [n_samples, n_labels]
        Correct labels, must belong to set {-1,1}
    P: {array-like}, shape = [n_samples] or [n_samples, n_labels]
        Predicted labels, can be any real numbers. 
    
    Returns
    -------
    auc: float
        number between 0 and 1
    """
    Y = array_tools.as_labelmatrix(Y)
    P = array_tools.as_labelmatrix(P)    
    return np.mean(auc_multitask(Y,P))
auc.iserror = False
