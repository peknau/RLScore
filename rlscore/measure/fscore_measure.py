import numpy as np

from measure_utilities import multitask
from rlscore.utilities import array_tools

def fscore_singletask(Y, P):
    correct = Y
    predictions = P
    assert len(correct) == len(predictions)
    TP = 0
    FP = 0
    FN = 0
    for i in range(len(correct)):
        if correct[i] == 1:
            if predictions[i] > 0.:
                TP += 1
            else:
                FN += 1
        elif correct[i] == -1:
            if predictions[i] > 0.:
                FP += 1
        else:
            assert False
    P = float(TP)/(TP+FP)
    R = float(TP)/(TP+FN)
    F = 2.*(P*R)/(P+R)
    return F

def fscore_multitask(Y, P):
    return multitask(Y, P, fscore_singletask)

def fscore(Y, P):
    """F1-Score.
    
    A performance measure for binary classification problems.
    F1 = 2*(Precision*Recall)/(Precision+Recall)
    
    If 2-dimensional arrays are supplied as arguments, then macro-averaged
    F-score is computed over the columns.
    
    Parameters
    ----------
    Y: {array-like}, shape = [n_samples] or [n_samples, n_labels]
        Correct labels, must belong to set {-1,1}
    P: {array-like}, shape = [n_samples] or [n_samples, n_labels]
        Predicted labels, can be any real numbers. P[i]>0 is treated
        as a positive, and P[i]<=0 as a negative class prediction.
    
    Returns
    -------
    fscore: float
        number between 0 and 1
    """
    Y = array_tools.as_labelmatrix(Y)
    P = array_tools.as_labelmatrix(P)
    return np.mean(fscore_multitask(Y,P))
fscore.iserror = False
