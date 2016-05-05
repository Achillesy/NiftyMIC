## \file ReconstructionManager.py
#  \brief  
# 
#  \author Michael Ebner (michael.ebner.14@ucl.ac.uk)
#  \date September 2015


## Import libraries
import os                       # used to execute terminal commands in python
import numpy as np

## Import modules from src-folder
import Stack as st
import StackManager as sm
import InPlaneRigidRegistration as iprr
import FirstEstimateOfHRVolume as efhrv
import SliceToVolumeRegistration as s2vr
import VolumeReconstruction as vr
import DataPreprocessing as dp
import HierarchicalSliceAlignment as hsa
import SimpleITKHelper as sitkh
import PSF as psf


## This class manages the whole reconstruction pipeline
class ReconstructionManager:

    ## Set up output directories to save reconstruction results
    #  \param[in] dir_output output directory where all results will be stored
    #  \param[in] target_stack_number stack chosen to define space and coordinate system of HR reconstruction, integer (optional)
    def __init__(self, dir_output, target_stack_number=0, recon_name="Reconstruction"):

        self._dir_results = dir_output
        self._HR_volume_filename = "recon_" + recon_name
        
        ## Directory of input data used for reconstruction algorithm
        self._dir_results_input_data = self._dir_results + "input_data/"

        ## Directory to store slices and their computed rigid registration transformations
        self._dir_results_slices = self._dir_results + "slices/"

        ## Optional: Directory of (intermediate) segmentation propagation data:
        self._dir_results_input_data_processed = self._dir_results + "input_data_processed/"

        ## Optional: Directory after all DP steps ready for reconstruction algorthm:
        # self._dir_results_input_data_dp_final = self._dir_results + "input_data_dp_final/"

        ## Create directory if not already existing
        os.system("mkdir -p " + self._dir_results)
        os.system("mkdir -p " + self._dir_results_slices)
        os.system("mkdir -p " + self._dir_results_input_data)
        os.system("mkdir -p " + self._dir_results_input_data_processed)

        ## Delete files in folder
        os.system("rm -rf " + self._dir_results_input_data + "*")
        os.system("rm -rf " + self._dir_results_input_data_processed + "*")
        # os.system("mkdir -p " + self._dir_results_input_data)

        ## Variables containing the respective classes
        self._data_preprocessing = dp.DataPreprocessing(self._dir_results_input_data, self._dir_results_input_data_processed, target_stack_number)
        self._in_plane_rigid_registration = None
        self._stack_manager = None
        self._HR_volume = None

        ## Pre-defined values
        self._flag_use_in_plane_rigid_registration_for_initial_volume_estimate = False
        self._flag_register_stacks_before_initial_volume_estimate = False

        self._target_stack_number = target_stack_number


    ## Read input stacks stored from given directory
    #  \param[in] dir_input_to_copy directory where stacks are stored
    #  \param[in] filenames_to_copy filenames of stacks to be considered in that directory
    #  \param[in] suffix_mask extension of stack filename which indicates associated mask
    def read_input_stacks_from_filenames(self, dir_input_to_copy, filenames_to_copy, suffix_mask="_mask"):
        N_stacks = len(filenames_to_copy)
        filenames = [str(i) for i in range(0, N_stacks)]

        self._stack_manager = sm.StackManager()

        ## Copy files to self._dir_results_input_data:
        ## (Filenames represent continuous numbering)
        for i in range(0, N_stacks):

            ## 1) Copy images:
            cmd = "cp " + dir_input_to_copy + filenames_to_copy[i] + ".nii.gz " \
                        + self._dir_results_input_data + filenames[i] + ".nii.gz"
            print cmd
            os.system(cmd)

            ## 2) Copy masks:
            if os.path.isfile(dir_input_to_copy + filenames_to_copy[i] + suffix_mask + ".nii.gz"):
                cmd = "cp " + dir_input_to_copy + filenames_to_copy[i] + suffix_mask + ".nii.gz " \
                            + self._dir_results_input_data + filenames[i] + suffix_mask + ".nii.gz"
                os.system(cmd)
            
        print(str(N_stacks) + " stacks were copied to directory " + self._dir_results_input_data)

        ## Data preprocessing:
        self._data_preprocessing.run_preprocessing(filenames, suffix_mask)

        ## Read stacks:
        self._stack_manager.read_input_stacks(self._dir_results_input_data_processed, filenames, suffix_mask)


    ## Read input stacks stored from given directory from separate slices
    #  \param[in] dir_input_to_copy directory where stacks are stored
    #  \param[in] file_prefixes_to_copy filenames of stacks to be considered in that directory
    #  \param[in] suffix_mask extension of stack filename which indicates associated mask
    def read_input_stacks_from_stacks(self, stacks, suffix_mask="_mask"):
        N_stacks = len(stacks)
        filenames = [str(i) for i in range(0, N_stacks)]

        self._stack_manager = sm.StackManager()

        ## Write files to self._dir_results_input_data:
        for i in range(0, N_stacks):
            stacks[i].write(directory=self._dir_results_input_data, filename=str(i))

        print(str(N_stacks) + " stacks were copied to directory " + self._dir_results_input_data)

        ## Data preprocessing:
        self._data_preprocessing.run_preprocessing(filenames, suffix_mask)

        ## Read stacks as bundle of slices:
        self._stack_manager.read_input_stacks(self._dir_results_input_data_processed, filenames, suffix_mask)


    ## Read input stacks stored from given directory from separate slices
    #  \param[in] dir_input_to_copy directory where stacks are stored
    #  \param[in] file_prefixes_to_copy filenames of stacks to be considered in that directory
    #  \param[in] suffix_mask extension of stack filename which indicates associated mask
    def read_input_stacks_from_slice_filenames(self, dir_input_to_copy, file_prefixes_to_copy, suffix_mask="_mask"):
        N_stacks = len(file_prefixes_to_copy)

        self._stack_manager = sm.StackManager()

        for i in range(0, N_stacks):

            ## Copy all slices and associated masks (if available):
            cmd = "cp " + dir_input_to_copy + file_prefixes_to_copy[i] + "*.nii.gz " \
                        + self._dir_results_input_data
            os.system(cmd)

            
        print(str(N_stacks) + " stacks as bundle of slices were copied to directory " + self._dir_results_input_data)

        ## Data preprocessing:
        # self._data_preprocessing.run_preprocessing(filenames, suffix_mask)

        ## Read stacks as bundle of slices:
        self._stack_manager.read_input_stacks_from_slices(self._dir_results_input_data, file_prefixes_to_copy, suffix_mask)


    ## Compute first estimate of HR volume to initialize reconstruction algortihm
    #  \param[in] display_info display information of registration results as we go along
    #  \post \p self._HR_volume is set to first estimate
    def compute_first_estimate_of_HR_volume_from_stacks(self, display_info=0):
        print("\n--- Compute first estimate of HR volume ---")

        ## Append number of stacks
        self._HR_volume_filename += "_stacks" + str(self._stack_manager.get_number_of_stacks())

        ## Instantiate object
        first_estimate_of_HR_volume = efhrv.FirstEstimateOfHRVolume(self._stack_manager, self._HR_volume_filename, self._target_stack_number)

        ## Choose reconstruction approach
        recon_approach = "SDA"
        # recon_approach = "Average"

        ## Get sigma value based on through-plane direction
        PSF = psf.PSF()
        stacks = self._stack_manager.get_stacks()
        cov_matrix = PSF.get_gaussian_PSF_covariance_matrix_from_spacing(stacks[0].sitk.GetSpacing())
        sigma_array = np.sqrt(cov_matrix.diagonal())
        print ("sigma_array = " + str(sigma_array))

        # sigma = np.mean(sigma_array)
        sigma = sigma_array[2]

        first_estimate_of_HR_volume.set_reconstruction_approach(recon_approach) #"SDA" or "Average"
        first_estimate_of_HR_volume.set_SDA_approach("Shepard-YVV") # "Shepard-YVV" or "Shepard-Deriche"
        first_estimate_of_HR_volume.set_SDA_sigma(sigma)

        ## Forward choice of whether or not in-plane registration within each
        #  stack shall be performed before estimation of initial volume
        first_estimate_of_HR_volume.use_in_plane_registration_for_initial_volume_estimate(self._flag_use_in_plane_rigid_registration_for_initial_volume_estimate)
        
        ## Forward choice of whether or not stacks shall be registered to chosen
        #  target stack or not prior the averaging of stacks for the initial volume estimation
        first_estimate_of_HR_volume.register_stacks_before_initial_volume_estimate(self._flag_register_stacks_before_initial_volume_estimate)
        
        ## Perform estimation of initial HR volume
        first_estimate_of_HR_volume.compute_first_estimate_of_HR_volume(display_info=display_info)

        ## Get estimation
        self._HR_volume = first_estimate_of_HR_volume.get_HR_volume()

        ## Write
        filename = self._HR_volume_filename + "_0"
        if recon_approach in ["SDA"]:
            filename += "_SDA_sigma" + str(np.round(sigma, decimals=2))
        else:
            filename +=  "_Average"

        self._HR_volume.write(directory=self._dir_results, filename=filename, write_mask=False)
        self._HR_volume.show(title=filename)

        

    ## Run hierarchical alignment of slices
    #  \param[in] interleave step of interleaved stack acquisition used for hierarchical alignment
    #  \param[in] use_static_volume_estimate use same HR volume for all stacks 
    #  \param[in] display_info display information of registration results as we go along
    #  \post Each slice has updated affine transformation specifying its new spatial position
    #  \post HR volume is updated according to updated slice positions
    def run_hierarchical_alignment_of_slices(self, interleave, use_static_volume_estimate=True, display_info=0):
        if self._HR_volume is None:
            raise ValueError("Error: Initial estimate of HR volume has not been computed yet")

        if self._flag_use_in_plane_rigid_registration_for_initial_volume_estimate:
            raise ValueError("Error: Hierarchical alignment of slices not possible after performed in-plane alignment of slices")

        print("\n--- Run hierarchical slice alignment approach ---")

        if use_static_volume_estimate:
            print("Current estimate of HR volume is used for all stacks and their hierarchical alignment")

        else:
            print("Current stack to be hierarchically aligned is left out for the volume estimate")

        ## Copy stack for comparison before-after
        foo = st.Stack.from_stack(self._HR_volume)

        ## Initialize object
        hierarchical_slice_alignment = hsa.HierarchicalSliceAlignment(self._stack_manager, self._HR_volume)

        ## Run hierarchical alignment of slices within stack
        hierarchical_slice_alignment.run_hierarchical_alignment(interleave, use_static_volume_estimate, display_info=display_info)

        ## Get sigma value based on through-plane direction
        PSF = psf.PSF()
        stacks = self._stack_manager.get_stacks()
        cov_matrix = PSF.get_gaussian_PSF_covariance_matrix_from_spacing(stacks[0].sitk.GetSpacing())
        sigma_array = np.sqrt(cov_matrix.diagonal())
        # print ("sigma_array = %s",%(sigma_array))

        sigma = sigma_array[2]

        ## Update HR estimate after hierarchical alignment
        volume_reconstruction = vr.VolumeReconstruction(self._stack_manager, self._HR_volume)
        recon_approach = "SDA" # "SDA" or "SRR" possible
        volume_reconstruction.set_reconstruction_approach(recon_approach)
        volume_reconstruction.set_SDA_approach("Shepard-YVV") # "Shepard-YVV" or "Shepard-Deriche"
        volume_reconstruction.set_SDA_sigma(sigma)

        ## Reconstruct new volume based on updated positions of slices
        volume_reconstruction.run_reconstruction()

        ## Write
        filename = self._HR_volume_filename + "_0"
        if recon_approach in ["SDA"]:
            filename += "_SDA_sigma" + str(np.round(sigma, decimals=2))
        else:
            filename +=  "_SRR" + SRR_approach + "_itermax" + str(SRR_iter_max) + "_alpha" + str(SRR_regularisation_param)
        filename +=  "_hierarchical_alignment"
            
        self._HR_volume.write(directory=self._dir_results, filename=filename, write_mask=False)

        sitkh.show_sitk_image(foo.sitk, overlay=self._HR_volume.sitk, title="HR_volume_before_and_after_hierarchical_alignment")


    ## Execute two-step reconstruction alignment approach
    #  \param[in] iterations amount of two-step reconstruction alignment steps
    #  \param[in] display_info display information of registration results as we go along
    def run_two_step_reconstruction_alignment_approach(self, iterations=5, display_info=0):
        if self._HR_volume is None:
            raise ValueError("Error: Initial estimate of HR volume has not been computed yet")

        print("\n--- Run two-step reconstruction alignment approach ---")

        ## Show initialization for two-step reconstruction alignment approach
        # filename = self._HR_volume_filename + "_init_2step_approach"
        # self._HR_volume.show(title=filename)

        ## Instantiate objects
        slice_to_volume_registration = s2vr.SliceToVolumeRegistration(self._stack_manager, self._HR_volume)
        volume_reconstruction = vr.VolumeReconstruction(self._stack_manager, self._HR_volume)

        ## Chose reconstruction approach 
        recon_approach = "SDA" # "SDA" or "SRR" possible

        ## Define static volumetric reconstruction settings
        if recon_approach in ["SDA"]:
            ## Get sigma value based on through-plane direction
            PSF = psf.PSF()
            stacks = self._stack_manager.get_stacks()
            cov_matrix = PSF.get_gaussian_PSF_covariance_matrix_from_spacing(stacks[0].sitk.GetSpacing())
            sigma_array = np.sqrt(cov_matrix.diagonal())
            print ("sigma_array = " + str(sigma_array))

            # sigma = sigma_array[2]
            sigma = 1
            volume_reconstruction.set_reconstruction_approach(recon_approach)
            volume_reconstruction.set_SDA_approach("Shepard-YVV") # "Shepard-YVV" or "Shepard-Deriche"
            volume_reconstruction.set_SDA_sigma(sigma)
        else:
            SRR_approach = "TK1"        # "TK0" or "TK1"
            SRR_iter_max = 5
            SRR_regularisation_param = 0.1

            volume_reconstruction.set_reconstruction_approach(recon_approach)
            volume_reconstruction.set_SRR_iter_max(SRR_iter_max)
            volume_reconstruction.set_SRR_alpha(SRR_regularisation_param)
            volume_reconstruction.set_SRR_approach(SRR_approach)       
            # volume_reconstruction.set_SRR_DTD_computation_type("Laplace")
            volume_reconstruction.set_SRR_DTD_computation_type("FiniteDifference") 
            ## More stable: Finite Difference
            ## Less complaints like "Bad direction in the line search; refresh the lbfgs memory and restart the iteration."


        ## Run two-step reconstruction alignment:
        for i in range(0, iterations):   

            ## Prepare filename            
            filename = self._HR_volume_filename 
            filename += "_" + str(i+1)

            ## Configure chosen reconstruction approach            
            if recon_approach in ["SDA"]:
                sigma = np.max((0.7,sigma-0.05))
                volume_reconstruction.set_SDA_sigma(sigma)
                
                filename += "_SDA_sigma" + str(np.round(sigma, decimals=2))

            else:
                filename +=  "_SRR" + SRR_approach + "_itermax" + str(SRR_iter_max) + "_alpha" + str(SRR_regularisation_param)

            ## Slice-to-Volume Registration: Register all slices to current HR estimate
            print("\n*** Iteration %s/%s: Slice-to-Volume Registration" %(i+1,iterations))
            slice_to_volume_registration.run_slice_to_volume_registration(display_info=display_info)

            ## Volumetric Reconstruction: Estimate HR volume based on updated position of slices
            print("\n*** Iteration %s/%s: Volumetric Reconstruction" %(i+1,iterations))
            volume_reconstruction.run_reconstruction()

            ## Write result to output directory
            self._HR_volume.write(directory=self._dir_results, filename=filename, write_mask=False)

            self._HR_volume.show(title=filename)


        ## Final SRR step
        recon_approach = "SRR"
        SRR_approach = "TK0"        # "TK0" or "TK1"
        # SRR_approach = "TK1"        # "TK0" or "TK1"
        SRR_iter_max = 30
        SRR_regularisation_param = 0.1

        volume_reconstruction.set_reconstruction_approach(recon_approach)
        volume_reconstruction.set_SRR_iter_max(SRR_iter_max)
        volume_reconstruction.set_SRR_alpha(SRR_regularisation_param)
        volume_reconstruction.set_SRR_approach(SRR_approach)       
        # volume_reconstruction.set_SRR_DTD_computation_type("Laplace")
        volume_reconstruction.set_SRR_DTD_computation_type("FiniteDifference")

        volume_reconstruction.run_reconstruction()

        ## Prepare filename
        filename =  self._HR_volume_filename 
        filename += "_cycles" + str(iterations)
        filename +=  "_SRR" + SRR_approach + "_itermax" + str(SRR_iter_max) + "_alpha" + str(SRR_regularisation_param)

        ## Update filename of HR reconstruction based on chosen options
        self._HR_volume_filename = filename

        ## Write result
        self._HR_volume.write(directory=self._dir_results, filename=filename, write_mask=False)


    ## Execute in-plane rigid registration align slices planarly within stack 
    #  to compensate for planarly occurred motion. It used
    #  \post Each slice is updated with new affine matrix defining its updated
    #       spatial position
    def run_in_plane_rigid_registration_within_stack(self):
        self._in_plane_rigid_registration = iprr.InPlaneRigidRegistration(self._stack_manager)


    ## \todo Delete that function. It is used only to check results
    def write_resampled_stacks_after_2D_in_plane_registration(self):
        self._in_plane_rigid_registration.write_resampled_stacks(self._dir_results)
        print("Resampled stacks after in-plane registration successfully written to directory %r " % self._dir_results)


    ## Perform in-plane rigid registration within each stack prior the first
    #  estimate of the HR volume via compute_first_estimate_of_HR_volume_from_stacks
    def set_on_in_plane_rigid_registration_before_estimating_initial_volume(self):
        self._flag_use_in_plane_rigid_registration_for_initial_volume_estimate = True


    ## Do not perform in-plane rigid registration within each stack prior the first
    #  estimate of the HR volume via compute_first_estimate_of_HR_volume_from_stacks
    def set_off_in_plane_rigid_registration_before_estimating_initial_volume(self):
        self._flag_use_in_plane_rigid_registration_for_initial_volume_estimate = False


    ## Rigidly register all stacks with chosen target volume prior the estimation
    #  of first HR volume
    def set_on_registration_of_stacks_before_estimating_initial_volume(self):
        self._flag_register_stacks_before_initial_volume_estimate = True


    ## Do not rigidly register all stacks with chosen target volume prior the estimation
    #  of first HR volume
    def set_off_registration_of_stacks_before_estimating_initial_volume(self):
        self._flag_register_stacks_before_initial_volume_estimate = False


    ## Request all stacks with all slices and their (header) information
    #  \return list of Stack objects
    def get_stacks(self):
        return self._stack_manager.get_stacks()


    ## Set current estimate of HR volume by hand
    #  \param[in] HR_volume current estimate of HR volume, instance of Stack
    def set_HR_volume(self, HR_volume):
        self._HR_volume = st.Stack.from_stack(HR_volume)


    ## Get current estimate of HR volume
    #  \return Stack object containing the current HR volume information
    def get_HR_volume(self):

        try: 
            if self._HR_volume is None:
                raise ValueError("Error: HR volume is not estimated/set yet")
            else:
                return self._HR_volume

        except ValueError as err:
            print(err.message)


    ## Write all important results to predefined output directories
    def write_results(self):
        if self._HR_volume is None:
            raise ValueError("Error: Initial estimate of HR volume has not been computed yet")

        self._stack_manager.write(self._dir_results_slices)

        self._HR_volume.write(directory=self._dir_results, filename=self._HR_volume_filename, write_mask=False)

