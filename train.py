import tensorflow as tf
import os
import numpy as np
import scipy.misc
import argparse
import sys

from config import *
from network import network


def train(args, sess, model):
    #optimizer
    optimizer = tf.train.AdamOptimizer(args.learning_rate, beta1=args.momentum, name="AdamOptimizer").minimize(model.loss, var_list=model.trainable_vars)

    epoch = 0
    step = 0
    overall_step = 0

    #saver
    saver = tf.train.Saver()        
    if args.continue_training:
        last_ckpt = tf.train.latest_checkpoint(args.modelpath)
        saver.restore(sess, last_ckpt)
        ckpt_name = str(last_ckpt)
        print "Loaded model file from " + ckpt_name
        epoch = int(last_ckpt[len(ckpt_name)-1])
    else:
        tf.global_variables_initializer().run()


    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(sess=sess, coord=coord)


    if hasattr(model, 'rec_img_summary'):
        all_summary = tf.summary.merge([model.img_summary,
                                        model.rec_img_summary,
                                        model.loss_summary,
                                        model.acc_summary])
    else:
        all_summary = tf.summary.merge([model.img_summary,
                                        model.loss_summary,
                                        model.acc_summary])
    
    writer = tf.summary.FileWriter(args.graphpath, sess.graph)

    while epoch < args.epochs:
        summary, loss, acc, _ = sess.run([all_summary, 
                                          model.loss, 
                                          model.accuracy, 
                                          optimizer])
        writer.add_summary(summary, overall_step)

        print "Epoch [%d] step [%d] Training Loss: [%.4f] Accuracy: [%.4f]" % (epoch, step, loss, acc)

        step += 1
        overall_step += 1

        if step*args.batch_size >= model.data_count:
            saver.save(sess, args.checkpoints_path + "model", global_step=epoch)
            print "Model saved at epoch %s" % str(epoch)                
            epoch += 1
            step = 0

    coord.request_stop()
    coord.join(threads)
    sess.close()            
    print("Done.")


def main(_):
    run_config = tf.ConfigProto()
    run_config.gpu_options.allow_growth = True
    
    with tf.Session(config=run_config) as sess:
        model = network(args)

        #create graph and checkpoints folder if they don't exist
        if not os.path.exists(args.modelpath):
            os.makedirs(args.modelpath)
        if not os.path.exists(args.graphpath):
            os.makedirs(args.graphpath)
            

        
        print 'Start Training...'
        train(args, sess, model)


main(args)

#Still Working....