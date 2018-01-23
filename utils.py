import tensorflow as tf
import numpy as np
import cv2
import os

def img_tile(step, args, imgs, aspect_ratio=1.0, tile_shape=None, border=1, border_color=0):
  imgs = imgs[0]

  if imgs.ndim != 3 and imgs.ndim != 4:
    raise ValueError('imgs has wrong number of dimensions.')
  n_imgs = imgs.shape[0]

  tile_shape = None
  # Grid shape
  img_shape = np.array(imgs.shape[1:3])
  if tile_shape is None:
    img_aspect_ratio = img_shape[1] / float(img_shape[0])
    aspect_ratio *= img_aspect_ratio
    tile_height = int(np.ceil(np.sqrt(n_imgs * aspect_ratio)))
    tile_width = int(np.ceil(np.sqrt(n_imgs / aspect_ratio)))
    grid_shape = np.array((tile_height, tile_width))
  else:
    assert len(tile_shape) == 2
    grid_shape = np.array(tile_shape)

  # Tile image shape
  tile_img_shape = np.array(imgs.shape[1:])
  tile_img_shape[:2] = (img_shape[:2] + border) * grid_shape[:2] - border

  # Assemble tile image
  tile_img = np.empty(tile_img_shape)
  tile_img[:] = border_color
  for i in range(grid_shape[0]):
    for j in range(grid_shape[1]):
      img_idx = j + i*grid_shape[1]
      if img_idx >= n_imgs:
        # No more images - stop filling out the grid.
        break
      img = imgs[img_idx]
      yoff = (img_shape[0] + border) * i
      xoff = (img_shape[1] + border) * j
      tile_img[yoff:yoff+img_shape[0], xoff:xoff+img_shape[1], ...] = img

  cv2.imwrite(args.images+"/img_"+str(step) + ".jpg", tile_img*255.)


def check_image(image):
    assertion = tf.assert_equal(tf.shape(image)[-1], 3, message="image must have 3 color channels")
    with tf.control_dependencies([assertion]):
        image = tf.identity(image)

    if image.get_shape().ndims not in (3, 4):
        raise ValueError("image must be either 3 or 4 dimensions")

    # make the last dimension 3 so that you can unstack the colors
    shape = list(image.get_shape())
    shape[-1] = 3
    image.set_shape(shape)
    return image

def deprocess(image):
    with tf.name_scope("deprocess"):
        # [-1, 1] => [0, 1]
        return (image + 1.0) / 2.0


def deprocess_lab(L_chan, a_chan, b_chan):
    with tf.name_scope("deprocess_lab"):
        # this is axis=3 instead of axis=2 because we process individual images but deprocess batches
        return tf.stack([(L_chan + 1.0) / 2.0 * 100.0, a_chan * 110.0, b_chan * 110.0], axis=3)

def preprocess_lab(lab):
    with tf.name_scope("preprocess_lab"):
        L_chan, a_chan, b_chan = tf.unstack(lab, axis=3)
        # L_chan: black and white with input range [0, 100]
        # a_chan/b_chan: color channels with input range ~[-110, 110], not exact
        # [0, 100] => [-1, 1],  ~[-110, 110] => [-1, 1]
        return [L_chan / 50.0 - 1.0, a_chan / 110.0, b_chan / 110.0]


def lab_to_rgb(lab):
    with tf.name_scope("lab_to_rgb"):
        lab = check_image(lab)
        lab_pixels = tf.reshape(lab, [-1, 3])

        # https://en.wikipedia.org/wiki/Lab_color_space#CIELAB-CIEXYZ_conversions
        with tf.name_scope("cielab_to_xyz"):
            # convert to fxfyfz
            lab_to_fxfyfz = tf.constant([
                #   fx      fy        fz
                [1.0/116.0, 1.0/116.0,  1.0/116.0], # l
                [1.0/500.0,       0.0,        0.0], # a
                [      0.0,       0.0, -1.0/200.0], # b
            ])
            fxfyfz_pixels = tf.matmul(lab_pixels + tf.constant([16.0, 0.0, 0.0]), lab_to_fxfyfz)

            # convert to xyz
            epsilon = 6.0/29.0
            linear_mask = tf.cast(fxfyfz_pixels <= epsilon, dtype=tf.float32)
            exponential_mask = tf.cast(fxfyfz_pixels > epsilon, dtype=tf.float32)
            xyz_pixels = (3.0 * epsilon**2 * (fxfyfz_pixels - 4.0/29.0)) * linear_mask + (fxfyfz_pixels ** 3) * exponential_mask

            # denormalize for D65 white point
            xyz_pixels = tf.multiply(xyz_pixels, [0.950456, 1.0, 1.088754])

        with tf.name_scope("xyz_to_srgb"):
            xyz_to_rgb = tf.constant([
                #     r           g          b
                [ 3.2404542, -0.9692660,  0.0556434], # x
                [-1.5371385,  1.8760108, -0.2040259], # y
                [-0.4985314,  0.0415560,  1.0572252], # z
            ])
            rgb_pixels = tf.matmul(xyz_pixels, xyz_to_rgb)
            # avoid a slightly negative number messing up the conversion
            rgb_pixels = tf.clip_by_value(rgb_pixels, 0.0, 1.0)
            linear_mask = tf.cast(rgb_pixels <= 0.0031308, dtype=tf.float32)
            exponential_mask = tf.cast(rgb_pixels > 0.0031308, dtype=tf.float32)
            srgb_pixels = (rgb_pixels * 12.92 * linear_mask) + ((rgb_pixels ** (1.0/2.4) * 1.055) - 0.055) * exponential_mask

        return tf.reshape(srgb_pixels, tf.shape(lab))



def rgb_to_lab(srgb):
    with tf.name_scope("rgb_to_lab"):
        srgb = check_image(srgb)
        srgb_pixels = tf.reshape(srgb, [-1, 3])
        
        with tf.name_scope("srgb_to_xyz"):
            linear_mask = tf.cast(srgb_pixels <= 0.04045, dtype=tf.float32)
            exponential_mask = tf.cast(srgb_pixels > 0.04045, dtype=tf.float32)
            rgb_pixels = (srgb_pixels / 12.92 * linear_mask) + (((srgb_pixels + 0.055) / 1.055) ** 2.4) * exponential_mask
            rgb_to_xyz = tf.constant([
                #    X        Y          Z
                [0.412453, 0.212671, 0.019334], # r
                [0.357580, 0.715160, 0.119193], # G
                [0.180423, 0.072169, 0.950227], # B
            ])

            xyz_pixels = tf.matmul(rgb_pixels, rgb_to_xyz)

        # https://en.wikipedia.org/wiki/Lab_color_space#CIELAB-CIEXYZ_conversions
        with tf.name_scope("xyz_to_cielab"):
            # convert to fx = f(X/Xn), fy = f(Y/Yn), fz = f(Z/Zn)

            # normalize for D65 white point
            xyz_normalized_pixels = tf.multiply(xyz_pixels, [1.0/0.950456, 1.0, 1.0/1.088754])

            epsilon = 6.0/29.0
            linear_mask = tf.cast(xyz_normalized_pixels <= (epsilon**3), dtype=tf.float32)
            exponential_mask = tf.cast(xyz_normalized_pixels > (epsilon**3), dtype=tf.float32)
            fxfyfz_pixels = (xyz_normalized_pixels / (3.0 * epsilon**2) + 4.0/29.0) * linear_mask + (xyz_normalized_pixels ** (1.0/3.0)) * exponential_mask

            # convert to lab
            fxfyfz_to_lab = tf.constant([
                #  l       a       b
                [  0.0,  500.0,    0.0], # fx
                [116.0, -500.0,  200.0], # fy
                [  0.0,    0.0, -200.0], # fz
            ])
            lab_pixels = tf.matmul(fxfyfz_pixels, fxfyfz_to_lab) + tf.constant([-16.0, 0.0, 0.0])
        
        
        #lab_pixels = tf.Print(lab_pixels, [epsilon], summarize=10, message="srgb_pixels")
        # lab_pixels = tf.Print(lab_pixels, [srgb_pixels], summarize=10, message="srgb_pixels")
        # lab_pixels = tf.Print(lab_pixels, [rgb_pixels], summarize=10, message="rgb_pixels")
        # lab_pixels = tf.Print(lab_pixels, [xyz_pixels], summarize=10, message="xyz_pixels")
        # lab_pixels = tf.Print(lab_pixels, [xyz_normalized_pixels], summarize=10, message="xyz_normalized_pixels")
        # lab_pixels = tf.Print(lab_pixels, [linear_mask], summarize=10, message="linear_mask")
        # lab_pixels = tf.Print(lab_pixels, [exponential_mask], summarize=10, message="exponential_mask")
        # lab_pixels = tf.Print(lab_pixels, [fxfyfz_pixels], summarize=10, message="fxfyfz_pixels")
        # lab_pixels = tf.Print(lab_pixels, [lab_pixels], summarize=10, message="lab_pixels")
        return tf.reshape(lab_pixels, tf.shape(srgb))




def batch_norm(input, name="batch_norm"):
    with tf.variable_scope(name) as scope:
        input = tf.identity(input)
        channels = input.get_shape()[3]

        offset = tf.get_variable("offset", [channels], dtype=tf.float32, initializer=tf.constant_initializer(0.0))
        scale = tf.get_variable("scale", [channels], dtype=tf.float32, initializer=tf.random_normal_initializer(1.0, 0.02))

        mean, variance = tf.nn.moments(input, axes=[0,1,2], keep_dims=False)

        normalized_batch = tf.nn.batch_normalization(input, mean, variance, offset, scale, variance_epsilon=1e-5)

        return normalized_batch 