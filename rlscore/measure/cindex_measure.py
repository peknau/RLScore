import operator
from numpy import array
import numpy as np
import sys
from rlscore.measure.measure_utilities import UndefinedPerformance
from rlscore.utilities import array_tools
from rlscore.utilities import swapped

def cindex_singletask(Y, P):
    Y = np.array(Y).T[0]
    P = np.array(P).T[0]
    correct = Y.astype(np.float64)
    predictions = P.astype(np.float64)
    assert len(correct) == len(predictions)
    C = array(correct).reshape(len(correct),)
    C.sort()
    pairs = 0
    c_ties = 0
    for i in range(1, len(C)):
        if C[i] != C[i-1]:
            c_ties = 0
        else:
            c_ties += 1
        #this example forms a pair with each previous example, that has a lower value
        pairs += i-c_ties
    if pairs == 0:
        raise UndefinedPerformance("No pairs, all the instances have the same output")
    #P = [(x, y) for y, x in enumerate(predictions)]
    #P.sort(key=operator.itemgetter(0))
    #P = [x[1] for x in P]
    I = np.argsort(P)
    #c code will not work, unless we ensure this
    correct = array(correct).reshape(correct.shape[0],)
    predictions = array(predictions).reshape(predictions.shape[0],)
    I = I.astype(np.int32)
    s = swapped.count_swapped(correct, predictions, I)
    disagreement = float(s)/float(pairs)
    return 1. - disagreement

def cindex_multitask(Y, P):
    perfs = []
    for i in range(Y.shape[1]):
        try:
            perfs.append(cindex_singletask(Y[:,i], P[:,i]))
        except UndefinedPerformance, e:
            perfs.append(np.nan)
    return perfs

def cindex(Y, P):
    Y = array_tools.as_labelmatrix(Y)
    P = array_tools.as_labelmatrix(P)
    perfs = cindex_multitask(Y,P)
    perfs = np.array(perfs)
    perfs = perfs[np.invert(np.isnan(perfs))]
    return np.mean(perfs)
cindex.iserror = False

