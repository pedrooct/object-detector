# Import the required modules
from skimage.transform import pyramid_gaussian
from skimage.io import imread , imsave
from skimage.feature import hog
from sklearn.externals import joblib
import cv2
import argparse as ap
from nms import nms
from config import *
import sys,time

def sliding_window(image, window_size, step_size):
    '''
    This function returns a patch of the input image `image` of size equal
    to `window_size`. The first image returned top-left co-ordinates (0, 0)
    and are increment in both x and y directions by the `step_size` supplied.
    So, the input parameters are -
    * `image` - Input Image
    * `window_size` - Size of Sliding Window
    * `step_size` - Incremented Size of Window

    The function returns a tuple -
    (x, y, im_window)
    where
    * x is the top-left x co-ordinate
    * y is the top-left y co-ordinate
    * im_window is the sliding window image
    '''
    for y in range(0, image.shape[0], step_size[1]):
        for x in range(0, image.shape[1], step_size[0]):
            yield (x, y, image[y:y + window_size[1], x:x + window_size[0]])

if __name__ == "__main__":
    # Parse the command line arguments
    parser = ap.ArgumentParser()
    parser.add_argument('-i', "--image", help="Path to the test image", required=True)
    parser.add_argument('-d','--downscale', help="Downscale ratio", default=1.3,
            type=int)
    parser.add_argument('-v', '--visualize', help="Visualize the sliding window",
            action="store_true")
    parser.add_argument('-s', '--scale', help="Scales a image a number of times",default=-1,type=int)
    parser.add_argument('-t', '--timer', help="Time to move on",default=-1, type=int)
    parser.add_argument('-l', '--learn', help="Learning level 0 - doesn't learn 1 - you decide what to learn , 2- auto-learning(use if it's good at it !!) ",default=0, type=int)
    parser.add_argument('-pl', '--pathlearn', help="Give path if you are using learning option")
    args = vars(parser.parse_args())

    # Read the image
    im = imread(args["image"],as_gray=True)
    min_wdw_sz = (100,250)
    step_size = (80,200)
    #min_wdw_sz = (32,32)
    #step_size = (64,64)
    downscale = args['downscale']
    visualize_det = args['visualize']
    timer = args["timer"]
    learn = args["learn"]

    # Load the classifier
    clf = joblib.load(model_path)

    # List to store the detections
    detections = []
    # The current scale of the image
    scale = 1
    # Downscale the image and iterate
    for im_scaled in pyramid_gaussian(im, downscale=downscale):
        # This list contains detections at the current scale
        if int(args["scale"])!=-1 and scale > int(args["scale"]):
             break

        cd = []
        # If the width or height of the scaled image is less than
        # the width or height of the window, then end the iterations.
        if im_scaled.shape[0] < min_wdw_sz[1] or im_scaled.shape[1] < min_wdw_sz[0]:
            break
        for (x, y, im_window) in sliding_window(im_scaled, min_wdw_sz, step_size):
            if im_window.shape[0] != min_wdw_sz[1] or im_window.shape[1] != min_wdw_sz[0]:
                continue
            # Calculate the HOG features
            fd = hog(im_window, orientations, pixels_per_cell, cells_per_block,feature_vector=True)
            pred = clf.predict([fd])
            if pred == 1:
                print(  "Detection:: Location -> ({}, {})".format(x, y))
                print( "Scale ->  {} | Confidence Score {} \n".format(scale,clf.decision_function([fd])))
                detections.append((x, y, clf.decision_function([fd]),
                    int(min_wdw_sz[0]*(downscale**scale)),
                    int(min_wdw_sz[1]*(downscale**scale))))
                cd.append(detections[-1])
            # If visualize is set to true, display the working
            # of the sliding window
            if visualize_det:
                clone = im_scaled.copy()
                for x1, y1, _, _, _  in cd:
                    # Draw the detections at this scale
                    cv2.rectangle(clone, (x1, y1), (x1 + im_window.shape[1], y1 +
                        im_window.shape[0]), (0, 0, 0), thickness=2)
                cv2.rectangle(clone, (x, y), (x + im_window.shape[1], y +
                    im_window.shape[0]), (255, 255, 255), thickness=2)
                cv2.imshow("Sliding Window in Progress", clone)
                cv2.waitKey(30)
        # Move the the next scale
        scale+=1

    detections = nms(detections, threshold)
    print("detections:"+str(len(detections)))
    # Display the results before performing NMS
    clone = im.copy()
    for (x_tl, y_tl, _, w, h) in detections:
        # Draw the detections
        cv2.rectangle(im, (x_tl, y_tl), (x_tl+w, y_tl+h), (0, 0, 0), thickness=2)
    cv2.imshow("Raw Detections before NMS", im)
    if timer!=-1:
         cv2.waitKey(timer)
    else:
         cv2.waitKey()

    # Perform Non Maxima Suppression
    # Display the results after performing NMS
    for (x_tl, y_tl, _, w, h) in detections:
        # Draw the detections
        cv2.rectangle(clone, (x_tl, y_tl), (x_tl+w,y_tl+h), (0, 0, 0), thickness=2)
    cv2.imshow("Final Detections after applying NMS", clone)
    if timer!=-1:
         cv2.waitKey(timer)
    else:
         cv2.waitKey()
    if learn ==1 :
        image=args["image"].split("/")
        imageName=image[len(image)-1].split(".")
        pathLearn=args["pathlearn"]
        a=input("save it ? yes(y) or no(n) or as bg? ")
        if a =="y":
            for (x_tl, y_tl, _, w, h) in detections:
                imCrop = im[y_tl:y_tl+h,x_tl:x_tl+w]
                result=imsave(f"{pathLearn}img_{imageName[0]}_{x_tl}_{y_tl}_save_1.png",imCrop)
                if result:
                    print("Result saved.")
                else:
                    print("Error ! maybe path is wrong , is folder created ?")
        if a=="bg":
            for (x_tl, y_tl, _, w, h) in detections:
                imCrop = im[y_tl:y_tl+h,x_tl:x_tl+w]
                result=imsave(f"{pathLearn}img_{imageName[0]}_{x_tl}_{y_tl}_save_2_bg.png",imCrop)
                if result:
                    print("Result saved.")
                else:
                    print("Error ! maybe path is wrong , is folder created ?")

    if learn ==2:
        image=args["image"].split("/")
        imageName=image[len(image)-1].split(".")
        pathLearn=args["pathlearn"]
        for (x_tl, y_tl, _, w, h) in detections:
            imCrop = im[y_tl:y_tl+h,x_tl:x_tl+w]
            result=imsave(f"{pathLearn}img_{imageName[0]}_{x_tl}_{y_tl}_save_1.png",imCrop)
            if result:
                print("Result saved.")
            else:
                print("Error ! maybe path is wrong , is folder created ?")
