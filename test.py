import unittest

def testKernels():
    from rlscore.test.test_kernel.test_linear import Test as lktest
    from rlscore.test.test_kernel.test_gaussian import Test as gktest
    from rlscore.test.test_kernel.test_polynomial import Test as pktest
    for test in [lktest, gktest, pktest]:
        suite = unittest.TestLoader().loadTestsFromTestCase(test)
        unittest.TextTestRunner(verbosity=2).run(suite)
        
def testLearners():
    '''
    from rlscore.test.test_learner.test_cg_rls import Test as cgtest
    from rlscore.test.test_learner.test_cg_rankrls import Test as cgranktest
    from rlscore.test.test_learner.test_rls import Test as rlstest
    from rlscore.test.test_learner.test_all_pairs_rankrls import Test as apranktest
    from rlscore.test.test_learner.test_labelrankrls import Test as lranktest
    from rlscore.test.test_learner.test_greedy_rls import Test as grlstest
    #from rlscore.test.test_learner.test_greedy_labelrankrls import Test as glrrlstest
    from rlscore.test.test_learner.test_reduced_set_approximation import Test as rsatest'''
    from rlscore.test.test_learner.test_kronecker_rls import Test as krontest
    from rlscore.test.test_learner.test_cg_kron_rls import Test as cgkrontest
    for test in [cgkrontest]:
    #for test in [krontest]:
    #for test in [cgtest, cgranktest, rlstest, apranktest, lranktest, grlstest, rsatest]:
        suite = unittest.TestLoader().loadTestsFromTestCase(test)
        unittest.TextTestRunner(verbosity=2).run(suite)
    
def testMeasures():
    #from rlscore.test.test_measure.test_accuracy import Test as atest
    #from rlscore.test.test_measure.test_sqerror import Test as btest
    from rlscore.test.test_measure.test_auc import Test as ctest
    #from rlscore.test.test_measure.test_disagreement import Test as dtest
    #from rlscore.test.test_measure.test_multiaccuracy import Test as etest
    #from rlscore.test.test_measure.test_sqmprank import Test as ftest
    #from rlscore.test.test_measure.test_fscore import Test as gtest
    from rlscore.test.test_measure.test_cindex import Test as htest    
    for test in [ctest,htest]:#[atest,btest,ctest,dtest,etest,ftest,gtest]:
        suite = unittest.TestLoader().loadTestsFromTestCase(test)
        unittest.TextTestRunner(verbosity=2).run(suite)

if __name__=="__main__":
    #testKernels()
    testLearners()
    #testMeasures()
