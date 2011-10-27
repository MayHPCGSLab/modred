#!/usr/bin/env python

import subprocess as SP
import bpodltirom as BPR
import unittest
import numpy as N
import util

try:
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    if comm.Get_size() > 1:
        raise RuntimeError('Not implemented in parallel! Use "python testbpodltirom.py" ')
except ImportError:
    pass

class TestBPODROM(unittest.TestCase):
    """
    Tests that can find the correct A,B,C matrices from modes
    """   
    def setUp(self):
        self.myBPODROM = BPR.BPODROM(save_mat=util.save_mat_text, load_field=\
            util.load_mat_text,inner_product=util.inner_product, save_field=\
            util.save_mat_text)
        self.test_dir = 'files_bpodltirom_test/'
        import os.path
        if not os.path.exists(self.test_dir):
            SP.call(['mkdir',self.test_dir])
        self.direct_mode_path = self.test_dir+'direct_mode_%03d.txt'
        self.adjoint_mode_path = self.test_dir +'adjoint_mode_%03d.txt'
        self.direct_deriv_mode_path =self.test_dir + 'direct_deriv_mode_%03d.txt'
        self.input_path = self.test_dir+'input_%03d.txt'
        self.output_path=self.test_dir+'output_%03d.txt'
        
        self.num_direct_modes = 10
        self.num_adjoint_modes = 8
        self.num_ROM_modes = 7
        self.num_states = 10
        self.num_inputs = 2
        self.num_outputs = 2
        self.dt = 0
        
        self.generate_data_set(self.num_direct_modes, self.num_adjoint_modes, \
            self.num_ROM_modes, self.num_states, self.num_inputs, self.num_outputs)

    def tearDown(self):
        SP.call(['rm -rf files_bpodltirom_test/*'], shell=True)
        
    def test_init(self):
        """ """
        pass
    
    def generate_data_set(self,num_direct_modes,num_adjoint_modes,num_ROM_modes,
        num_states,num_inputs,num_outputs):
        """
        Generates random data, saves to file, and computes corect A,B,C.
        """
        self.direct_mode_paths=[]
        self.direct_deriv_mode_paths=[]
        self.adjoint_mode_paths=[]
        self.input_paths=[]
        self.output_paths=[]
        
        self.direct_mode_mat = N.mat(
              N.random.random((num_states, num_direct_modes)))
        self.direct_deriv_mode_mat = N.mat(
              N.random.random((num_states, num_direct_modes)))
              
        self.adjoint_mode_mat = N.mat(
              N.random.random((num_states, num_adjoint_modes))) 
        self.input_mat = N.mat(
              N.random.random((num_states, num_inputs))) 
        self.output_mat = N.mat(
              N.random.random((num_states, num_outputs))) 
        
        for direct_mode_num in range(num_direct_modes):
            util.save_mat_text(self.direct_mode_mat[:,direct_mode_num],
              self.direct_mode_path%direct_mode_num)
            util.save_mat_text(self.direct_deriv_mode_mat[:,direct_mode_num],
              self.direct_deriv_mode_path%direct_mode_num)
            self.direct_mode_paths.append(self.direct_mode_path%direct_mode_num)
            self.direct_deriv_mode_paths.append(self.direct_deriv_mode_path %\
                direct_mode_num)
            
        for adjoint_mode_num in range(self.num_adjoint_modes):
            util.save_mat_text(self.adjoint_mode_mat[:,adjoint_mode_num],
              self.adjoint_mode_path%adjoint_mode_num)
            self.adjoint_mode_paths.append(self.adjoint_mode_path%adjoint_mode_num)
        
        for input_num in xrange(num_inputs):
            self.input_paths.append(self.input_path%input_num)
            util.save_mat_text(self.input_mat[:,input_num],self.input_paths[
                input_num])
        for output_num in xrange(num_inputs):
            self.output_paths.append(self.output_path%output_num)
            util.save_mat_text(self.output_mat[:,output_num],self.output_paths[
                output_num])            
        
        self.A_true = (self.adjoint_mode_mat.T*self.direct_deriv_mode_mat)[
            :num_ROM_modes,:num_ROM_modes]
        self.B_true = (self.adjoint_mode_mat.T*self.input_mat)[:num_ROM_modes,:]
        self.C_true = (self.output_mat.T*self.direct_mode_mat)[:,:num_ROM_modes]
        
    
    def test_form_A(self):
        """
        Test that, given modes, can find correct A matrix
        """
        A_Path = self.test_dir +'A.txt'
        self.myBPODROM.form_A(A_Path, \
            self.direct_deriv_mode_paths, \
            self.adjoint_mode_paths, self.dt, \
            num_modes=self.num_ROM_modes)
        N.testing.assert_array_almost_equal(self.A_true, \
            util.load_mat_text(A_Path))

    def test_form_B(self):
        """
        Test that, given modes, can find correct B matrix
        """
        B_Path = self.test_dir +'B.txt'
        self.myBPODROM.form_B(B_Path,self.input_paths,\
            self.adjoint_mode_paths, self.dt, num_modes=self.num_ROM_modes)
        N.testing.assert_array_almost_equal(self.B_true, \
            util.load_mat_text(B_Path))

    def test_form_C(self):
        """
        Test that, given modes, can find correct C matrix
        """
        C_Path = self.test_dir +'C.txt'
        self.myBPODROM.form_C(C_Path,self.output_paths,
            self.direct_mode_paths,
            num_modes=self.num_ROM_modes)
        
        N.testing.assert_array_almost_equal(self.C_true, \
            util.load_mat_text(C_Path))

if __name__ == '__main__':
    unittest.main(verbosity=2)
