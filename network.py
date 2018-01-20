import tensorflow as tf
import numpy as np
import os

from DataReader import *
from utils import *

class network():
	def __init__(self, args):

		#load image data X and label data Y
		self.orig, self.gray, self.img_count = load_data(args)

		self.build_model()
		self.build_loss()

		#summary


	def build_model(self):
		low_out, low_nets = self.low_level_features_network(self.gray, name="low_level_features_network")
		low_out_scaled, low_nets_scaled = self.low_level_features_network(self.gray, reuse=True, name="low_level_features_network")

		middle_out, middle__nets = self.middle_level_features_network(low_out, name="middle_level_features_network")

		global_out, global_nets = self.global_features_network(low_out_scaled, name="global_features_network")

		fused = self.fuse_net(global_out, middle_out, name="fusenet")
		
		self.colorization_out, self.colorization_nets = self.colorization_network(fused, name="colorization_network")


		self.trainable_vars = tf.trainable_variables()
		
	def build_loss(self):

		gray_lab = tf.concat([self.gray , self.colorization_out], axis=-1)
		rgb_lab = rgb_to_lab(self.orig)

		self.loss = tf.losses.mean_squared_error(gray_lab, rgb_lab)

		self.res = lab_to_rgb(gray_lab)


	def low_level_features_network(self, input, reuse=False, name="low_network"):
		nets = []
		with tf.variable_scope(name, reuse=reuse) as scope:

			conv1 = tf.contrib.layers.conv2d(input, 64,
											 kernel_size=3, stride=2,
											 padding="VALID",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv1")
			nets.append(conv1)


			conv2 = tf.contrib.layers.conv2d(conv1, 128,
											 kernel_size=3, stride=1,
											 padding="SAME",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv2")
			nets.append(conv2)

			conv3 = tf.contrib.layers.conv2d(conv2, 128,
											 kernel_size=3, stride=2,
											 padding="VALID",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv3")
			nets.append(conv3)

			conv4 = tf.contrib.layers.conv2d(conv3, 256,
											 kernel_size=3, stride=1,
											 padding="SAME",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv4")
			nets.append(conv4)

			conv5 = tf.contrib.layers.conv2d(conv4, 256,
											 kernel_size=3, stride=2,
											 padding="VALID",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv5")
			nets.append(conv5)

			conv6 = tf.contrib.layers.conv2d(conv5, 512,
											 kernel_size=3, stride=1,
											 padding="SAME",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv6")	
			nets.append(conv6)

			output = conv6

			
			return output, nets								 			

	def global_features_network(self, input, name="global_network"):
		nets = []
		with tf.variable_scope(name) as scope:
			conv1 = tf.contrib.layers.conv2d(input, 512,
											 kernel_size=3, stride=2,
											 padding="VALID",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv1")	
			nets.append(conv1)

			conv2 = tf.contrib.layers.conv2d(conv1, 512,
											 kernel_size=3, stride=1,
											 padding="SAME",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv2")	
			nets.append(conv2)

			conv3 = tf.contrib.layers.conv2d(conv2, 512,
											 kernel_size=3, stride=2,
											 padding="VALID",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv3")	
			nets.append(conv3)

			conv4 = tf.contrib.layers.conv2d(conv3, 512,
											 kernel_size=3, stride=1,
											 padding="SAME",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv4")
			nets.append(conv4)

			flattened = tf.contrib.layers.flatten(conv4)
			fc1 = tf.contrib.layers.fully_connected(flattened, num_outputs=1024,
													weights_initializer=tf.contrib.layers.xavier_initializer(),
													scope="fc1"
													)
			fc2 = tf.contrib.layers.fully_connected(fc1, num_outputs=512,
													weights_initializer=tf.contrib.layers.xavier_initializer(),
													scope="fc2"
													)
			fc3 = tf.contrib.layers.fully_connected(fc2, num_outputs=256,
													weights_initializer=tf.contrib.layers.xavier_initializer(),
													scope="fc3"
													)
			output = fc3

			return output, nets

	def middle_level_features_network(self, input, name="middle_network"):
		nets = []
		with tf.variable_scope(name) as scope:
			conv1 = tf.contrib.layers.conv2d(input, 512,
											 kernel_size=3, stride=1,
											 padding="SAME",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv1")
			nets.append(conv1)

			conv2 = tf.contrib.layers.conv2d(conv1, 256,
											 kernel_size=3, stride=1,
											 padding="SAME",
											 weights_initializer=tf.contrib.layers.xavier_initializer(),
											 activation_fn=tf.nn.relu,											 
											 scope="conv2")
			nets.append(conv2)

			output = conv2


			return output, nets



	def colorization_network(self, input, name="colorization_network"):
		nets = []
		with tf.variable_scope(name) as scope:
			deconv1 = tf.contrib.layers.conv2d_transpose(input, 128,
														 kernel_size=3, stride=1,
														 padding="SAME",
														 weights_initializer=tf.contrib.layers.xavier_initializer(),
														 activation_fn=tf.nn.relu,
														 scope="deconv1")
			nets.append(deconv1)

			deconv2 = tf.contrib.layers.conv2d_transpose(deconv1, 64,
														 kernel_size=3, stride=2,
														 padding="VALID",
														 weights_initializer=tf.contrib.layers.xavier_initializer(),
														 activation_fn=tf.nn.relu,
														 scope="deconv2")			
			nets.append(deconv2)

			deconv3 = tf.contrib.layers.conv2d_transpose(deconv2, 64,
														 kernel_size=3, stride=1,
														 padding="SAME",
														 weights_initializer=tf.contrib.layers.xavier_initializer(),
														 activation_fn=tf.nn.relu,
														 scope="deconv3")			
			nets.append(deconv3)

			deconv4 = tf.contrib.layers.conv2d_transpose(deconv3, 32,
														 kernel_size=3, stride=2,
														 padding="VALID",
														 weights_initializer=tf.contrib.layers.xavier_initializer(),
														 activation_fn=tf.nn.relu,
														 scope="deconv4")			
			nets.append(deconv4)			

			deconv5 = tf.contrib.layers.conv2d_transpose(deconv4, 32,
														 kernel_size=4, stride=2,
														 padding="VALID",
														 weights_initializer=tf.contrib.layers.xavier_initializer(),
														 activation_fn=tf.nn.sigmoid,
														 scope="deconv5")			
			nets.append(deconv5)		

			deconv6 = tf.contrib.layers.conv2d_transpose(deconv5, 2,
														 kernel_size=3, stride=1,
														 padding="SAME",
														 weights_initializer=tf.contrib.layers.xavier_initializer(),
														 activation_fn=tf.nn.sigmoid,
														 scope="deconv6")			
			nets.append(deconv6)

			output = deconv6

			return output, nets
			#Continue workign on this part


	def fuse_net(self, global_input, middle_input, name="fusenet"):
		with tf.variable_scope(name) as scope:
			middle_shape = middle_input.get_shape()
			reshaped_global = global_input[:,tf.newaxis,:]
			reshaped_global = tf.tile(reshaped_global, [1, middle_shape[1].value*middle_shape[2].value, 1])
			reshaped_global = tf.reshape(reshaped_global, shape=[middle_shape[0].value, middle_shape[1].value, middle_shape[2].value, -1])

			fuse_ready = tf.concat([middle_input, reshaped_global], axis=3)
			fuse_ready_shape = fuse_ready.get_shape()
			fuse_ready = fuse_ready[...,tf.newaxis]
			fuse_weight = tf.get_variable("weight", shape=[fuse_ready_shape[0], fuse_ready_shape[1], fuse_ready_shape[2], 512, 256])		
			fused = tf.matmul(fuse_ready, fuse_weight, transpose_a=True)
			fused = tf.squeeze(fused, axis=-2)

			return fused			








