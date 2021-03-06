"""Evaluation for grka.

Accuracy:
grka_train.py achieves 83.0% accuracy after 100K steps (256 epochs
of data) as judged by grka_eval.py.

Speed:
On a single Tesla K40, grka_train.py processes a single batch of 128 images
in 0.25-0.35 sec (i.e. 350 - 600 images /sec). The model reaches ~86%
accuracy after 100K steps in 8 hours of training time.

Usage:
Please see the tutorial and website for how to download the grka
data set, compile the program and train the model.

http://tensorflow.org/tutorials/deep_cnn/
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from datetime import datetime
import math
import time
import os

import numpy as np
import tensorflow as tf

import grka

import atexit

from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

FLAGS = tf.app.flags.FLAGS

tf.app.flags.DEFINE_string('checkpoint_dir', '../../models/',
                           """Directory where to read model checkpoints.""")
tf.app.flags.DEFINE_float('dropout_keep_probability', 1.0,
                          "How many nodes to keep during dropout")

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class MLServer(object):
    def inference(self, data):
        images = np.reshape(data, (1, 4410))
        predictions = self.logits.eval(feed_dict={self.images: images},
                                       session=self.sess)
        return np.argmax(predictions).item()

    def setup(self):
        self.g = tf.Graph().as_default()
        # Get images and labels for grka.
        self.images = tf.placeholder(tf.float32, shape=(1, 4410),
                                     name="input_images")

        # Build a Graph that computes the logits predictions from the
        # inference model.
        self.logits = grka.inference(self.images, False)

        # Calculate predictions.
        # top_k_op = tf.nn.in_top_k(logits, labels, 1)
        # top_k_op2 = tf.nn.in_top_k(logits, labels, 3)
        # conf_matrix_op = tf.contrib.metrics.confusion_matrix(
        #     tf.argmax(logits, 1), labels,
        #     num_classes=grka.NUM_CLASSES)

        # Restore the moving average version of the learned variables for eval.
        # variable_averages = tf.train.ExponentialMovingAverage(
        #     grka.MOVING_AVERAGE_DECAY)
        # variables_to_restore = variable_averages.variables_to_restore()
        saver = tf.train.Saver(
                               write_version=tf.train.SaverDef.V2)

        config = tf.ConfigProto(
            # device_count={'GPU': 0}
        )
        self.sess = tf.Session(config=config)

        ckpt = tf.train.get_checkpoint_state(FLAGS.checkpoint_dir)
        if ckpt and ckpt.model_checkpoint_path:
            # Restores from checkpoint
            saver.restore(self.sess, FLAGS.checkpoint_dir +
            os.path.basename(
                ckpt.model_checkpoint_path))
            # Assuming model_checkpoint_path looks something like:
            #   /my-favorite-path/grka_train/model.ckpt-0,
            # extract global_step from it.
            global_step = ckpt.model_checkpoint_path.split('/')[-1] \
                .split('-')[-1]
        else:
            print('No checkpoint file found')
            return

def main(argv=None):  # pylint: disable=unused-argument
    serv = MLServer()

    serv.setup()

    atexit.register(teardown, serv.sess, serv.g)

    server = SimpleXMLRPCServer(("localhost", 8765),
                            requestHandler=RequestHandler)
    server.register_introspection_functions()

    server.register_function(serv.inference, 'inference')

    # Run the server's main loop
    server.serve_forever()

def teardown(session, graph):
    session.close()
    graph.close()


if __name__ == '__main__':
    tf.app.run()
