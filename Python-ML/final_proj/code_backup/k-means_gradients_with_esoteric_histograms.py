from __future__ import division
'''
Created on Nov 30, 2012

@author: jason
'''

import numpy as np
import os
import inspect
from scipy.cluster.vq import *
from numpy.linalg import norm
from util.mlExceptions import *
from collections import Counter
import pickle as pkl

# Global constant for current function name

CURR_FUNC_NAME = inspect.stack()[0][3]

def getClusterHistogram(pointsInCluster, trueLabelHash, histSize = 101):
    '''
    Given all the points in a cluster, extract a histogram which plots the 
    amount of those points allocated to a true label of the data. This function
    is used as a degree of approximation to cluster accuracy.
    
    @param pointsInCluster: 2D ndarray which holds all the D-dimensional points assigned to the cluster.
    @param trueLabelHash: a hash table which maps the index of a point to its true label in the data.
    @param histSize: The size of the histogram to build (by default 101, corresponding to Caltech 101's labels).
    @return a histogram as described above
    @return the maximal true label in the cluster
    @raise LogicalError when the first or second parameter is None, or when histSize <= 0.      
    '''
    
    if pointsInCluster is None or trueLabelHash is None:
        raise LogicalError, "Method %s: None arguments were provided." %(CURR_FUNC_NAME)
    if histSize is None or histSize <=0:
        raise LogicalError, "Method %s: histSize parameter should be a positive integer (provided: %s)" %(CURR_FUNC_NAME, str(histSize))
    
    trueLabels = [trueLabelHash[point] for point in pointsInCluster]
    histogram, _binEdges = np.histogram(trueLabels, range(0, histSize + 1))
    return histogram, Counter(trueLabels).most_common(1)[0][0]

def evaluateClustering(centroids, data, assignments, trueLabelMeans, trueLabelHash, histSize=101):
    
    '''
    Evaluates a clustering algorithm, when the true labels of the data have been given. Those
    labels are contained as mapped values in "trueLabelHash". 
    
    To evaluate the clustering algorithm's accuracy, we will follow a base approach: it is possible to compute the
    distance of every centroid to the mean values of the true labels. Therefore, for every cluster it is possible
    to find the category mean to which it is closest in vector space. Furthermore, for every cluster, we build 
    a histogram which plots the distribution of its points over the ***true*** labels. Clusters whose points' 
    majority true label coincide with the label whose mean is closest to the centroid are more "accurate" than
    ones for which this condition does not hold.
    
    @param centroids: K x D ndarray, representing K centroids in D-space.
    @param data: N x D ndarray, representing the training data X.
    @param assignments: N-sized ndarray, mapping each example to its cluter. assignments[i] = k means that
            the ith example in "data" is mapped to the cluster represented by the kth centroid.
    @param trueLabelMeans: |labels| xD ndarray, holding the D-dimensional mean values of every class
    @param trueLabelHash: A hash which maps example indices to their true label.
    @param histSize: integer which represents the size of the histogram to pass to "getClusterHistogram".
            By default it's equal to 101, the amount of labels in Caltech101.
    @raise LogicalError: For various cases which have to do with argument sanity checking.
    @raise DatasetError: If provided with no data.
    @return The number of "accurate" clusters, as defined above.
    '''
    
    if centroids is None or assignments is None or trueLabelMeans is None or trueLabelHash is None:
        raise LogicalError, "Method %s: \"None\" argument(s) provided." %(CURR_FUNC_NAME)
    if data is None or data.shape[0] == 0 or data.shape[1] == 0:
        raise DatasetError, "Method %s: No training data provided." %(CURR_FUNC_NAME)
    if histSize is None or histSize <= 0:
        raise LogicalError, "Method %s: histSize parameter should be a positive integer (provided: %s)." %(CURR_FUNC_NAME, str(histSize))
    
    if len(trueLabelMeans) != 101:
        raise LogicalError, "Method %s: trueLabelMeans array should have 101 dimensions." %(CURR_FUNC_NAME)
    
     # for each centroid, find the category mean it is closest to. Then associate this cluster with this
     # mean in a hash.
     
     
     # I have tried quite a bit to find an efficient solution to this, and have failed. Instead,
     # I will write an inefficient for loop - based implementation.
     
     # Careful: the trueLabelMeans 2D ndarray is zero-indexed, whereas the labels are not!
     
    closestLabel = dict()
    for i in range(len(centroids)):
        closestLabel[i] = np.array([norm(centroids[i] - mean) for mean in trueLabelMeans]).argmin() + 1
       
    
    # Compute histograms, store them on disk, and gauge which clusters are the best. 
    # The best clusters are closest to the mean of the majority vote label voted by 
    # their points.
    
    goodCentroids = 0
    fp = open('output_data/k-means-caltech.hist' , 'w')
    for i in range(len(centroids)):
        print "Examining cluster %d." %(i)
        # Get the indices of all the points in the cluster
        pointsInCluster = [j for j in range(len(assignments)) if assignments[j] == i]
        print "Amount of points in cluster %d: %d" %(i, len(pointsInCluster))
        print "Retrieved all points in cluster %d." %(i)
        if len(pointsInCluster) > 0:
            clusterHist, majVoteLabel = getClusterHistogram(pointsInCluster, trueLabelHash, histSize)
            print "Retrieved histogram and majority vote label of cluster %d." %(i)
            # write the histogram in a file.
            fp.write(str(clusterHist))
            fp.write('\n')
            if closestLabel[i] != None and majVoteLabel == closestLabel[i]:
                goodCentroids+=1 
    fp.close()
    
    return goodCentroids
    
    
if __name__ == '__main__':
    
    try:
        os.chdir("../")
        np.random.seed()        # uses system time as default
        
        ##### Part 1: Read the Caltech101 data and store it in memory.#####
        
        DIR_categories=os.listdir('input_data/caltech_training/');       # list and store all categories (classes)
        imFeatures=[]                                                       # this list will store all training examples 
        imLabels=[]                                                         # this list will store all labels
        i=0;                                                                # this integer will effectively be the class label in our code (i = 1 to 101)
        labelNames = []                                           
        categoryMeans = []                                                  # We need the means of all categories to compare them with the cluster means later on
        labelCardinalities = []
        exampleHash = dict()                                                # We need to map every example to its respective category in O(1) for later operations.
        overAllExampleCounter = 0
        for cat in DIR_categories:                                          # loop through all categories
            if os.path.isdir('input_data/caltech_training/'+ cat):   
                labelNames.append(cat)
                i=i+1;                                             # i = current class label
                count = 0
                localList = []                                      # will hold only examples of this class (useful for computing means after for loop)
                DIR_image=os.listdir('input_data/caltech_training/'+ cat +'/');      # store all images of category "cat" 
                for im in DIR_image:                                           # loop through all images of the current category
                    if (not '._image_' in im):                                 # protect ourselves against those pesky Mac OS X - generated files
                        F = np.genfromtxt('input_data/caltech_training/'+cat+'/'+im, delimiter=' '); # F is now an 2-D numpy ndarray holding all features of an image
                        F = np.reshape(F,21*28);                               # F is now a 588 - sized 1-D ndarray holding all features of the image
                        F = F.tolist();                                        # listify the vector
                        count = count + 1
                        imFeatures.append(F);                                  # store the vector
                        imLabels.append(i);                                    # store the label
                        localList.append(F)
                        exampleHash[overAllExampleCounter] = i                                      # associate example with class in hash.           
                        overAllExampleCounter+=1                        
                        
                # compute and store the category mean
                categoryMeans.append(np.mean(localList, axis = 0))
                try:
                    len(categoryMeans)
                except TypeError:
                    raise LogicalError, "Method %s: categoryMeans should be an iterable." %(CURR_FUNC_NAME)
                labelCardinalities.append(count)
                
        # transform the data into a 2-D numpy ndarray to use in kmeans.
        imFeatures = np.array(imFeatures)
        print "Read Caltech data in memory."
        
        # How about we also store the processed data on disk?
        
        fp1 = open('proc_data/traindat.pkl', 'wb')
        fp2 = open('proc_data/trainlabs.pkl', 'wb')
        fp3 = open('proc_data/categorymeans.pkl', 'wb')
        fp4 = open('proc_data/examplehash.pkl', 'wb')
        pkl.dump(imFeatures, fp1)
        pkl.dump(imLabels, fp2)
        pkl.dump(categoryMeans, fp3)
        pkl.dump(exampleHash, fp4)
        fp4.close()
        fp3.close()
        fp2.close()
        fp1.close()
        
        ####### Part 2: Run K-means with K = 101 on data and store results on disk. #############
        
        
        # Normalize the features to have variance 1 (k-means requirement).
        
        whiten(imFeatures)
        
        # Run k-means 500 times (the default) on the data with aim to produce k = 101 clusters.
        # The stopping criterion of each iteration is a difference in the computed distortion
        # (mean squared error) less than e-05 (the default)
        
        print "Running K-means..."
        codebook, _distortion = kmeans(imFeatures, 101, 500)
        assignments, _distortion = vq(imFeatures, codebook)
        if(len(assignments) != imFeatures.shape[0]):
            raise LogicalError, "Method %s: K-means should have computed %d assignments; instead, it computed %d." %(CURR_FUNC_NAME, imFeatures.shape[0], len(assignments))
        print "Ran K-means"
        accurateClusters = evaluateClustering(codebook, imFeatures, assignments, categoryMeans, exampleHash, 101)
     
        print "We computed %d \"accurate\" clusters, which corresponds to %.3f%% of total true classes." %(accurateClusters, 100*(accurateClusters/101)) 
        
        fp = open('output_data/accurateClustersForGradients.pkl', 'wb')
        pkl.dump(accurateClusters, fp)
        fp.close()
        print "That would be all. Exiting..."
        quit()
        
    except DatasetError as d:
        print "A dataset-related error occurred: " + str(d)
        quit()
    except LogicalError as l:
        print "A logical error occurred: " + str(l)
        quit()
    except Exception as e:
        print "An exception occurred: " + str(e)
        quit()