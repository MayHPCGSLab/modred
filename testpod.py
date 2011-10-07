#!/usr/bin/env python
import subprocess as SP
import os
import unittest

import numpy as N

from pod import POD
from fieldoperations import FieldOperations
import util
import copy
import parallel as parallel_mod

parallel = parallel_mod.parallelInstance

if parallel.isRankZero():
    print 'To test fully, remember to do both:'
    print '    1) python testpod.py'
    print '    2) mpiexec -n <# procs> python testpod.py\n'


class TestPOD(unittest.TestCase):
    """ Test all the POD class methods """
    
    def setUp(self):
        if not os.path.isdir('files_modaldecomp_test'):        
            SP.call(['mkdir','files_modaldecomp_test'])
        self.modeNumList =[2, 4, 3, 6, 9, 8, 10, 11, 30]
        self.numSnaps = 40
        self.numStates = 100
        self.indexFrom = 2
        self.pod = POD(load_field=util.load_mat_text, save_field=\
            util.save_mat_text, save_mat=util.save_mat_text, inner_product=\
            util.inner_product, verbose=False)
        self.generate_data_set()

    def tearDown(self):
        parallel.sync()
        if parallel.isRankZero():
            SP.call(['rm -rf files_modaldecomp_test/*'], shell=True)
        parallel.sync()

    def generate_data_set(self):
        # create data set (saved to file)
        self.snapPath = 'files_modaldecomp_test/snap_%03d.txt'
        self.snapPaths = []
        
        if parallel.isRankZero():
            self.snapMat = N.mat(N.random.random((self.numStates,self.\
                numSnaps)))
            for snapIndex in range(self.numSnaps):
                util.save_mat_text(self.snapMat[:, snapIndex], self.snapPath %\
                    snapIndex)
                self.snapPaths.append(self.snapPath % snapIndex)
        else:
            self.snapPaths = None
            self.snapMat = None
        if parallel.isDistributed():
            self.snapPaths = parallel.comm.bcast(self.snapPaths,root=0)
            self.snapMat = parallel.comm.bcast(self.snapMat,root=0)
         
        self.correlationMatTrue = self.snapMat.T * self.snapMat
        
        #Do the SVD on all procs.
        self.singVecsTrue, self.singValsTrue, dummy = util.svd(self.\
            correlationMatTrue)
        # Use N.dot ?
        self.modeMat = self.snapMat * N.mat(self.singVecsTrue) * N.mat(N.diag(
            self.singValsTrue ** -0.5))

     
    def test_init(self):
        """Test arguments passed to the constructor are assigned properly"""
        # Get default data member values
        # Set verbose to false, to avoid printing warnings during tests
        
        dataMembersDefault = {'save_mat': util.save_mat_text, 'load_mat': util.\
            load_mat_text, 'parallel': parallel_mod.parallelInstance,\
            'verbose': False,
            'fieldOperations': FieldOperations(load_field=None, save_field=None,
            inner_product=None, maxFieldsPerNode=2, verbose=False)}
        
        self.assertEqual(util.get_data_members(POD(verbose=False)), 
            dataMembersDefault)

        def my_load(fname): pass
        myPOD = POD(load_field=my_load, verbose=False)
        dataMembersModified = copy.deepcopy(dataMembersDefault)
        dataMembersModified['fieldOperations'].load_field = my_load
        self.assertEqual(util.get_data_members(myPOD), dataMembersModified)
       
        myPOD = POD(load_mat=my_load, verbose=False)
        dataMembersModified = copy.deepcopy(dataMembersDefault)
        dataMembersModified['load_mat'] = my_load
        self.assertEqual(util.get_data_members(myPOD), dataMembersModified)
 
        def my_save(data, fname): pass 
        myPOD = POD(save_field=my_save, verbose=False)
        dataMembersModified = copy.deepcopy(dataMembersDefault)
        dataMembersModified['fieldOperations'].save_field = my_save
        self.assertEqual(util.get_data_members(myPOD), dataMembersModified)
        
        myPOD = POD(save_mat=my_save, verbose=False)
        dataMembersModified = copy.deepcopy(dataMembersDefault)
        dataMembersModified['save_mat'] = my_save
        self.assertEqual(util.get_data_members(myPOD), dataMembersModified)
        
        def my_ip(f1, f2): pass
        myPOD = POD(inner_product=my_ip, verbose=False)
        dataMembersModified = copy.deepcopy(dataMembersDefault)
        dataMembersModified['fieldOperations'].inner_product = my_ip
        self.assertEqual(util.get_data_members(myPOD), dataMembersModified)

        maxFieldsPerNode = 500
        myPOD = POD(maxFieldsPerNode=maxFieldsPerNode, verbose=False)
        dataMembersModified = copy.deepcopy(dataMembersDefault)
        dataMembersModified['fieldOperations'].maxFieldsPerNode =\
            maxFieldsPerNode
        dataMembersModified['fieldOperations'].maxFieldsPerProc =\
            maxFieldsPerNode * parallel.getNumNodes() / parallel.\
            getNumProcs()
        self.assertEqual(util.get_data_members(myPOD), dataMembersModified)
          
        
    def test_compute_decomp(self):
        """
        Test that can take snapshots, compute the correlation and SVD matrices
        
        With previously generated random snapshots, compute the correlation 
        matrix, then take the SVD. The computed matrices are saved, then
        loaded and compared to the true matrices. 
        """
        tol = 8
        snapPath = 'files_modaldecomp_test/snap_%03d.txt'
        singVecsPath = 'files_modaldecomp_test/singvecs.txt'
        singValsPath = 'files_modaldecomp_test/singvals.txt'
        correlationMatPath = 'files_modaldecomp_test/correlation.txt'
        
        self.pod.compute_decomp(self.snapPaths)
        self.pod.save_correlation_mat(correlationMatPath)
        self.pod.save_decomp(singVecsPath, singValsPath)
        
        if parallel.isRankZero():
            singVecsLoaded = util.load_mat_text(singVecsPath)
            singValsLoaded = N.squeeze(N.array(util.load_mat_text(
                singValsPath)))
            correlationMatLoaded = util.load_mat_text(correlationMatPath)
        else:
            singVecsLoaded = None
            singValsLoaded = None
            correlationMatLoaded = None

        if parallel.isDistributed():
            singVecsLoaded = parallel.comm.bcast(singVecsLoaded, root=0)
            singValsLoaded = parallel.comm.bcast(singValsLoaded, root=0)
            correlationMatLoaded = parallel.comm.bcast(correlationMatLoaded,
                root=0)
        
        N.testing.assert_array_almost_equal(self.pod.correlationMat, self.\
            correlationMatTrue, decimal=tol)
        N.testing.assert_array_almost_equal(self.pod.singVecs, self.\
            singVecsTrue, decimal=tol)
        N.testing.assert_array_almost_equal(self.pod.singVals, self.\
            singValsTrue, decimal=tol)
          
        N.testing.assert_array_almost_equal(correlationMatLoaded, self.\
            correlationMatTrue, decimal=tol)
        N.testing.assert_array_almost_equal(singVecsLoaded, self.singVecsTrue,
            decimal=tol)
        N.testing.assert_array_almost_equal(singValsLoaded, self.singValsTrue,
            decimal=tol)
        

    def test_compute_modes(self):
        """
        Test computing modes in serial and parallel. 
        
        This method uses the existing random data set saved to disk. It tests
        that POD can generate the modes, save them, and load them, then
        compares them to the known solution.
        """
        modePath = 'files_modaldecomp_test/mode_%03d.txt'
        
        # starts with the CORRECT decomposition.
        self.pod.singVecs = self.singVecsTrue
        self.pod.singVals = self.singValsTrue
        
        self.pod.compute_modes(self.modeNumList, modePath, indexFrom=self.\
            indexFrom, snapPaths=self.snapPaths)
          
        for modeNum in self.modeNumList:
            if parallel.isRankZero():
                mode = util.load_mat_text(modePath % modeNum)
            else:
                mode = None
            if parallel.isDistributed():
                mode = parallel.comm.bcast(mode, root=0)
            N.testing.assert_array_almost_equal(mode, self.modeMat[:, 
                modeNum - self.indexFrom])
        
        if parallel.isRankZero():
            for modeNum1 in self.modeNumList:
                mode1 = util.load_mat_text(modePath % modeNum1)
                for modeNum2 in self.modeNumList:
                    mode2 = util.load_mat_text(modePath % modeNum2)
                    innerProduct = self.pod.fieldOperations.inner_product(mode1, mode2)
                    if modeNum1 != modeNum2:
                        self.assertAlmostEqual(innerProduct, 0.)
                    else:
                        self.assertAlmostEqual(innerProduct, 1.)


if __name__=='__main__':
    unittest.main(verbosity=2)


