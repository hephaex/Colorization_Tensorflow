# Let there be Color Tensorflow

Tensorflow mplementation of [Let there be Color](http://hi.cs.waseda.ac.jp/~iizuka/projects/colorization/en/) paper published in 2016.  
The model implemented here is a lot smaller than the one described in the paper due to resource issue.  

## What's different
* no classification network  
* all the output filter size other than the colorization network is reduced to half  
* input size is reduced to 63x127 (larger input gives OOM error)  

## Available dataset
* flowers
* images

### Folder setting
```
-data
  -flowers
    -img1.jpg
    -img2.jpg
    -...
  -images
    -img1.jpg
    -img2.jpg
    -...  
```

## Requirements
* python 2.7
* Tensorflow 1.3
* cv2

## Network Model
![Alt text](images/network.jpg?raw=true "network")

## Training
```
$ python train.py 
```

To continue training  
```
$ python train.py --continue_train=True
```

## Testing 
```
$ python test.py --test_img=test1.jpg
```



